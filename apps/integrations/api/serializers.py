"""
Serializers for integrations API.
"""

from rest_framework import serializers

from apps.integrations.models import (
    DataMapping,
    ExternalSystem,
    IntegrationLog,
    Webhook,
    WebhookDelivery,
)


class ExternalSystemListSerializer(serializers.ModelSerializer):
    """List serializer for external systems."""

    type_display = serializers.CharField(
        source="get_system_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ExternalSystem
        fields = [
            "id",
            "name",
            "code",
            "system_type",
            "type_display",
            "status",
            "status_display",
            "is_active",
            "last_sync_at",
            "created_at",
        ]


class ExternalSystemSerializer(serializers.ModelSerializer):
    """Full serializer for external systems."""

    class Meta:
        model = ExternalSystem
        fields = [
            "id",
            "name",
            "code",
            "system_type",
            "description",
            "base_url",
            "api_version",
            "auth_type",
            "credentials",
            "headers",
            "settings",
            "status",
            "last_sync_at",
            "last_error",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["last_sync_at", "last_error", "created_at", "updated_at"]
        extra_kwargs = {
            "credentials": {"write_only": True},
        }


class ExternalSystemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating external systems."""

    class Meta:
        model = ExternalSystem
        fields = [
            "name",
            "code",
            "system_type",
            "description",
            "base_url",
            "api_version",
            "auth_type",
            "credentials",
            "headers",
            "settings",
        ]


class IntegrationLogSerializer(serializers.ModelSerializer):
    """Serializer for integration logs."""

    system_name = serializers.CharField(
        source="external_system.name", read_only=True
    )
    direction_display = serializers.CharField(
        source="get_direction_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = IntegrationLog
        fields = [
            "id",
            "external_system",
            "system_name",
            "operation",
            "direction",
            "direction_display",
            "status",
            "status_display",
            "request_data",
            "response_data",
            "http_status",
            "duration_ms",
            "error_message",
            "records_processed",
            "records_failed",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class DataMappingSerializer(serializers.ModelSerializer):
    """Serializer for data mappings."""

    system_name = serializers.CharField(
        source="external_system.name", read_only=True
    )

    class Meta:
        model = DataMapping
        fields = [
            "id",
            "external_system",
            "system_name",
            "entity_type",
            "external_field",
            "internal_field",
            "transformation",
            "is_required",
            "default_value",
            "is_active",
        ]


class WebhookListSerializer(serializers.ModelSerializer):
    """List serializer for webhooks."""

    event_count = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    class Meta:
        model = Webhook
        fields = [
            "id",
            "name",
            "url",
            "events",
            "event_count",
            "is_active",
            "last_triggered_at",
            "created_by_name",
            "created_at",
        ]

    def get_event_count(self, obj):
        return len(obj.events) if obj.events else 0


class WebhookSerializer(serializers.ModelSerializer):
    """Full serializer for webhooks."""

    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    class Meta:
        model = Webhook
        fields = [
            "id",
            "name",
            "url",
            "events",
            "secret_key",
            "headers",
            "is_active",
            "retry_count",
            "timeout_seconds",
            "last_triggered_at",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "last_triggered_at",
            "created_by",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "secret_key": {"write_only": True},
        }


class WebhookDeliverySerializer(serializers.ModelSerializer):
    """Serializer for webhook deliveries."""

    webhook_name = serializers.CharField(source="webhook.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = WebhookDelivery
        fields = [
            "id",
            "webhook",
            "webhook_name",
            "event",
            "payload",
            "status",
            "status_display",
            "http_status",
            "response_body",
            "attempt_count",
            "next_retry_at",
            "duration_ms",
            "error_message",
            "created_at",
            "delivered_at",
        ]


class WebhookTestSerializer(serializers.Serializer):
    """Serializer for testing a webhook."""

    event = serializers.ChoiceField(choices=Webhook.Event.choices)
    payload = serializers.JSONField(required=False, default=dict)
