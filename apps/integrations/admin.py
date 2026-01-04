"""
Admin configuration for integrations app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    DataMapping,
    ExternalSystem,
    IntegrationLog,
    Webhook,
    WebhookDelivery,
)


class DataMappingInline(admin.TabularInline):
    """Inline for data mappings in external system admin."""

    model = DataMapping
    extra = 1


@admin.register(ExternalSystem)
class ExternalSystemAdmin(admin.ModelAdmin):
    """Admin configuration for ExternalSystem model."""

    list_display = [
        "name",
        "code",
        "system_type",
        "status",
        "is_active",
        "last_sync_at",
    ]
    list_filter = ["system_type", "status", "is_active"]
    search_fields = ["name", "code", "description"]
    readonly_fields = ["last_sync_at", "created_at", "updated_at"]
    inlines = [DataMappingInline]

    fieldsets = [
        (
            None,
            {
                "fields": ["name", "code", "system_type", "description"],
            },
        ),
        (
            _("Conexión"),
            {
                "fields": ["base_url", "api_version", "auth_type", "credentials", "headers"],
            },
        ),
        (
            _("Configuración"),
            {
                "fields": ["settings", "status", "is_active"],
            },
        ),
        (
            _("Estado"),
            {
                "fields": ["last_sync_at", "last_error"],
                "classes": ["collapse"],
            },
        ),
    ]


@admin.register(IntegrationLog)
class IntegrationLogAdmin(admin.ModelAdmin):
    """Admin configuration for IntegrationLog model."""

    list_display = [
        "external_system",
        "operation",
        "direction",
        "status",
        "http_status",
        "records_processed",
        "created_at",
    ]
    list_filter = ["status", "direction", "external_system", "created_at"]
    search_fields = ["operation", "error_message"]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    """Admin configuration for Webhook model."""

    list_display = [
        "name",
        "url",
        "is_active",
        "retry_count",
        "last_triggered_at",
    ]
    list_filter = ["is_active"]
    search_fields = ["name", "url"]
    readonly_fields = ["last_triggered_at", "created_at", "updated_at"]


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    """Admin configuration for WebhookDelivery model."""

    list_display = [
        "webhook",
        "event",
        "status",
        "http_status",
        "attempt_count",
        "created_at",
    ]
    list_filter = ["status", "event", "created_at"]
    readonly_fields = ["created_at", "delivered_at"]
    date_hierarchy = "created_at"
