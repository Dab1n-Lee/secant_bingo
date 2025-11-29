from django import forms

from .models import BingoSubmission, Member


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class LoginForm(forms.Form):
    student_id = forms.CharField(label="학번", max_length=20)
    phone_last4 = forms.CharField(label="전화번호 뒷자리", min_length=4, max_length=4)

    def clean_phone_last4(self):
        last4 = self.cleaned_data["phone_last4"]
        if not last4.isdigit():
            raise forms.ValidationError("숫자만 입력해주세요.")
        return last4


class BingoSubmissionForm(forms.ModelForm):
    attachments = forms.FileField(
        label="첨부 파일",
        required=False,
        widget=MultiFileInput(attrs={"multiple": True, "accept": "image/*,video/*"}),
    )

    class Meta:
        model = BingoSubmission
        fields = ["title", "content", "participants", "attachments"]
        widgets = {"participants": forms.CheckboxSelectMultiple()}

    def __init__(self, *args, member: Member, existing_attachment_count: int = 0, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["participants"].queryset = Member.objects.filter(team=member.team).exclude(
            id=member.id
        )
        self.member = member
        self.existing_attachment_count = existing_attachment_count

    def clean(self):
        cleaned = super().clean()
        participants = cleaned.get("participants")
        participant_count = participants.count() if participants is not None else 0
        total_people = participant_count + 1  # + submitter
        if total_people < 4:
            raise forms.ValidationError("본인을 포함해 최소 4명이 참여해야 합니다.")

        files = self.files.getlist("attachments") if self.files else []
        file_count = len(files)
        existing_count = self.existing_attachment_count or 0
        effective_count = file_count if file_count > 0 else existing_count
        if effective_count == 0:
            raise forms.ValidationError("사진 또는 동영상 최소 1개를 첨부해주세요.")
        if effective_count > 5:
            raise forms.ValidationError("첨부 파일은 최대 5개까지 가능합니다.")

        for f in files:
            content_type = getattr(f, "content_type", "") or ""
            if not (content_type.startswith("image/") or content_type.startswith("video/")):
                raise forms.ValidationError("사진 또는 동영상 파일만 첨부할 수 있습니다.")
        return cleaned
