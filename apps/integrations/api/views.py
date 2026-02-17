"""
ViewSets for integrations API.
"""

from django.db.models import Q
from django.utils import timezone

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.integrations.models import (
    DataMapping,
    ExternalSystem,
    IntegrationLog,
    Webhook,
    WebhookDelivery,
)

from .serializers import (
    DataMappingSerializer,
    ExternalSystemCreateSerializer,
    ExternalSystemListSerializer,
    ExternalSystemSerializer,
    IntegrationLogSerializer,
    WebhookDeliverySerializer,
    WebhookListSerializer,
    WebhookSerializer,
    WebhookTestSerializer,
)


class IsStaffPermission(permissions.BasePermission):
    """Only allow staff users."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff


class ExternalSystemViewSet(viewsets.ModelViewSet):
    """ViewSet for managing external systems."""

    permission_classes = [IsStaffPermission]

    def get_queryset(self):
        queryset = ExternalSystem.objects.all()

        # Filter by type
        system_type = self.request.query_params.get("type")
        if system_type:
            queryset = queryset.filter(system_type=system_type)

        # Filter by status
        system_status = self.request.query_params.get("status")
        if system_status:
            queryset = queryset.filter(status=system_status)

        # Filter by active
        is_active = self.request.query_params.get("active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # Search
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(code__icontains=search)
                | Q(description__icontains=search)
            )

        return queryset.order_by("name")

    def get_serializer_class(self):
        if self.action == "list":
            return ExternalSystemListSerializer
        if self.action == "create":
            return ExternalSystemCreateSerializer
        return ExternalSystemSerializer

    @action(detail=True, methods=["post"])
    def test_connection(self, request, pk=None):
        """Test connection to external system."""
        self.get_object()

        # In a real implementation, attempt to connect to the system
        # For now, return a simulated result
        return Response(
            {
                "success": True,
                "message": "Conexión exitosa",
                "response_time_ms": 150,
            }
        )

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        """Trigger sync with external system."""
        system = self.get_object()

        if not system.is_active:
            return Response(
                {"error": "El sistema está inactivo"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if system.status == ExternalSystem.Status.MAINTENANCE:
            return Response(
                {"error": "El sistema está en mantenimiento"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create an integration log for the sync
        log = IntegrationLog.objects.create(
            external_system=system,
            operation="sync",
            direction=IntegrationLog.Direction.INBOUND,
            status=IntegrationLog.Status.SUCCESS,
            records_processed=0,
        )

        system.last_sync_at = timezone.now()
        system.save()

        return Response(
            {
                "message": "Sincronización iniciada",
                "log_id": log.id,
            }
        )

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        """Toggle system active status."""
        system = self.get_object()
        system.is_active = not system.is_active
        system.save()
        return Response(ExternalSystemSerializer(system).data)

    @action(detail=True, methods=["get"])
    def mappings(self, request, pk=None):
        """Get data mappings for a system."""
        system = self.get_object()
        mappings = system.mappings.filter(is_active=True).order_by("entity_type")
        return Response(DataMappingSerializer(mappings, many=True).data)

    @action(detail=True, methods=["get"])
    def logs(self, request, pk=None):
        """Get recent logs for a system."""
        system = self.get_object()
        logs = system.logs.order_by("-created_at")[:50]
        return Response(IntegrationLogSerializer(logs, many=True).data)


class IntegrationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing integration logs."""

    permission_classes = [IsStaffPermission]
    serializer_class = IntegrationLogSerializer

    def get_queryset(self):
        queryset = IntegrationLog.objects.select_related("external_system")

        # Filter by system
        system_id = self.request.query_params.get("system")
        if system_id:
            queryset = queryset.filter(external_system_id=system_id)

        # Filter by operation
        operation = self.request.query_params.get("operation")
        if operation:
            queryset = queryset.filter(operation=operation)

        # Filter by direction
        direction = self.request.query_params.get("direction")
        if direction:
            queryset = queryset.filter(direction=direction)

        # Filter by status
        log_status = self.request.query_params.get("status")
        if log_status:
            queryset = queryset.filter(status=log_status)

        # Filter by date range
        date_from = self.request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.order_by("-created_at")

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get integration statistics."""
        from django.db.models import Avg, Count, Sum

        # Last 24 hours stats
        since = timezone.now() - timezone.timedelta(hours=24)
        logs = IntegrationLog.objects.filter(created_at__gte=since)

        stats = logs.aggregate(
            total=Count("id"),
            successful=Count("id", filter=Q(status="success")),
            failed=Count("id", filter=Q(status="error")),
            records_processed=Sum("records_processed"),
            records_failed=Sum("records_failed"),
            avg_duration=Avg("duration_ms"),
        )

        return Response(
            {
                "period": "24h",
                **stats,
            }
        )


class DataMappingViewSet(viewsets.ModelViewSet):
    """ViewSet for managing data mappings."""

    permission_classes = [IsStaffPermission]
    serializer_class = DataMappingSerializer

    def get_queryset(self):
        queryset = DataMapping.objects.select_related("external_system")

        # Filter by system
        system_id = self.request.query_params.get("system")
        if system_id:
            queryset = queryset.filter(external_system_id=system_id)

        # Filter by entity type
        entity_type = self.request.query_params.get("entity")
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)

        # Filter by active
        is_active = self.request.query_params.get("active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset.order_by("external_system", "entity_type", "external_field")

    @action(detail=False, methods=["get"])
    def entity_types(self, request):
        """Get list of available entity types."""
        types = (
            DataMapping.objects.values_list("entity_type", flat=True)
            .distinct()
            .order_by("entity_type")
        )

        return Response(list(types))

    @action(detail=False, methods=["post"])
    def bulk_create(self, request):
        """Create multiple mappings at once."""
        mappings = request.data.get("mappings", [])

        if not mappings:
            return Response(
                {"error": "No se proporcionaron mapeos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = []
        errors = []

        for mapping_data in mappings:
            serializer = DataMappingSerializer(data=mapping_data)
            if serializer.is_valid():
                serializer.save()
                created.append(serializer.data)
            else:
                errors.append(
                    {
                        "data": mapping_data,
                        "errors": serializer.errors,
                    }
                )

        return Response(
            {
                "created": len(created),
                "errors": len(errors),
                "error_details": errors,
            }
        )


class WebhookViewSet(viewsets.ModelViewSet):
    """ViewSet for managing webhooks."""

    permission_classes = [IsStaffPermission]

    def get_queryset(self):
        queryset = Webhook.objects.select_related("created_by")

        # Filter by active
        is_active = self.request.query_params.get("active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # Search
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(url__icontains=search))

        return queryset.order_by("name")

    def get_serializer_class(self):
        if self.action == "list":
            return WebhookListSerializer
        if self.action == "test":
            return WebhookTestSerializer
        return WebhookSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        """Toggle webhook active status."""
        webhook = self.get_object()
        webhook.is_active = not webhook.is_active
        webhook.save()
        return Response(WebhookSerializer(webhook).data)

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        """Test a webhook with sample data."""
        webhook = self.get_object()

        serializer = WebhookTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event = serializer.validated_data["event"]
        payload = serializer.validated_data.get("payload", {"test": True})

        # Create a test delivery
        delivery = WebhookDelivery.objects.create(
            webhook=webhook,
            event=event,
            payload=payload,
            status=WebhookDelivery.Status.PENDING,
        )

        # In a real implementation, send the webhook and update the delivery
        # For now, simulate success
        delivery.status = WebhookDelivery.Status.SUCCESS
        delivery.http_status = 200
        delivery.attempt_count = 1
        delivery.duration_ms = 100
        delivery.delivered_at = timezone.now()
        delivery.save()

        webhook.last_triggered_at = timezone.now()
        webhook.save()

        return Response(
            {
                "success": True,
                "delivery_id": delivery.id,
            }
        )

    @action(detail=True, methods=["get"])
    def deliveries(self, request, pk=None):
        """Get recent deliveries for a webhook."""
        webhook = self.get_object()
        deliveries = webhook.deliveries.order_by("-created_at")[:50]
        return Response(WebhookDeliverySerializer(deliveries, many=True).data)


class WebhookDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing webhook deliveries."""

    permission_classes = [IsStaffPermission]
    serializer_class = WebhookDeliverySerializer

    def get_queryset(self):
        queryset = WebhookDelivery.objects.select_related("webhook")

        # Filter by webhook
        webhook_id = self.request.query_params.get("webhook")
        if webhook_id:
            queryset = queryset.filter(webhook_id=webhook_id)

        # Filter by event
        event = self.request.query_params.get("event")
        if event:
            queryset = queryset.filter(event=event)

        # Filter by status
        delivery_status = self.request.query_params.get("status")
        if delivery_status:
            queryset = queryset.filter(status=delivery_status)

        # Filter by date range
        date_from = self.request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.order_by("-created_at")

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """Retry a failed delivery."""
        delivery = self.get_object()

        if delivery.status == WebhookDelivery.Status.SUCCESS:
            return Response(
                {"error": "Esta entrega ya fue exitosa"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # In a real implementation, re-send the webhook
        delivery.status = WebhookDelivery.Status.RETRYING
        delivery.attempt_count += 1
        delivery.save()

        return Response(
            {
                "message": "Reintento en proceso",
                "attempt": delivery.attempt_count,
            }
        )

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """Get pending/failed deliveries."""
        deliveries = WebhookDelivery.objects.filter(
            status__in=[
                WebhookDelivery.Status.PENDING,
                WebhookDelivery.Status.FAILED,
                WebhookDelivery.Status.RETRYING,
            ]
        ).order_by("-created_at")[:100]

        return Response(WebhookDeliverySerializer(deliveries, many=True).data)
