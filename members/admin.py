from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm

from .models import BingoItem, BingoSubmission, BingoSubmissionAttachment, Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("name", "student_id", "team", "phone_last4")
    list_filter = ("team",)
    search_fields = ("name", "student_id", "phone_number")


@admin.register(BingoItem)
class BingoItemAdmin(admin.ModelAdmin):
    list_display = ("team", "position", "title")
    list_filter = ("team",)
    ordering = ("team", "position")
    search_fields = ("title", "description")


class BingoSubmissionAttachmentInline(admin.TabularInline):
    model = BingoSubmissionAttachment
    extra = 0
    readonly_fields = ("uploaded_at",)


@admin.register(BingoSubmission)
class BingoSubmissionAdmin(admin.ModelAdmin):
    list_display = ("bingo_item", "team", "status", "submitted_by", "created_at")
    list_filter = ("team", "status")
    search_fields = ("title", "content", "submitted_by__name")
    autocomplete_fields = ("submitted_by", "participants", "bingo_item")
    actions = ["approve_selected", "reject_selected"]
    inlines = (BingoSubmissionAttachmentInline,)
    exclude = ("photo",)
    form = None  # placeholder for assignment below
    class RejectReasonActionForm(ActionForm):
        rejection_reason = forms.CharField(label="반려 사유", required=False)

        class Media:
            js = ("admin/reject_reason_toggle.js",)

    action_form = RejectReasonActionForm

    @admin.action(description="승인 처리")
    def approve_selected(self, request, queryset):
        updated = queryset.update(status=BingoSubmission.STATUS_APPROVED, rejected_reason="")
        self.message_user(request, f"{updated}개 제출을 승인했습니다.")

    @admin.action(description="반려 처리")
    def reject_selected(self, request, queryset):
        reason = request.POST.get("rejection_reason", "").strip()
        if not reason:
            messages.error(request, "반려 사유를 입력해주세요.")
            return
        updated = queryset.update(status=BingoSubmission.STATUS_REJECTED, rejected_reason=reason)
        self.message_user(request, f"{updated}개 제출을 반려했습니다.")


class BingoSubmissionAdminForm(forms.ModelForm):
    class Meta:
        model = BingoSubmission
        fields = "__all__"

    class Media:
        js = ("admin/reject_reason_toggle.js",)

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        reason = cleaned.get("rejected_reason", "").strip()
        if status == BingoSubmission.STATUS_REJECTED and not reason:
            raise forms.ValidationError({"rejected_reason": "반려 사유를 입력해주세요."})
        if status != BingoSubmission.STATUS_REJECTED:
            cleaned["rejected_reason"] = ""
        return cleaned


BingoSubmissionAdmin.form = BingoSubmissionAdminForm
