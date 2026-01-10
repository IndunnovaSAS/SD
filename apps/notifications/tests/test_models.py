"""
Tests for notification models.

Covers:
- Notification model
- NotificationTemplate model
- UserNotificationPreference model
- PushSubscription model
"""

import pytest
from datetime import time, timedelta
from django.db import IntegrityError
from django.utils import timezone

from apps.notifications.models import (
    Notification,
    NotificationTemplate,
    PushSubscription,
    UserNotificationPreference,
)

from .factories import (
    NotificationFactory,
    NotificationTemplateFactory,
    PushSubscriptionFactory,
    UserFactory,
    UserNotificationPreferenceFactory,
    SentNotificationFactory,
    ReadNotificationFactory,
    FailedNotificationFactory,
    EmailTemplateFactory,
    PushTemplateFactory,
    SMSTemplateFactory,
    InactiveTemplateFactory,
)


@pytest.mark.django_db
class TestNotificationTemplate:
    """Tests for NotificationTemplate model."""

    def test_create_notification_template(self):
        """Test creating a notification template."""
        template = NotificationTemplateFactory()

        assert template.pk is not None
        assert template.name is not None
        assert template.is_active is True
        assert template.channel == NotificationTemplate.Channel.IN_APP

    def test_template_str_representation(self):
        """Test string representation of template."""
        template = NotificationTemplateFactory(name="Welcome Email")

        assert str(template) == "Welcome Email"

    def test_template_channels(self):
        """Test all template channel choices."""
        email_template = EmailTemplateFactory()
        push_template = PushTemplateFactory()
        sms_template = SMSTemplateFactory()
        in_app_template = NotificationTemplateFactory()

        assert email_template.channel == NotificationTemplate.Channel.EMAIL
        assert push_template.channel == NotificationTemplate.Channel.PUSH
        assert sms_template.channel == NotificationTemplate.Channel.SMS
        assert in_app_template.channel == NotificationTemplate.Channel.IN_APP

    def test_template_unique_name_constraint(self):
        """Test that template names must be unique."""
        NotificationTemplateFactory(name="Unique Template")

        with pytest.raises(IntegrityError):
            NotificationTemplate.objects.create(
                name="Unique Template",
                subject="Test",
                body="Test body",
            )

    def test_inactive_template(self):
        """Test inactive template creation."""
        template = InactiveTemplateFactory()

        assert template.is_active is False

    def test_template_with_html_body(self):
        """Test template with HTML body."""
        template = EmailTemplateFactory(
            subject="Test Subject",
            body="Plain text body",
            html_body="<html><body><p>HTML body</p></body></html>",
        )

        assert template.html_body is not None
        assert "<html>" in template.html_body

    def test_template_timestamps(self):
        """Test that created_at and updated_at are set."""
        template = NotificationTemplateFactory()

        assert template.created_at is not None
        assert template.updated_at is not None

    def test_template_with_placeholders(self):
        """Test template body with placeholders."""
        template = NotificationTemplateFactory(
            subject="Hola {{user_name}}",
            body="Bienvenido {{user_name}}, tu curso {{course_name}} te espera.",
        )

        assert "{{user_name}}" in template.subject
        assert "{{user_name}}" in template.body
        assert "{{course_name}}" in template.body


@pytest.mark.django_db
class TestNotification:
    """Tests for Notification model."""

    def test_create_notification(self):
        """Test creating a notification."""
        notification = NotificationFactory()

        assert notification.pk is not None
        assert notification.user is not None
        assert notification.status == Notification.Status.PENDING

    def test_notification_str_representation(self):
        """Test string representation of notification."""
        user = UserFactory(email="john@test.com")
        notification = NotificationFactory(
            user=user,
            subject="Test Subject",
        )

        assert "john@test.com" in str(notification)
        assert "Test Subject" in str(notification)

    def test_notification_status_choices(self):
        """Test all notification status choices."""
        pending = NotificationFactory(status=Notification.Status.PENDING)
        sent = SentNotificationFactory()
        read = ReadNotificationFactory()
        failed = FailedNotificationFactory()

        assert pending.status == Notification.Status.PENDING
        assert sent.status == Notification.Status.SENT
        assert read.status == Notification.Status.READ
        assert failed.status == Notification.Status.FAILED

    def test_notification_priority_choices(self):
        """Test all notification priority choices."""
        low = NotificationFactory(priority=Notification.Priority.LOW)
        normal = NotificationFactory(priority=Notification.Priority.NORMAL)
        high = NotificationFactory(priority=Notification.Priority.HIGH)
        urgent = NotificationFactory(priority=Notification.Priority.URGENT)

        assert low.priority == Notification.Priority.LOW
        assert normal.priority == Notification.Priority.NORMAL
        assert high.priority == Notification.Priority.HIGH
        assert urgent.priority == Notification.Priority.URGENT

    def test_notification_with_template(self):
        """Test notification with associated template."""
        template = NotificationTemplateFactory()
        notification = NotificationFactory(template=template)

        assert notification.template == template
        assert notification.template.name == template.name

    def test_notification_channel_choices(self):
        """Test all notification channel choices."""
        email = NotificationFactory(channel=NotificationTemplate.Channel.EMAIL)
        push = NotificationFactory(channel=NotificationTemplate.Channel.PUSH)
        sms = NotificationFactory(channel=NotificationTemplate.Channel.SMS)
        in_app = NotificationFactory(channel=NotificationTemplate.Channel.IN_APP)

        assert email.channel == NotificationTemplate.Channel.EMAIL
        assert push.channel == NotificationTemplate.Channel.PUSH
        assert sms.channel == NotificationTemplate.Channel.SMS
        assert in_app.channel == NotificationTemplate.Channel.IN_APP

    def test_notification_with_action(self):
        """Test notification with action URL and text."""
        notification = NotificationFactory(
            action_url="https://example.com/action",
            action_text="Ver detalles",
        )

        assert notification.action_url == "https://example.com/action"
        assert notification.action_text == "Ver detalles"

    def test_notification_with_metadata(self):
        """Test notification with metadata."""
        metadata = {"course_id": 123, "lesson_id": 456}
        notification = NotificationFactory(metadata=metadata)

        assert notification.metadata == metadata
        assert notification.metadata["course_id"] == 123

    def test_notification_timestamps(self):
        """Test notification timestamp fields."""
        now = timezone.now()
        notification = NotificationFactory(
            sent_at=now,
            delivered_at=now + timedelta(seconds=30),
            read_at=now + timedelta(minutes=5),
        )

        assert notification.sent_at is not None
        assert notification.delivered_at is not None
        assert notification.read_at is not None
        assert notification.delivered_at > notification.sent_at
        assert notification.read_at > notification.delivered_at

    def test_notification_retry_count(self):
        """Test notification retry count."""
        notification = FailedNotificationFactory(retry_count=3)

        assert notification.retry_count == 3
        assert notification.status == Notification.Status.FAILED

    def test_notification_error_message(self):
        """Test notification error message."""
        notification = FailedNotificationFactory(
            error_message="SMTP connection failed"
        )

        assert notification.error_message == "SMTP connection failed"

    def test_notification_user_cascade_delete(self):
        """Test that notifications are deleted when user is deleted."""
        user = UserFactory()
        NotificationFactory(user=user)
        NotificationFactory(user=user)

        user_id = user.id
        user.delete()

        assert Notification.objects.filter(user_id=user_id).count() == 0

    def test_notification_template_set_null(self):
        """Test that notification template is set to null when template is deleted."""
        template = NotificationTemplateFactory()
        notification = NotificationFactory(template=template)

        notification_id = notification.id
        template.delete()

        notification.refresh_from_db()
        assert notification.template is None

    def test_notification_ordering(self):
        """Test that notifications are ordered by created_at descending."""
        user = UserFactory()
        old_notification = NotificationFactory(user=user)
        new_notification = NotificationFactory(user=user)

        notifications = Notification.objects.filter(user=user)

        assert list(notifications) == [new_notification, old_notification]


@pytest.mark.django_db
class TestUserNotificationPreference:
    """Tests for UserNotificationPreference model."""

    def test_create_preference(self):
        """Test creating user notification preferences."""
        preference = UserNotificationPreferenceFactory()

        assert preference.pk is not None
        assert preference.user is not None

    def test_preference_str_representation(self):
        """Test string representation of preferences."""
        user = UserFactory(email="prefs@test.com")
        preference = UserNotificationPreferenceFactory(user=user)

        assert "prefs@test.com" in str(preference)

    def test_preference_defaults(self):
        """Test default preference values."""
        preference = UserNotificationPreferenceFactory()

        assert preference.email_enabled is True
        assert preference.push_enabled is True
        assert preference.sms_enabled is False
        assert preference.in_app_enabled is True

    def test_preference_notification_types(self):
        """Test notification type preferences."""
        preference = UserNotificationPreferenceFactory(
            course_reminders=False,
            assessment_results=True,
            certificate_issued=True,
            new_assignments=False,
            deadline_reminders=True,
            lesson_learned_updates=False,
        )

        assert preference.course_reminders is False
        assert preference.assessment_results is True
        assert preference.certificate_issued is True
        assert preference.new_assignments is False
        assert preference.deadline_reminders is True
        assert preference.lesson_learned_updates is False

    def test_preference_quiet_hours(self):
        """Test quiet hours settings."""
        preference = UserNotificationPreferenceFactory(
            quiet_hours_start=time(22, 0),
            quiet_hours_end=time(7, 0),
        )

        assert preference.quiet_hours_start == time(22, 0)
        assert preference.quiet_hours_end == time(7, 0)

    def test_preference_no_quiet_hours(self):
        """Test preferences without quiet hours."""
        preference = UserNotificationPreferenceFactory(
            quiet_hours_start=None,
            quiet_hours_end=None,
        )

        assert preference.quiet_hours_start is None
        assert preference.quiet_hours_end is None

    def test_preference_user_unique_constraint(self):
        """Test that each user can have only one preference record."""
        user = UserFactory()
        UserNotificationPreferenceFactory(user=user)

        with pytest.raises(IntegrityError):
            UserNotificationPreference.objects.create(user=user)

    def test_preference_cascade_delete(self):
        """Test that preferences are deleted when user is deleted."""
        user = UserFactory()
        UserNotificationPreferenceFactory(user=user)

        user_id = user.id
        user.delete()

        assert UserNotificationPreference.objects.filter(user_id=user_id).count() == 0

    def test_preference_timestamps(self):
        """Test preference timestamp fields."""
        preference = UserNotificationPreferenceFactory()

        assert preference.created_at is not None
        assert preference.updated_at is not None

    def test_preference_all_channels_disabled(self):
        """Test preferences with all channels disabled."""
        preference = UserNotificationPreferenceFactory(
            email_enabled=False,
            push_enabled=False,
            sms_enabled=False,
            in_app_enabled=False,
        )

        assert not any([
            preference.email_enabled,
            preference.push_enabled,
            preference.sms_enabled,
            preference.in_app_enabled,
        ])


@pytest.mark.django_db
class TestPushSubscription:
    """Tests for PushSubscription model."""

    def test_create_push_subscription(self):
        """Test creating a push subscription."""
        subscription = PushSubscriptionFactory()

        assert subscription.pk is not None
        assert subscription.user is not None
        assert subscription.endpoint is not None
        assert subscription.is_active is True

    def test_subscription_str_representation(self):
        """Test string representation of subscription."""
        user = UserFactory(email="push@test.com")
        subscription = PushSubscriptionFactory(
            user=user,
            device_name="iPhone 15 Pro",
        )

        assert "push@test.com" in str(subscription)
        assert "iPhone 15 Pro" in str(subscription)

    def test_subscription_str_without_device_name(self):
        """Test string representation without device name."""
        user = UserFactory(email="push@test.com")
        subscription = PushSubscriptionFactory(
            user=user,
            device_name="",
        )

        assert "Unknown" in str(subscription)

    def test_subscription_keys(self):
        """Test subscription key fields."""
        subscription = PushSubscriptionFactory(
            p256dh_key="test_p256dh_key",
            auth_key="test_auth_key",
        )

        assert subscription.p256dh_key == "test_p256dh_key"
        assert subscription.auth_key == "test_auth_key"

    def test_subscription_device_info(self):
        """Test subscription device information."""
        subscription = PushSubscriptionFactory(
            device_name="Chrome on Windows",
            device_type="desktop",
        )

        assert subscription.device_name == "Chrome on Windows"
        assert subscription.device_type == "desktop"

    def test_subscription_timestamps(self):
        """Test subscription timestamp fields."""
        subscription = PushSubscriptionFactory()

        assert subscription.created_at is not None
        assert subscription.last_used_at is not None

    def test_inactive_subscription(self):
        """Test inactive subscription."""
        from .factories import InactivePushSubscriptionFactory

        subscription = InactivePushSubscriptionFactory()

        assert subscription.is_active is False

    def test_user_can_have_multiple_subscriptions(self):
        """Test that a user can have multiple push subscriptions."""
        user = UserFactory()
        sub1 = PushSubscriptionFactory(user=user, device_name="Mobile")
        sub2 = PushSubscriptionFactory(user=user, device_name="Desktop")

        assert PushSubscription.objects.filter(user=user).count() == 2
        assert sub1.device_name == "Mobile"
        assert sub2.device_name == "Desktop"

    def test_subscription_cascade_delete(self):
        """Test that subscriptions are deleted when user is deleted."""
        user = UserFactory()
        PushSubscriptionFactory(user=user)
        PushSubscriptionFactory(user=user)

        user_id = user.id
        user.delete()

        assert PushSubscription.objects.filter(user_id=user_id).count() == 0

    def test_subscription_endpoint_url(self):
        """Test subscription endpoint URL format."""
        subscription = PushSubscriptionFactory(
            endpoint="https://fcm.googleapis.com/fcm/send/abc123"
        )

        assert subscription.endpoint.startswith("https://")


@pytest.mark.django_db
class TestNotificationRelationships:
    """Tests for relationships between notification models."""

    def test_user_notifications_relationship(self):
        """Test user to notifications relationship."""
        user = UserFactory()
        NotificationFactory(user=user)
        NotificationFactory(user=user)
        NotificationFactory(user=user)

        assert user.notifications.count() == 3

    def test_user_push_subscriptions_relationship(self):
        """Test user to push subscriptions relationship."""
        user = UserFactory()
        PushSubscriptionFactory(user=user)
        PushSubscriptionFactory(user=user)

        assert user.push_subscriptions.count() == 2

    def test_template_notifications_relationship(self):
        """Test template to notifications relationship."""
        template = NotificationTemplateFactory()
        NotificationFactory(template=template)
        NotificationFactory(template=template)

        assert template.notifications.count() == 2

    def test_user_notification_preferences_relationship(self):
        """Test user to notification preferences one-to-one relationship."""
        user = UserFactory()
        preference = UserNotificationPreferenceFactory(user=user)

        assert user.notification_preferences == preference
        assert preference.user == user
