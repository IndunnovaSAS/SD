"""
Admin configuration for notifications app.
"""

from django.contrib import admin

from .models import (
    Notification,
    NotificationTemplate,
    PushSubscription,
    UserNotificationPreference,
)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """Admin configuration for NotificationTemplate model."""

    list_display = ["name", "channel", "subject", "is_active", "created_at"]
    list_filter = ["channel", "is_active"]
    search_fields = ["name", "subject", "body"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin configuration for Notification model."""

    list_display = [
        "subject",
        "user",
        "channel",
        "status",
        "priority",
        "sent_at",
        "read_at",
    ]
    list_filter = ["status", "channel", "priority", "created_at"]
    search_fields = ["subject", "body", "user__email"]
    readonly_fields = [
        "created_at",
        "sent_at",
        "delivered_at",
        "read_at",
    ]
    raw_id_fields = ["user"]
    date_hierarchy = "created_at"


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    """Admin configuration for UserNotificationPreference model."""

    list_display = [
        "user",
        "email_enabled",
        "push_enabled",
        "sms_enabled",
        "in_app_enabled",
    ]
    list_filter = ["email_enabled", "push_enabled", "sms_enabled"]
    search_fields = ["user__email"]
    raw_id_fields = ["user"]


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    """Admin configuration for PushSubscription model."""

    list_display = [
        "user",
        "device_name",
        "device_type",
        "is_active",
        "last_used_at",
    ]
    list_filter = ["is_active", "device_type"]
    search_fields = ["user__email", "device_name"]
    raw_id_fields = ["user"]
