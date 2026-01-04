"""
Admin configuration for lessons_learned app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Category, LessonAttachment, LessonComment, LessonLearned


class LessonAttachmentInline(admin.TabularInline):
    """Inline for attachments in lesson admin."""

    model = LessonAttachment
    extra = 1


class LessonCommentInline(admin.TabularInline):
    """Inline for comments in lesson admin."""

    model = LessonComment
    extra = 0
    readonly_fields = ["user", "created_at"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin configuration for Category model."""

    list_display = ["name", "parent", "order", "is_active"]
    list_filter = ["is_active", "parent"]
    search_fields = ["name"]
    ordering = ["order", "name"]


@admin.register(LessonLearned)
class LessonLearnedAdmin(admin.ModelAdmin):
    """Admin configuration for LessonLearned model."""

    list_display = [
        "title",
        "category",
        "lesson_type",
        "severity",
        "status",
        "is_featured",
        "view_count",
        "created_at",
    ]
    list_filter = ["status", "lesson_type", "severity", "category", "is_featured"]
    search_fields = ["title", "description", "situation", "lesson"]
    readonly_fields = ["view_count", "created_at", "updated_at", "reviewed_at"]
    date_hierarchy = "created_at"
    inlines = [LessonAttachmentInline, LessonCommentInline]
    autocomplete_fields = ["category"]

    fieldsets = [
        (
            None,
            {
                "fields": ["title", "description", "category"],
            },
        ),
        (
            _("Clasificación"),
            {
                "fields": [
                    "lesson_type",
                    "severity",
                    "status",
                    "is_featured",
                ],
            },
        ),
        (
            _("Contenido"),
            {
                "fields": [
                    "situation",
                    "root_cause",
                    "lesson",
                    "recommendations",
                ],
            },
        ),
        (
            _("Contexto"),
            {
                "fields": [
                    "location",
                    "date_occurred",
                    "tags",
                    "target_profiles",
                ],
            },
        ),
        (
            _("Revisión"),
            {
                "fields": [
                    "created_by",
                    "reviewed_by",
                    "reviewed_at",
                    "review_notes",
                ],
            },
        ),
        (
            _("Estadísticas"),
            {
                "fields": ["view_count", "created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
