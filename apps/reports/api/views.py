"""
ViewSets for reports and dashboards API.
"""

from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.reports.models import (
    Dashboard,
    GeneratedReport,
    ReportTemplate,
    ScheduledReport,
    UserDashboard,
)

from .serializers import (
    DashboardListSerializer,
    DashboardSerializer,
    GeneratedReportListSerializer,
    GeneratedReportSerializer,
    GenerateReportSerializer,
    ReportTemplateListSerializer,
    ReportTemplateSerializer,
    ScheduledReportSerializer,
    UserDashboardSerializer,
)


class IsStaffOrReadOnly(permissions.BasePermission):
    """Allow read-only access for authenticated users, write for staff."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_staff


class ReportTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing report templates."""

    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        queryset = ReportTemplate.objects.select_related("created_by")

        # Filter by type
        report_type = self.request.query_params.get("type")
        if report_type:
            queryset = queryset.filter(report_type=report_type)

        # Filter by active
        is_active = self.request.query_params.get("active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # Filter by schedulable
        is_scheduled = self.request.query_params.get("schedulable")
        if is_scheduled is not None:
            queryset = queryset.filter(is_scheduled=is_scheduled.lower() == "true")

        # Search
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        return queryset.order_by("name")

    def get_serializer_class(self):
        if self.action == "list":
            return ReportTemplateListSerializer
        return ReportTemplateSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        """Get a preview of the report data."""
        template = self.get_object()
        # Return template configuration for preview
        return Response({
            "template": ReportTemplateSerializer(template).data,
            "columns": template.columns,
            "filters": template.filters,
        })


class GeneratedReportViewSet(viewsets.ModelViewSet):
    """ViewSet for managing generated reports."""

    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        queryset = GeneratedReport.objects.select_related("template", "generated_by")

        # Regular users see only their reports, staff sees all
        if not self.request.user.is_staff:
            queryset = queryset.filter(generated_by=self.request.user)

        # Filter by status
        report_status = self.request.query_params.get("status")
        if report_status:
            queryset = queryset.filter(status=report_status)

        # Filter by template
        template_id = self.request.query_params.get("template")
        if template_id:
            queryset = queryset.filter(template_id=template_id)

        # Filter by format
        report_format = self.request.query_params.get("format")
        if report_format:
            queryset = queryset.filter(format=report_format)

        # Filter by date range
        date_from = self.request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "list":
            return GeneratedReportListSerializer
        if self.action == "generate":
            return GenerateReportSerializer
        return GeneratedReportSerializer

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """Generate a new report."""
        serializer = GenerateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        template_id = serializer.validated_data["template_id"]
        try:
            template = ReportTemplate.objects.get(id=template_id, is_active=True)
        except ReportTemplate.DoesNotExist:
            return Response(
                {"error": "Plantilla no encontrada o inactiva"},
                status=status.HTTP_404_NOT_FOUND,
            )

        report_name = serializer.validated_data.get(
            "name",
            f"{template.name} - {timezone.now().strftime('%Y-%m-%d %H:%M')}"
        )
        report_format = serializer.validated_data.get("format", template.default_format)
        filters_applied = serializer.validated_data.get("filters", {})

        # Create the report record
        report = GeneratedReport.objects.create(
            template=template,
            name=report_name,
            format=report_format,
            status=GeneratedReport.Status.PENDING,
            filters_applied=filters_applied,
            generated_by=request.user,
            generation_started_at=timezone.now(),
        )

        # In a real implementation, this would queue a background task
        # For now, we just return the pending report
        return Response(
            GeneratedReportSerializer(report).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """Get download URL for a report."""
        report = self.get_object()

        if report.status != GeneratedReport.Status.COMPLETED:
            return Response(
                {"error": "El reporte aún no está listo"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not report.file:
            return Response(
                {"error": "El archivo del reporte no existe"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if report.expires_at and report.expires_at < timezone.now():
            return Response(
                {"error": "El reporte ha expirado"},
                status=status.HTTP_410_GONE,
            )

        return Response({"url": report.file.url})

    @action(detail=False, methods=["get"])
    def my_reports(self, request):
        """Get current user's reports."""
        reports = GeneratedReport.objects.filter(
            generated_by=request.user
        ).order_by("-created_at")[:20]

        return Response(GeneratedReportListSerializer(reports, many=True).data)


class ScheduledReportViewSet(viewsets.ModelViewSet):
    """ViewSet for managing scheduled reports."""

    permission_classes = [IsStaffOrReadOnly]
    serializer_class = ScheduledReportSerializer

    def get_queryset(self):
        queryset = ScheduledReport.objects.select_related("template", "created_by")

        # Filter by template
        template_id = self.request.query_params.get("template")
        if template_id:
            queryset = queryset.filter(template_id=template_id)

        # Filter by frequency
        frequency = self.request.query_params.get("frequency")
        if frequency:
            queryset = queryset.filter(frequency=frequency)

        # Filter by active
        is_active = self.request.query_params.get("active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset.order_by("name")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        """Toggle scheduled report active status."""
        schedule = self.get_object()
        schedule.is_active = not schedule.is_active
        schedule.save()
        return Response(ScheduledReportSerializer(schedule).data)

    @action(detail=True, methods=["post"])
    def run_now(self, request, pk=None):
        """Trigger immediate execution of a scheduled report."""
        schedule = self.get_object()

        # Create a generated report
        report = GeneratedReport.objects.create(
            template=schedule.template,
            name=f"{schedule.name} - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            format=schedule.format,
            status=GeneratedReport.Status.PENDING,
            filters_applied=schedule.filters,
            generated_by=request.user,
            generation_started_at=timezone.now(),
        )

        return Response({
            "message": "Reporte en proceso de generación",
            "report_id": report.id,
        })


class DashboardViewSet(viewsets.ModelViewSet):
    """ViewSet for managing dashboards."""

    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        queryset = Dashboard.objects.select_related("created_by")
        user = self.request.user

        # Non-staff users see only public dashboards or ones they have access to
        if not user.is_staff:
            queryset = queryset.filter(
                Q(is_public=True) | Q(created_by=user)
            ).filter(is_active=True)

        # Filter by active
        is_active = self.request.query_params.get("active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # Filter by public
        is_public = self.request.query_params.get("public")
        if is_public is not None:
            queryset = queryset.filter(is_public=is_public.lower() == "true")

        # Search
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        return queryset.order_by("-is_default", "name")

    def get_serializer_class(self):
        if self.action == "list":
            return DashboardListSerializer
        return DashboardSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def set_default(self, request, pk=None):
        """Set dashboard as default."""
        if not request.user.is_staff:
            return Response(
                {"error": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )

        dashboard = self.get_object()

        # Unset other defaults
        Dashboard.objects.filter(is_default=True).update(is_default=False)

        dashboard.is_default = True
        dashboard.save()

        return Response(DashboardSerializer(dashboard).data)

    @action(detail=False, methods=["get"])
    def default(self, request):
        """Get the default dashboard."""
        dashboard = Dashboard.objects.filter(
            is_default=True, is_active=True
        ).first()

        if not dashboard:
            return Response(
                {"error": "No hay dashboard por defecto"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(DashboardSerializer(dashboard).data)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Duplicate a dashboard."""
        dashboard = self.get_object()

        new_dashboard = Dashboard.objects.create(
            name=f"{dashboard.name} (copia)",
            description=dashboard.description,
            layout=dashboard.layout,
            widgets=dashboard.widgets,
            is_active=True,
            is_public=False,
            allowed_roles=dashboard.allowed_roles,
            created_by=request.user,
        )

        return Response(
            DashboardSerializer(new_dashboard).data,
            status=status.HTTP_201_CREATED,
        )


class UserDashboardViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user dashboard preferences."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserDashboardSerializer
    http_method_names = ["get", "put", "patch"]

    def get_queryset(self):
        return UserDashboard.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"])
    def my_dashboard(self, request):
        """Get current user's dashboard preference."""
        try:
            user_dashboard = UserDashboard.objects.get(user=request.user)
            return Response(UserDashboardSerializer(user_dashboard).data)
        except UserDashboard.DoesNotExist:
            # Return default dashboard
            default = Dashboard.objects.filter(is_default=True, is_active=True).first()
            if default:
                return Response({"dashboard": DashboardSerializer(default).data})
            return Response({"dashboard": None})

    @action(detail=False, methods=["post"])
    def select(self, request):
        """Select a dashboard for the current user."""
        dashboard_id = request.data.get("dashboard_id")

        if not dashboard_id:
            return Response(
                {"error": "dashboard_id requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            dashboard = Dashboard.objects.get(
                id=dashboard_id,
                is_active=True,
            )
        except Dashboard.DoesNotExist:
            return Response(
                {"error": "Dashboard no encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check access
        if not dashboard.is_public and not request.user.is_staff:
            if dashboard.created_by != request.user:
                return Response(
                    {"error": "No autorizado"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        user_dashboard, _ = UserDashboard.objects.update_or_create(
            user=request.user,
            defaults={"dashboard": dashboard},
        )

        return Response(UserDashboardSerializer(user_dashboard).data)

    @action(detail=False, methods=["patch"])
    def update_widgets(self, request):
        """Update custom widgets for user's dashboard."""
        custom_widgets = request.data.get("custom_widgets", [])

        user_dashboard, _ = UserDashboard.objects.get_or_create(
            user=request.user,
            defaults={"dashboard": None},
        )

        user_dashboard.custom_widgets = custom_widgets
        user_dashboard.save()

        return Response(UserDashboardSerializer(user_dashboard).data)
