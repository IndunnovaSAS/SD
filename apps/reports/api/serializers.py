"""
Serializers for reports and dashboards API.
"""

from rest_framework import serializers

from apps.reports.models import (
    Dashboard,
    GeneratedReport,
    ReportTemplate,
    ScheduledReport,
    UserDashboard,
)


class ReportTemplateListSerializer(serializers.ModelSerializer):
    """List serializer for report templates."""

    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )
    report_type_display = serializers.CharField(
        source="get_report_type_display", read_only=True
    )

    class Meta:
        model = ReportTemplate
        fields = [
            "id",
            "name",
            "description",
            "report_type",
            "report_type_display",
            "default_format",
            "is_active",
            "is_scheduled",
            "created_by_name",
            "created_at",
        ]


class ReportTemplateSerializer(serializers.ModelSerializer):
    """Full serializer for report templates."""

    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    class Meta:
        model = ReportTemplate
        fields = [
            "id",
            "name",
            "description",
            "report_type",
            "default_format",
            "template_file",
            "query_definition",
            "columns",
            "filters",
            "is_active",
            "is_scheduled",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]


class GeneratedReportListSerializer(serializers.ModelSerializer):
    """List serializer for generated reports."""

    template_name = serializers.CharField(source="template.name", read_only=True)
    generated_by_name = serializers.CharField(
        source="generated_by.get_full_name", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = GeneratedReport
        fields = [
            "id",
            "name",
            "template",
            "template_name",
            "format",
            "status",
            "status_display",
            "file_size",
            "row_count",
            "generated_by_name",
            "created_at",
            "expires_at",
        ]


class GeneratedReportSerializer(serializers.ModelSerializer):
    """Full serializer for generated reports."""

    template_name = serializers.CharField(source="template.name", read_only=True)
    generated_by_name = serializers.CharField(
        source="generated_by.get_full_name", read_only=True
    )

    class Meta:
        model = GeneratedReport
        fields = [
            "id",
            "name",
            "template",
            "template_name",
            "format",
            "status",
            "filters_applied",
            "file",
            "file_size",
            "row_count",
            "generation_started_at",
            "generation_completed_at",
            "error_message",
            "generated_by",
            "generated_by_name",
            "expires_at",
            "created_at",
        ]
        read_only_fields = [
            "status",
            "file",
            "file_size",
            "row_count",
            "generation_started_at",
            "generation_completed_at",
            "error_message",
            "generated_by",
            "created_at",
        ]


class GenerateReportSerializer(serializers.Serializer):
    """Serializer for report generation request."""

    template_id = serializers.IntegerField()
    name = serializers.CharField(max_length=200, required=False)
    format = serializers.ChoiceField(
        choices=ReportTemplate.Format.choices,
        required=False,
    )
    filters = serializers.JSONField(required=False, default=dict)


class ScheduledReportSerializer(serializers.ModelSerializer):
    """Serializer for scheduled reports."""

    template_name = serializers.CharField(source="template.name", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )
    frequency_display = serializers.CharField(
        source="get_frequency_display", read_only=True
    )

    class Meta:
        model = ScheduledReport
        fields = [
            "id",
            "name",
            "template",
            "template_name",
            "frequency",
            "frequency_display",
            "format",
            "filters",
            "recipients",
            "day_of_week",
            "day_of_month",
            "time_of_day",
            "is_active",
            "last_run_at",
            "next_run_at",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "last_run_at",
            "next_run_at",
            "created_by",
            "created_at",
            "updated_at",
        ]


class DashboardListSerializer(serializers.ModelSerializer):
    """List serializer for dashboards."""

    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )
    widget_count = serializers.SerializerMethodField()

    class Meta:
        model = Dashboard
        fields = [
            "id",
            "name",
            "description",
            "is_default",
            "is_active",
            "is_public",
            "widget_count",
            "created_by_name",
            "created_at",
        ]

    def get_widget_count(self, obj):
        return len(obj.widgets) if obj.widgets else 0


class DashboardSerializer(serializers.ModelSerializer):
    """Full serializer for dashboards."""

    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    class Meta:
        model = Dashboard
        fields = [
            "id",
            "name",
            "description",
            "is_default",
            "layout",
            "widgets",
            "is_active",
            "is_public",
            "allowed_roles",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]


class UserDashboardSerializer(serializers.ModelSerializer):
    """Serializer for user dashboard preferences."""

    dashboard_name = serializers.CharField(source="dashboard.name", read_only=True)

    class Meta:
        model = UserDashboard
        fields = [
            "id",
            "user",
            "dashboard",
            "dashboard_name",
            "custom_widgets",
            "updated_at",
        ]
        read_only_fields = ["user", "updated_at"]
