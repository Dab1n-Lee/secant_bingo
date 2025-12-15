from django.db import models


class Member(models.Model):
    TEAM_ACTIVITY = "activity"
    TEAM_CULTURE = "culture"
    TEAM_FOOD = "food"

    TEAM_CHOICES = [
        (TEAM_ACTIVITY, "액티비티조"),
        (TEAM_CULTURE, "문화탐방조"),
        (TEAM_FOOD, "맛집탐방조"),
    ]

    name = models.CharField(max_length=50)
    student_id = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(
        max_length=20,
        help_text="대시 없이 숫자만 입력하세요.",
    )
    team = models.CharField(
        max_length=20,
        choices=TEAM_CHOICES,
        default=TEAM_ACTIVITY,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.student_id})"

    @property
    def phone_last4(self) -> str:
        return self.phone_number[-4:]


class BingoItem(models.Model):
    TEAM_CHOICES = Member.TEAM_CHOICES

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(
        help_text="빙고판 순서를 위해 1~9 값을 사용하세요. 숫자가 낮을수록 위쪽/왼쪽에 배치됩니다.",
    )
    team = models.CharField(
        max_length=20,
        choices=TEAM_CHOICES,
        default=Member.TEAM_ACTIVITY,
    )

    class Meta:
        ordering = ["team", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "position"],
                name="unique_position_per_team",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_team_display()} #{self.position}: {self.title}"


class BingoSubmission(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "검토중"),
        (STATUS_APPROVED, "승인"),
        (STATUS_REJECTED, "반려"),
    ]

    team = models.CharField(
        max_length=20,
        choices=Member.TEAM_CHOICES,
        default=Member.TEAM_ACTIVITY,
    )
    bingo_item = models.ForeignKey(
        BingoItem,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    submitted_by = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    participants = models.ManyToManyField(
        Member,
        related_name="participated_submissions",
        blank=True,
    )
    title = models.CharField(max_length=100)
    content = models.TextField()
    photo = models.FileField(upload_to="bingo_photos/", null=True, blank=True)
    rejected_reason = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["team", "bingo_item__position"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "bingo_item"],
                name="unique_submission_per_team_item",
            )
        ]

    def clean(self):
        if self.team and self.bingo_item and self.team != self.bingo_item.team:
            raise models.ValidationError("빙고 아이템의 팀과 제출 팀이 일치해야 합니다.")
        if self.submitted_by and self.team and self.submitted_by.team != self.team:
            raise models.ValidationError("제출자의 팀과 제출 팀이 일치해야 합니다.")

    def __str__(self) -> str:
        return f"{self.get_team_display()} - {self.bingo_item.title} ({self.get_status_display()})"


class BingoSubmissionAttachment(models.Model):
    submission = models.ForeignKey(
        BingoSubmission,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to="bingo_attachments/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.submission_id} - {self.filename}"

    @property
    def filename(self) -> str:
        return self.file.name.split("/")[-1]

    @property
    def kind(self) -> str:
        name = self.filename.lower()
        if any(name.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic", ".heif"]):
            return "image"
        if any(name.endswith(ext) for ext in [".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"]):
            return "video"
        return "other"
