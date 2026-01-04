"""
Serializers for notifications API.
"""

from rest_framework import serializers

from apps.notifications.models import (
    Notification,
    NotificationTemplate,
    PushSubscription,
    UserNotificationPreference,
)


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for NotificationTemplate model."""

    class Meta:
        model = NotificationTemplate
        fields = [
            "id",
            "name",
            "description",
            "subject",
            "body",
            "html_body",
            "channel",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""

    template_name = serializers.CharField(source="template.name", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "user",
            "template",
            "template_name",
            "channel",
            "subject",
            "body",
            "status",
            "priority",
            "action_url",
            "action_text",
            "metadata",
            "sent_at",
            "delivered_at",
            "read_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "status",
            "sent_at",
            "delivered_at",
            "read_at",
            "created_at",
        ]


class NotificationListSerializer(serializers.ModelSerializer):
    """Simplified serializer for notification lists."""

    class Meta:
        model = Notification
        fields = [
            "id",
            "channel",
            "subject",
            "status",
            "priority",
            "action_url",
            "read_at",
            "created_at",
        ]


class NotificationCreateSerializer(serializers.Serializer):
    """Serializer for creating notifications."""

    user_id = serializers.IntegerField(required=False)
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
    )
    template_id = serializers.IntegerField(required=False)
    channel = serializers.ChoiceField(
        choices=NotificationTemplate.Channel.choices,
        required=False,
    )
    subject = serializers.CharField(max_length=200)
    body = serializers.CharField()
    priority = serializers.ChoiceField(
        choices=Notification.Priority.choices,
        default=Notification.Priority.NORMAL,
    )
    action_url = serializers.URLField(required=False, allow_blank=True)
    action_text = serializers.CharField(max_length=100, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)


class UserNotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for UserNotificationPreference model."""

    class Meta:
        model = UserNotificationPreference
        fields = [
            "id",
            "email_enabled",
            "push_enabled",
            "sms_enabled",
            "in_app_enabled",
            "course_reminders",
            "assessment_results",
            "certificate_issued",
            "new_assignments",
            "deadline_reminders",
            "lesson_learned_updates",
            "quiet_hours_start",
            "quiet_hours_end",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class PushSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for PushSubscription model."""

    class Meta:
        model = PushSubscription
        fields = [
            "id",
            "endpoint",
            "p256dh_key",
            "auth_key",
            "device_name",
            "device_type",
            "is_active",
            "created_at",
            "last_used_at",
        ]
        read_only_fields = ["id", "created_at", "last_used_at"]


class MarkReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read."""

    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
    )
    mark_all = serializers.BooleanField(default=False)
