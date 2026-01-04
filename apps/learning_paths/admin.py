"""
Admin configuration for learning_paths app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import LearningPath, PathAssignment, PathCourse


class PathCourseInline(admin.TabularInline):
    """Inline for courses in learning path admin."""

    model = PathCourse
    extra = 1
    ordering = ["order"]
    autocomplete_fields = ["course"]


@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    """Admin configuration for LearningPath model."""

    list_display = [
        "name",
        "status",
        "is_mandatory",
        "total_courses",
        "estimated_duration",
        "created_at",
    ]
    list_filter = ["status", "is_mandatory", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [PathCourseInline]

    fieldsets = [
        (
            None,
            {
                "fields": ["name", "description", "thumbnail"],
            },
        ),
        (
            _("Configuración"),
            {
                "fields": [
                    "target_profiles",
                    "is_mandatory",
                    "estimated_duration",
                    "status",
                ],
            },
        ),
        (
            _("Auditoría"),
            {
                "fields": ["created_by", "created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PathAssignment)
class PathAssignmentAdmin(admin.ModelAdmin):
    """Admin configuration for PathAssignment model."""

    list_display = [
        "user",
        "learning_path",
        "status",
        "progress",
        "due_date",
        "assigned_by",
    ]
    list_filter = ["status", "created_at", "due_date"]
    search_fields = ["user__email", "user__first_name", "learning_path__name"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["user", "assigned_by"]
    autocomplete_fields = ["learning_path"]
