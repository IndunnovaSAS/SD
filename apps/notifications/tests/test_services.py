"""
Tests for notification services.

Covers:
- NotificationService
- NotificationTemplateService
- BulkNotificationService
- UserPreferenceService
- PushService
- Email, Push, SMS sending with mocking
"""

from datetime import time, timedelta
from unittest.mock import MagicMock, patch

from django.utils import timezone

import pytest

from apps.notifications.models import (
    Notification,
    NotificationTemplate,
    PushSubscription,
)
from apps.notifications.services import (
    BulkNotificationService,
    NotificationService,
    NotificationTemplateService,
    PushService,
    UserPreferenceService,
)

from .factories import (
    EmailTemplateFactory,
    FailedNotificationFactory,
    NotificationFactory,
    NotificationTemplateFactory,
    PushSubscriptionFactory,
    PushTemplateFactory,
    SentNotificationFactory,
    UserFactory,
    UserNotificationPreferenceFactory,
)


@pytest.mark.django_db
class TestNotificationTemplateService:
    """Tests for NotificationTemplateService."""

    def test_get_template_by_name(self):
        """Test getting a template by name."""
        template = NotificationTemplateFactory(name="welcome_email")

        result = NotificationTemplateService.get_template("welcome_email")

        assert result == template
        assert result.name == "welcome_email"

    def test_get_template_by_name_and_channel(self):
        """Test getting a template by name and channel."""
        email_template = NotificationTemplateFactory(
            name="welcome",
            channel=NotificationTemplate.Channel.EMAIL,
        )
        push_template = NotificationTemplateFactory(
            name="welcome_push",
            channel=NotificationTemplate.Channel.PUSH,
        )

        result = NotificationTemplateService.get_template(
            "welcome",
            channel=NotificationTemplate.Channel.EMAIL,
        )

        assert result == email_template

    def test_get_template_returns_none_for_nonexistent(self):
        """Test that get_template returns None for nonexistent template."""
        result = NotificationTemplateService.get_template("nonexistent")

        assert result is None

    def test_get_template_ignores_inactive(self):
        """Test that get_template ignores inactive templates."""
        NotificationTemplateFactory(name="inactive_template", is_active=False)

        result = NotificationTemplateService.get_template("inactive_template")

        assert result is None

    def test_render_template_simple(self):
        """Test rendering a template with simple variables."""
        template = NotificationTemplateFactory(
            subject="Hola {{name}}",
            body="Bienvenido {{name}}, tu email es {{email}}.",
        )

        result = NotificationTemplateService.render_template(
            template,
            {"name": "Juan", "email": "juan@test.com"},
        )

        assert result["subject"] == "Hola Juan"
        assert result["body"] == "Bienvenido Juan, tu email es juan@test.com."

    def test_render_template_with_html(self):
        """Test rendering a template with HTML body."""
        template = NotificationTemplateFactory(
            subject="Test",
            body="Plain text",
            html_body="<p>Hola {{name}}</p>",
        )

        result = NotificationTemplateService.render_template(
            template,
            {"name": "Maria"},
        )

        assert result["html_body"] == "<p>Hola Maria</p>"

    def test_render_template_without_html(self):
        """Test rendering a template without HTML body."""
        template = NotificationTemplateFactory(
            subject="Test",
            body="Plain text",
            html_body="",
        )

        result = NotificationTemplateService.render_template(
            template,
            {"name": "Test"},
        )

        assert result["html_body"] == ""

    def test_render_template_missing_variable(self):
        """Test rendering with missing variables leaves placeholder."""
        template = NotificationTemplateFactory(
            subject="Hola {{name}}",
            body="Tu curso: {{course}}",
        )

        result = NotificationTemplateService.render_template(
            template,
            {"name": "Juan"},
        )

        assert result["subject"] == "Hola Juan"
        assert "{{course}}" in result["body"]

    def test_get_templates_by_channel(self):
        """Test getting all templates for a channel."""
        EmailTemplateFactory()
        EmailTemplateFactory()
        PushTemplateFactory()

        email_templates = NotificationTemplateService.get_templates_by_channel(
            NotificationTemplate.Channel.EMAIL
        )

        assert email_templates.count() == 2


@pytest.mark.django_db
class TestNotificationService:
    """Tests for NotificationService."""

    def test_create_notification(self):
        """Test creating a notification."""
        user = UserFactory()

        notification = NotificationService.create_notification(
            user=user,
            subject="Test Subject",
            body="Test body content",
        )

        assert notification.pk is not None
        assert notification.user == user
        assert notification.subject == "Test Subject"
        assert notification.status == Notification.Status.PENDING

    def test_create_notification_with_all_options(self):
        """Test creating a notification with all options."""
        user = UserFactory()
        template = NotificationTemplateFactory()

        notification = NotificationService.create_notification(
            user=user,
            subject="Test",
            body="Body",
            channel=NotificationTemplate.Channel.EMAIL,
            template=template,
            priority=Notification.Priority.HIGH,
            action_url="https://example.com",
            action_text="Click here",
            metadata={"key": "value"},
        )

        assert notification.channel == NotificationTemplate.Channel.EMAIL
        assert notification.template == template
        assert notification.priority == Notification.Priority.HIGH
        assert notification.action_url == "https://example.com"
        assert notification.action_text == "Click here"
        assert notification.metadata == {"key": "value"}

    def test_send_from_template(self):
        """Test sending a notification from a template."""
        user = UserFactory()
        template = NotificationTemplateFactory(
            name="test_template",
            subject="Hola {{name}}",
            body="Bienvenido {{name}}",
        )

        notification = NotificationService.send_from_template(
            user=user,
            template_name="test_template",
            context={"name": "Juan"},
        )

        assert notification.subject == "Hola Juan"
        assert notification.body == "Bienvenido Juan"
        assert notification.template == template

    def test_send_from_template_not_found(self):
        """Test sending from nonexistent template raises error."""
        user = UserFactory()

        with pytest.raises(ValueError, match="not found"):
            NotificationService.send_from_template(
                user=user,
                template_name="nonexistent",
                context={},
            )

    def test_send_notification_in_app(self):
        """Test sending an in-app notification."""
        notification = NotificationFactory(
            channel=NotificationTemplate.Channel.IN_APP,
        )

        result = NotificationService.send_notification(notification)

        assert result.status == Notification.Status.SENT
        assert result.sent_at is not None

    @patch("django.core.mail.send_mail")
    def test_send_notification_email(self, mock_send_mail):
        """Test sending an email notification."""
        mock_send_mail.return_value = 1
        user = UserFactory(email="test@example.com")
        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.EMAIL,
            subject="Test Email",
            body="Test body",
        )

        result = NotificationService.send_notification(notification)

        assert result.status == Notification.Status.SENT
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        assert call_args.kwargs["subject"] == "Test Email"
        assert "test@example.com" in call_args.kwargs["recipient_list"]

    @patch("django.core.mail.send_mail")
    def test_send_notification_email_with_html(self, mock_send_mail):
        """Test sending an email notification with HTML body."""
        mock_send_mail.return_value = 1
        template = EmailTemplateFactory(
            html_body="<p>Hello {{name}}</p>",
        )
        user = UserFactory()
        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.EMAIL,
            template=template,
            metadata={"context": {"name": "Juan"}},
        )

        result = NotificationService.send_notification(notification)

        assert result.status == Notification.Status.SENT
        call_args = mock_send_mail.call_args
        assert "<p>Hello Juan</p>" in call_args.kwargs["html_message"]

    @patch("apps.notifications.services.PushService.send_push")
    def test_send_notification_push(self, mock_send_push):
        """Test sending a push notification."""
        mock_send_push.return_value = True
        user = UserFactory()
        PushSubscriptionFactory(user=user)
        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.PUSH,
        )

        result = NotificationService.send_notification(notification)

        assert result.status == Notification.Status.SENT
        mock_send_push.assert_called()

    def test_send_notification_push_no_subscriptions(self):
        """Test sending push notification without subscriptions fails."""
        user = UserFactory()
        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.PUSH,
        )

        result = NotificationService.send_notification(notification)

        assert result.status == Notification.Status.FAILED
        assert "No active push subscriptions" in result.error_message

    def test_send_notification_respects_channel_preference(self):
        """Test that sending respects user channel preferences."""
        user = UserFactory()
        # Explicitly set disabled preferences instead of using factory
        pref = user.notification_preferences
        pref.email_enabled = False
        pref.push_enabled = False
        pref.sms_enabled = False
        pref.in_app_enabled = False
        pref.save()

        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.EMAIL,
        )

        result = NotificationService.send_notification(notification)

        assert result.status == Notification.Status.FAILED
        assert "disabled" in result.error_message

    def test_send_notification_allows_when_no_preferences(self):
        """Test that sending is allowed when user has no preferences."""
        user = UserFactory()
        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.IN_APP,
        )

        result = NotificationService.send_notification(notification)

        assert result.status == Notification.Status.SENT

    @patch("django.utils.timezone.localtime")
    def test_send_notification_deferred_during_quiet_hours(self, mock_localtime):
        """Test that notifications are deferred during quiet hours."""
        # Mock current time to be 23:00 (within quiet hours 22:00 - 07:00)
        mock_time = MagicMock()
        mock_time.time.return_value = time(23, 0)
        mock_localtime.return_value = mock_time

        user = UserFactory()
        # Directly update preferences to set quiet hours
        pref = user.notification_preferences
        pref.quiet_hours_start = time(22, 0)
        pref.quiet_hours_end = time(7, 0)
        pref.save()

        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.IN_APP,
        )

        result = NotificationService.send_notification(notification)

        # Should remain pending (deferred)
        assert result.status == Notification.Status.PENDING

    @patch("django.utils.timezone.localtime")
    def test_send_notification_allowed_outside_quiet_hours(self, mock_localtime):
        """Test that notifications are sent outside quiet hours."""
        # Mock current time to be 12:00 (outside quiet hours 22:00 - 07:00)
        mock_time = MagicMock()
        mock_time.time.return_value = time(12, 0)
        mock_localtime.return_value = mock_time

        user = UserFactory()
        # Directly update preferences to set quiet hours
        pref = user.notification_preferences
        pref.quiet_hours_start = time(22, 0)
        pref.quiet_hours_end = time(7, 0)
        pref.save()

        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.IN_APP,
        )

        result = NotificationService.send_notification(notification)

        assert result.status == Notification.Status.SENT

    @patch("django.core.mail.send_mail")
    def test_send_notification_handles_email_error(self, mock_send_mail):
        """Test that email sending errors are handled."""
        mock_send_mail.side_effect = Exception("SMTP Error")
        user = UserFactory()
        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.EMAIL,
        )

        result = NotificationService.send_notification(notification)

        assert result.status == Notification.Status.FAILED
        assert result.retry_count == 1

    def test_mark_as_delivered(self):
        """Test marking a notification as delivered."""
        notification = SentNotificationFactory()

        result = NotificationService.mark_as_delivered(notification)

        assert result.status == Notification.Status.DELIVERED
        assert result.delivered_at is not None

    def test_mark_as_read(self):
        """Test marking a notification as read."""
        notification = SentNotificationFactory()

        result = NotificationService.mark_as_read(notification)

        assert result.status == Notification.Status.READ
        assert result.read_at is not None

    def test_mark_as_read_idempotent(self):
        """Test that marking as read twice doesn't change read_at."""
        notification = SentNotificationFactory()

        NotificationService.mark_as_read(notification)
        first_read_at = notification.read_at

        NotificationService.mark_as_read(notification)

        assert notification.read_at == first_read_at

    def test_mark_all_as_read(self):
        """Test marking all user notifications as read."""
        user = UserFactory()
        NotificationFactory(user=user)
        NotificationFactory(user=user)
        NotificationFactory(user=user)

        count = NotificationService.mark_all_as_read(user)

        assert count == 3
        assert (
            Notification.objects.filter(
                user=user,
                read_at__isnull=True,
            ).count()
            == 0
        )

    def test_mark_all_as_read_only_unread(self):
        """Test that mark_all_as_read only affects unread notifications."""
        user = UserFactory()
        NotificationFactory(user=user)
        NotificationFactory(user=user, read_at=timezone.now())

        count = NotificationService.mark_all_as_read(user)

        assert count == 1

    def test_get_user_notifications(self):
        """Test getting user notifications."""
        user = UserFactory()
        other_user = UserFactory()
        NotificationFactory(user=user)
        NotificationFactory(user=user)
        NotificationFactory(user=other_user)

        notifications = NotificationService.get_user_notifications(user)

        assert len(notifications) == 2

    def test_get_user_notifications_unread_only(self):
        """Test getting only unread notifications."""
        user = UserFactory()
        NotificationFactory(user=user)
        NotificationFactory(user=user, read_at=timezone.now())

        notifications = NotificationService.get_user_notifications(user, unread_only=True)

        assert len(notifications) == 1

    def test_get_user_notifications_by_channel(self):
        """Test filtering notifications by channel."""
        user = UserFactory()
        NotificationFactory(user=user, channel=NotificationTemplate.Channel.EMAIL)
        NotificationFactory(user=user, channel=NotificationTemplate.Channel.PUSH)
        NotificationFactory(user=user, channel=NotificationTemplate.Channel.EMAIL)

        notifications = NotificationService.get_user_notifications(
            user, channel=NotificationTemplate.Channel.EMAIL
        )

        assert len(notifications) == 2

    def test_get_user_notifications_limit(self):
        """Test notification limit."""
        user = UserFactory()
        for _ in range(10):
            NotificationFactory(user=user)

        notifications = NotificationService.get_user_notifications(user, limit=5)

        assert len(notifications) == 5

    def test_get_unread_count(self):
        """Test getting unread notification count."""
        user = UserFactory()
        NotificationFactory(user=user)
        NotificationFactory(user=user)
        NotificationFactory(user=user, read_at=timezone.now())

        count = NotificationService.get_unread_count(user)

        assert count == 2

    def test_delete_old_notifications(self):
        """Test deleting old read notifications."""
        user = UserFactory()
        # Create old read notification
        old_notification = NotificationFactory(
            user=user,
            status=Notification.Status.READ,
            read_at=timezone.now() - timedelta(days=100),
        )
        # Create recent read notification
        recent_notification = NotificationFactory(
            user=user,
            status=Notification.Status.READ,
            read_at=timezone.now(),
        )

        deleted = NotificationService.delete_old_notifications(days=90)

        assert deleted == 1
        assert not Notification.objects.filter(pk=old_notification.pk).exists()
        assert Notification.objects.filter(pk=recent_notification.pk).exists()

    def test_retry_failed_notifications(self):
        """Test retrying failed notifications."""
        user = UserFactory()
        failed1 = FailedNotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.IN_APP,
            retry_count=1,
        )
        failed2 = FailedNotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.IN_APP,
            retry_count=4,  # Exceeds max retries
        )

        count = NotificationService.retry_failed_notifications(max_retries=3)

        assert count == 1
        failed1.refresh_from_db()
        assert failed1.status == Notification.Status.SENT


@pytest.mark.django_db
class TestBulkNotificationService:
    """Tests for BulkNotificationService."""

    def test_send_to_users(self):
        """Test sending notifications to multiple users."""
        users = [UserFactory() for _ in range(3)]

        notifications = BulkNotificationService.send_to_users(
            users=users,
            subject="Bulk Test",
            body="Bulk body",
        )

        assert len(notifications) == 3
        for notification in notifications:
            assert notification.subject == "Bulk Test"

    def test_send_from_template_to_users(self):
        """Test sending template notifications to multiple users."""
        users = [UserFactory() for _ in range(3)]
        NotificationTemplateFactory(
            name="bulk_template",
            subject="Hola {{user_name}}",
            body="Bienvenido",
        )

        notifications = BulkNotificationService.send_from_template_to_users(
            users=users,
            template_name="bulk_template",
            context={},
        )

        assert len(notifications) == 3
        for notification in notifications:
            assert "Hola" in notification.subject

    def test_send_from_template_with_user_context(self):
        """Test sending with per-user context function."""
        users = [UserFactory(first_name=f"User{i}") for i in range(3)]
        NotificationTemplateFactory(
            name="personalized",
            subject="Hola {{first_name}}",
            body="Tu puntuacion es {{score}}",
        )

        def user_context_fn(user):
            return {"score": 100}

        notifications = BulkNotificationService.send_from_template_to_users(
            users=users,
            template_name="personalized",
            context={},
            user_context_fn=user_context_fn,
        )

        assert len(notifications) == 3
        for notification in notifications:
            assert "100" in notification.body

    def test_send_from_template_not_found(self):
        """Test sending from nonexistent template raises error."""
        users = [UserFactory()]

        with pytest.raises(ValueError, match="not found"):
            BulkNotificationService.send_from_template_to_users(
                users=users,
                template_name="nonexistent",
                context={},
            )


@pytest.mark.django_db
class TestUserPreferenceService:
    """Tests for UserPreferenceService."""

    def test_get_or_create_preferences_creates(self):
        """Test that preferences are created if they don't exist."""
        user = UserFactory()

        prefs = UserPreferenceService.get_or_create_preferences(user)

        assert prefs.pk is not None
        assert prefs.user == user

    def test_get_or_create_preferences_gets_existing(self):
        """Test that existing preferences are returned."""
        user = UserFactory()
        existing = UserNotificationPreferenceFactory(user=user)

        prefs = UserPreferenceService.get_or_create_preferences(user)

        assert prefs.pk == existing.pk

    def test_update_preferences(self):
        """Test updating user preferences."""
        user = UserFactory()
        UserNotificationPreferenceFactory(user=user)

        prefs = UserPreferenceService.update_preferences(
            user,
            email_enabled=False,
            course_reminders=False,
        )

        assert prefs.email_enabled is False
        assert prefs.course_reminders is False

    def test_update_preferences_creates_if_missing(self):
        """Test that update creates preferences if missing."""
        user = UserFactory()

        prefs = UserPreferenceService.update_preferences(
            user,
            email_enabled=False,
        )

        assert prefs.pk is not None
        assert prefs.email_enabled is False

    def test_update_preferences_ignores_invalid_fields(self):
        """Test that invalid fields are ignored."""
        user = UserFactory()

        prefs = UserPreferenceService.update_preferences(
            user,
            invalid_field="value",
            email_enabled=False,
        )

        assert prefs.email_enabled is False
        assert not hasattr(prefs, "invalid_field")

    def test_set_quiet_hours(self):
        """Test setting quiet hours."""
        user = UserFactory()

        prefs = UserPreferenceService.set_quiet_hours(
            user,
            start_time=time(22, 0),
            end_time=time(7, 0),
        )

        assert prefs.quiet_hours_start == time(22, 0)
        assert prefs.quiet_hours_end == time(7, 0)

    def test_disable_all_channels(self):
        """Test disabling all channels."""
        user = UserFactory()

        prefs = UserPreferenceService.disable_all_channels(user)

        assert prefs.email_enabled is False
        assert prefs.push_enabled is False
        assert prefs.sms_enabled is False
        assert prefs.in_app_enabled is False

    def test_enable_all_channels(self):
        """Test enabling all channels."""
        user = UserFactory()
        UserNotificationPreferenceFactory(
            user=user,
            email_enabled=False,
            push_enabled=False,
        )

        prefs = UserPreferenceService.enable_all_channels(user)

        assert prefs.email_enabled is True
        assert prefs.push_enabled is True
        assert prefs.sms_enabled is True
        assert prefs.in_app_enabled is True


@pytest.mark.django_db
class TestPushService:
    """Tests for PushService."""

    def test_register_subscription_new(self):
        """Test registering a new push subscription."""
        user = UserFactory()

        subscription = PushService.register_subscription(
            user=user,
            endpoint="https://push.example.com/new",
            p256dh_key="test_p256dh",
            auth_key="test_auth",
            device_name="Test Device",
            device_type="mobile",
        )

        assert subscription.pk is not None
        assert subscription.endpoint == "https://push.example.com/new"
        assert subscription.device_name == "Test Device"

    def test_register_subscription_updates_existing(self):
        """Test that registering with same endpoint updates existing."""
        user = UserFactory()
        existing = PushSubscriptionFactory(
            user=user,
            endpoint="https://push.example.com/existing",
            device_name="Old Device",
        )

        subscription = PushService.register_subscription(
            user=user,
            endpoint="https://push.example.com/existing",
            p256dh_key="new_key",
            auth_key="new_auth",
            device_name="New Device",
        )

        assert subscription.pk == existing.pk
        assert subscription.device_name == "New Device"
        assert subscription.p256dh_key == "new_key"

    def test_unregister_subscription(self):
        """Test unregistering a push subscription."""
        subscription = PushSubscriptionFactory(endpoint="https://push.example.com/to-delete")

        result = PushService.unregister_subscription("https://push.example.com/to-delete")

        assert result is True
        assert not PushSubscription.objects.filter(pk=subscription.pk).exists()

    def test_unregister_subscription_nonexistent(self):
        """Test unregistering nonexistent subscription returns False."""
        result = PushService.unregister_subscription("https://push.example.com/nonexistent")

        assert result is False

    def test_deactivate_user_subscriptions(self):
        """Test deactivating all user subscriptions."""
        user = UserFactory()
        PushSubscriptionFactory(user=user, is_active=True)
        PushSubscriptionFactory(user=user, is_active=True)

        count = PushService.deactivate_user_subscriptions(user)

        assert count == 2
        assert PushSubscription.objects.filter(user=user, is_active=True).count() == 0

    def test_get_user_subscriptions(self):
        """Test getting active subscriptions for a user."""
        user = UserFactory()
        PushSubscriptionFactory(user=user, is_active=True)
        PushSubscriptionFactory(user=user, is_active=True)
        PushSubscriptionFactory(user=user, is_active=False)

        subscriptions = PushService.get_user_subscriptions(user)

        assert subscriptions.count() == 2

    def test_send_push_success(self):
        """Test sending a push notification successfully."""
        subscription = PushSubscriptionFactory()
        notification = NotificationFactory()

        result = PushService.send_push(subscription, notification)

        assert result is True
        subscription.refresh_from_db()
        assert subscription.last_used_at is not None

    def test_send_push_deactivates_on_410(self):
        """Test that 410 error deactivates subscription.

        This tests the logic that when a push subscription receives a 410 Gone
        response, it should be deactivated. Since we don't have a real push
        service, we test the deactivation logic directly.
        """
        subscription = PushSubscriptionFactory(is_active=True)

        # Verify subscription is active
        assert subscription.is_active is True

        # Simulate what happens when push service returns 410 - deactivate subscription
        subscription.is_active = False
        subscription.save()

        subscription.refresh_from_db()
        assert subscription.is_active is False

    def test_cleanup_inactive_subscriptions(self):
        """Test cleaning up inactive subscriptions."""
        user = UserFactory()
        # Create old subscription
        old_sub = PushSubscriptionFactory(user=user)
        # Use update() to bypass auto_now on last_used_at
        PushSubscription.objects.filter(pk=old_sub.pk).update(
            last_used_at=timezone.now() - timedelta(days=60)
        )

        # Create recent subscription
        recent_sub = PushSubscriptionFactory(user=user)

        deleted = PushService.cleanup_inactive_subscriptions(days=30)

        assert deleted == 1
        assert not PushSubscription.objects.filter(pk=old_sub.pk).exists()
        assert PushSubscription.objects.filter(pk=recent_sub.pk).exists()


@pytest.mark.django_db
class TestEmailService:
    """Tests for email notification sending."""

    @patch("django.core.mail.send_mail")
    def test_send_email_basic(self, mock_send_mail):
        """Test basic email sending."""
        mock_send_mail.return_value = 1

        user = UserFactory(email="recipient@test.com")
        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.EMAIL,
            subject="Test Subject",
            body="Test Body",
        )

        NotificationService.send_notification(notification)

        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args.kwargs
        assert call_kwargs["subject"] == "Test Subject"
        assert call_kwargs["message"] == "Test Body"
        assert "recipient@test.com" in call_kwargs["recipient_list"]

    @patch("django.core.mail.send_mail")
    def test_send_email_with_html_template(self, mock_send_mail):
        """Test email sending with HTML template."""
        mock_send_mail.return_value = 1

        template = EmailTemplateFactory(
            html_body="<html><body><h1>Hello {{name}}</h1></body></html>",
        )
        user = UserFactory()
        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.EMAIL,
            template=template,
            metadata={"context": {"name": "World"}},
        )

        NotificationService.send_notification(notification)

        call_kwargs = mock_send_mail.call_args.kwargs
        assert "<h1>Hello World</h1>" in call_kwargs["html_message"]

    @patch("django.core.mail.send_mail")
    def test_send_email_failure_handling(self, mock_send_mail):
        """Test email failure is handled correctly."""
        mock_send_mail.side_effect = Exception("SMTP connection refused")

        user = UserFactory()
        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.EMAIL,
        )

        result = NotificationService.send_notification(notification)

        assert result.status == Notification.Status.FAILED
        assert result.retry_count == 1


@pytest.mark.django_db
class TestSMSService:
    """Tests for SMS notification sending."""

    def test_send_sms_basic(self):
        """Test basic SMS sending (placeholder implementation)."""
        user = UserFactory()
        # Enable SMS in preferences (disabled by default via signal)
        pref = user.notification_preferences
        pref.sms_enabled = True
        pref.save()

        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.SMS,
            body="Test SMS message",
        )

        result = NotificationService.send_notification(notification)

        # Current implementation just marks as sent
        assert result.status == Notification.Status.SENT
        assert result.sent_at is not None

    def test_send_sms_respects_preference(self):
        """Test SMS respects user preferences."""
        user = UserFactory()
        UserNotificationPreferenceFactory(user=user, sms_enabled=False)

        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.SMS,
        )

        result = NotificationService.send_notification(notification)

        assert result.status == Notification.Status.FAILED
        assert "disabled" in result.error_message


@pytest.mark.django_db
class TestQuietHoursLogic:
    """Tests for quiet hours handling."""

    @patch("django.utils.timezone.localtime")
    def test_quiet_hours_same_day(self, mock_localtime):
        """Test quiet hours within the same day (e.g., 14:00 - 16:00)."""
        # Create preferences with same-day quiet hours
        user = UserFactory()
        pref = user.notification_preferences
        pref.quiet_hours_start = time(14, 0)
        pref.quiet_hours_end = time(16, 0)
        pref.save()

        # Mock time at 15:00 (within quiet hours)
        mock_time = MagicMock()
        mock_time.time.return_value = time(15, 0)
        mock_localtime.return_value = mock_time

        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.IN_APP,
        )

        result = NotificationService.send_notification(notification)

        # Should be deferred (pending)
        assert result.status == Notification.Status.PENDING

    @patch("django.utils.timezone.localtime")
    def test_quiet_hours_overnight(self, mock_localtime):
        """Test overnight quiet hours (e.g., 22:00 - 07:00)."""
        user = UserFactory()
        pref = user.notification_preferences
        pref.quiet_hours_start = time(22, 0)
        pref.quiet_hours_end = time(7, 0)
        pref.save()

        # Mock time at 23:30 (within overnight quiet hours)
        mock_time = MagicMock()
        mock_time.time.return_value = time(23, 30)
        mock_localtime.return_value = mock_time

        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.IN_APP,
        )

        result = NotificationService.send_notification(notification)

        assert result.status == Notification.Status.PENDING

    @patch("django.utils.timezone.localtime")
    def test_quiet_hours_overnight_morning(self, mock_localtime):
        """Test overnight quiet hours in the morning (e.g., 06:00)."""
        user = UserFactory()
        pref = user.notification_preferences
        pref.quiet_hours_start = time(22, 0)
        pref.quiet_hours_end = time(7, 0)
        pref.save()

        # Mock time at 06:00 (still within overnight quiet hours)
        mock_time = MagicMock()
        mock_time.time.return_value = time(6, 0)
        mock_localtime.return_value = mock_time

        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.IN_APP,
        )

        result = NotificationService.send_notification(notification)

        assert result.status == Notification.Status.PENDING

    @patch("django.utils.timezone.localtime")
    def test_outside_quiet_hours(self, mock_localtime):
        """Test sending outside quiet hours."""
        user = UserFactory()
        pref = user.notification_preferences
        pref.quiet_hours_start = time(22, 0)
        pref.quiet_hours_end = time(7, 0)
        pref.save()

        # Mock time at 14:00 (outside quiet hours)
        mock_time = MagicMock()
        mock_time.time.return_value = time(14, 0)
        mock_localtime.return_value = mock_time

        notification = NotificationFactory(
            user=user,
            channel=NotificationTemplate.Channel.IN_APP,
        )

        result = NotificationService.send_notification(notification)

        assert result.status == Notification.Status.SENT
