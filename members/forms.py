from django import forms

from .models import BingoSubmission, Member


class LoginForm(forms.Form):
    student_id = forms.CharField(label="학번", max_length=20)
    phone_last4 = forms.CharField(label="전화번호 뒷자리", min_length=4, max_length=4)

    def clean_phone_last4(self):
        last4 = self.cleaned_data["phone_last4"]
        if not last4.isdigit():
            raise forms.ValidationError("숫자만 입력해주세요.")
        return last4


class BingoSubmissionForm(forms.ModelForm):
    class Meta:
        model = BingoSubmission
        fields = ["title", "content", "photo", "participants"]
        widgets = {"participants": forms.CheckboxSelectMultiple()}

    def __init__(self, *args, member: Member, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["participants"].queryset = Member.objects.filter(team=member.team).exclude(
            id=member.id
        )
        self.member = member

    def clean(self):
        cleaned = super().clean()
        participants = cleaned.get("participants")
        participant_count = participants.count() if participants is not None else 0
        total_people = participant_count + 1  # + submitter
        if total_people < 4:
            raise forms.ValidationError("본인을 포함해 최소 4명이 참여해야 합니다.")
        return cleaned
