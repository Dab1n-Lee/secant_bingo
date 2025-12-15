from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .forms import BingoSubmissionForm, LoginForm
from .models import BingoItem, BingoSubmission, BingoSubmissionAttachment, Member


def _get_member_from_session(request):
    member_id = request.session.get("member_id")
    if not member_id:
        return None
    try:
        return Member.objects.get(pk=member_id)
    except Member.DoesNotExist:
        request.session.pop("member_id", None)
        return None


@require_http_methods(["GET", "POST"])
def login_view(request):
    if _get_member_from_session(request):
        return redirect("board")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        student_id = form.cleaned_data["student_id"]
        phone_last4 = form.cleaned_data["phone_last4"]

        try:
            member = Member.objects.get(student_id=student_id)
        except Member.DoesNotExist:
            form.add_error(None, "회원 정보가 없어요. 관리자에게 문의해주세요.")
        else:
            if member.phone_last4 != phone_last4:
                form.add_error("phone_last4", "전화번호 뒷자리가 일치하지 않아요.")
            else:
                request.session["member_id"] = member.id
                messages.success(request, f"{member.name}님, 환영합니다!")
                return redirect("board")

    return render(request, "members/login.html", {"form": form, "member": None})


def board_view(request):
    member = _get_member_from_session(request)
    if not member:
        return redirect("login")

    bingo_items = list(BingoItem.objects.filter(team=member.team).order_by("position"))
    submissions = list(
        BingoSubmission.objects.filter(team=member.team)
        .select_related("bingo_item", "submitted_by")
        .prefetch_related("participants", "attachments")
    )
    submissions_map = {s.bingo_item_id: s for s in submissions}
    team_members = Member.objects.filter(team=member.team).order_by("name")
    approved_count = sum(1 for s in submissions_map.values() if s.status == BingoSubmission.STATUS_APPROVED)
    approved_positions = {s.bingo_item.position for s in submissions if s.status == BingoSubmission.STATUS_APPROVED}
    winning_lines = [
        {1, 2, 3}, {4, 5, 6}, {7, 8, 9},  # 가로
        {1, 4, 7}, {2, 5, 8}, {3, 6, 9},  # 세로
        {1, 5, 9}, {3, 5, 7},  # 대각선
    ]
    bingo_line_completed = any(line.issubset(approved_positions) for line in winning_lines)
    completed = bingo_line_completed
    board_data = [(item, submissions_map.get(item.id)) for item in bingo_items]

    submission_details = {}
    for s in submissions:
        attachments = [
            {"url": a.file.url, "name": a.filename, "kind": a.kind} for a in s.attachments.all()
        ]
        submission_details[s.bingo_item_id] = {
            "id": s.id,
            "title": s.title,
            "content": s.content,
            "status": s.status,
            "rejected_reason": s.rejected_reason,
            "participants": [p.name for p in s.participants.all()],
            "participant_ids": [p.id for p in s.participants.all()],
            "attachments": attachments,
            "submitted_by": s.submitted_by.name,
            "submitted_by_id": s.submitted_by_id,
            "item_title": s.bingo_item.title,
            "item_desc": s.bingo_item.description or "",
            "item_position": s.bingo_item.position,
        }

    # 팀 반려 알림(1회성)
    rejected_submissions = [s for s in submissions if s.status == BingoSubmission.STATUS_REJECTED]
    notified_ids = set(request.session.get("notified_rejections", []))
    new_rejections = [s for s in rejected_submissions if s.id not in notified_ids]
    if new_rejections:
        for s in new_rejections:
            reason = s.rejected_reason or "사유 없음"
            messages.warning(
                request,
                f"{s.bingo_item.position}번 빙고가 반려되었습니다. 사유: {reason}",
            )
        request.session["notified_rejections"] = list(
            notified_ids.union({s.id for s in rejected_submissions})
        )

    return render(
        request,
        "members/board.html",
        {
            "member": member,
            "board_data": board_data,
            "team_members": team_members,
            "completed": completed,
            "bingo_line_completed": bingo_line_completed,
            "submission_details": submission_details,
        },
    )


@csrf_exempt
@require_http_methods(["GET", "POST"])
def logout_view(request):
    request.session.flush()
    messages.info(request, "로그아웃 되었습니다.")
    return redirect(reverse("login"))


@require_http_methods(["POST"])
def submit_bingo_item(request, item_id: int):
    member = _get_member_from_session(request)
    if not member:
        return redirect("login")

    bingo_item = get_object_or_404(BingoItem, id=item_id, team=member.team)
    existing = BingoSubmission.objects.filter(team=member.team, bingo_item=bingo_item).first()
    if existing:
        messages.info(request, "이미 제출된 항목입니다. 상태를 기다려주세요.")
        return redirect("board")

    form = BingoSubmissionForm(request.POST, request.FILES, member=member)
    # 모델 clean에서 bingo_item을 참조하므로 검증 전에 미리 설정해 준다.
    form.instance.bingo_item = bingo_item
    form.instance.team = member.team
    form.instance.submitted_by = member

    if form.is_valid():
        submission: BingoSubmission = form.save(commit=False)
        submission.bingo_item = bingo_item
        submission.team = member.team
        submission.submitted_by = member
        submission.status = BingoSubmission.STATUS_PENDING
        submission.save()
        form.save_m2m()
        uploaded_files = form.cleaned_data.get("attachments") or request.FILES.getlist("attachments")
        if not isinstance(uploaded_files, (list, tuple)):
            uploaded_files = [uploaded_files] if uploaded_files else []
        for f in uploaded_files:
            BingoSubmissionAttachment.objects.create(submission=submission, file=f)
        messages.success(request, "제출이 완료되었어요. 승인 대기 상태입니다.")
        return redirect("board")

    # If validation fails, re-render board with errors
    bingo_items = list(BingoItem.objects.filter(team=member.team).order_by("position"))
    submissions = list(
        BingoSubmission.objects.filter(team=member.team)
        .select_related("bingo_item", "submitted_by")
        .prefetch_related("participants", "attachments")
    )
    submissions_map = {s.bingo_item_id: s for s in submissions}
    team_members = Member.objects.filter(team=member.team).order_by("name")
    board_data = [(item, submissions_map.get(item.id)) for item in bingo_items]
    submission_details = {}
    for s in submissions:
        submission_details[s.bingo_item_id] = {
            "id": s.id,
            "title": s.title,
            "content": s.content,
            "status": s.status,
            "rejected_reason": s.rejected_reason,
            "participants": [p.name for p in s.participants.all()],
            "participant_ids": [p.id for p in s.participants.all()],
            "attachments": [
                {"url": a.file.url, "name": a.filename, "kind": a.kind} for a in s.attachments.all()
            ],
            "submitted_by": s.submitted_by.name,
            "submitted_by_id": s.submitted_by_id,
            "item_title": s.bingo_item.title,
            "item_desc": s.bingo_item.description or "",
            "item_position": s.bingo_item.position,
        }
    return render(
        request,
        "members/board.html",
        {
            "member": member,
            "board_data": board_data,
            "team_members": team_members,
            "form_errors": form.errors,
            "completed": False,
            "bingo_line_completed": False,
            "submission_details": submission_details,
        },
    )


@require_http_methods(["POST"])
def update_submission(request, submission_id: int):
    member = _get_member_from_session(request)
    if not member:
        return redirect("login")

    submission = get_object_or_404(
        BingoSubmission,
        id=submission_id,
        submitted_by=member,
        status__in=[BingoSubmission.STATUS_PENDING, BingoSubmission.STATUS_REJECTED],
    )
    existing_count = submission.attachments.count()
    form = BingoSubmissionForm(
        request.POST,
        request.FILES,
        member=member,
        existing_attachment_count=existing_count,
        instance=submission,
    )
    if form.is_valid():
        submission.title = form.cleaned_data["title"]
        submission.content = form.cleaned_data["content"]
        submission.save()
        submission.participants.set(form.cleaned_data["participants"])

        uploaded_files = form.cleaned_data.get("attachments") or request.FILES.getlist("attachments")
        if not isinstance(uploaded_files, (list, tuple)):
            uploaded_files = [uploaded_files] if uploaded_files else []
        if uploaded_files:
            if submission.photo:
                submission.photo.delete(save=False)
                submission.photo = None
                submission.save(update_fields=["photo"])
            for attachment in submission.attachments.all():
                attachment.file.delete(save=False)
                attachment.delete()
            for f in uploaded_files:
                BingoSubmissionAttachment.objects.create(submission=submission, file=f)

        messages.success(request, "제출 내용을 수정했습니다.")
        return redirect("board")

    messages.error(request, f"수정에 실패했습니다: {form.errors.as_text()}")
    return redirect("board")


@require_http_methods(["POST"])
def cancel_submission(request, submission_id: int):
    member = _get_member_from_session(request)
    if not member:
        return redirect("login")

    submission = get_object_or_404(
        BingoSubmission,
        id=submission_id,
        submitted_by=member,
        status__in=[BingoSubmission.STATUS_PENDING, BingoSubmission.STATUS_REJECTED],
    )
    if submission.photo:
        submission.photo.delete(save=False)
    for attachment in submission.attachments.all():
        attachment.file.delete(save=False)
        attachment.delete()
    submission.delete()
    messages.info(request, "제출을 취소했어요. 다시 제출할 수 있습니다.")
    return redirect("board")
