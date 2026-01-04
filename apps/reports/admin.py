"""
Admin configuration for reports app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    Dashboard,
    GeneratedReport,
    ReportTemplate,
    ScheduledReport,
    UserDashboard,
)


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    """Admin configuration for ReportTemplate model."""

    list_display = [
        "name",
        "report_type",
        "default_format",
        "is_active",
        "is_scheduled",
        "created_at",
    ]
    list_filter = ["report_type", "default_format", "is_active", "is_scheduled"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = [
        (
            None,
            {
                "fields": ["name", "description", "report_type", "default_format"],
            },
        ),
        (
            _("Configuración"),
            {
                "fields": [
                    "template_file",
                    "query_definition",
                    "columns",
                    "filters",
                ],
            },
        ),
        (
            _("Estado"),
            {
                "fields": ["is_active", "is_scheduled", "created_by"],
            },
        ),
    ]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    """Admin configuration for GeneratedReport model."""

    list_display = [
        "name",
        "template",
        "format",
        "status",
        "row_count",
        "generated_by",
        "created_at",
    ]
    list_filter = ["status", "format", "created_at"]
    search_fields = ["name", "template__name"]
    readonly_fields = [
        "file_size",
        "row_count",
        "generation_started_at",
        "generation_completed_at",
        "created_at",
    ]
    raw_id_fields = ["generated_by"]
    date_hierarchy = "created_at"


@admin.register(ScheduledReport)
class ScheduledReportAdmin(admin.ModelAdmin):
    """Admin configuration for ScheduledReport model."""

    list_display = [
        "name",
        "template",
        "frequency",
        "is_active",
        "next_run_at",
        "last_run_at",
    ]
    list_filter = ["frequency", "is_active"]
    search_fields = ["name", "template__name"]
    readonly_fields = ["last_run_at", "next_run_at", "created_at", "updated_at"]
    raw_id_fields = ["created_by"]


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    """Admin configuration for Dashboard model."""

    list_display = [
        "name",
        "is_default",
        "is_public",
        "is_active",
        "created_by",
    ]
    list_filter = ["is_default", "is_public", "is_active"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(UserDashboard)
class UserDashboardAdmin(admin.ModelAdmin):
    """Admin configuration for UserDashboard model."""

    list_display = ["user", "dashboard", "updated_at"]
    search_fields = ["user__email"]
    raw_id_fields = ["user"]
