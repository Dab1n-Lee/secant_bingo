from django.contrib import admin

from .models import BingoItem, BingoSubmission, Member


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


@admin.register(BingoSubmission)
class BingoSubmissionAdmin(admin.ModelAdmin):
    list_display = ("bingo_item", "team", "status", "submitted_by", "created_at")
    list_filter = ("team", "status")
    search_fields = ("title", "content", "submitted_by__name")
    autocomplete_fields = ("submitted_by", "participants", "bingo_item")
    actions = ["approve_selected"]

    @admin.action(description="승인 처리")
    def approve_selected(self, request, queryset):
        updated = queryset.update(status=BingoSubmission.STATUS_APPROVED)
        self.message_user(request, f"{updated}개 제출을 승인했습니다.")
