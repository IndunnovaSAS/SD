"""
Business logic services for notifications.
"""

import logging
import re
from typing import Optional

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.notifications.models import (
    Notification,
    NotificationTemplate,
    PushSubscription,
    UserNotificationPreference,
)

logger = logging.getLogger(__name__)


class NotificationTemplateService:
    """Service for notification template operations."""

    @staticmethod
    def get_template(name: str, channel: str = None) -> NotificationTemplate:
        """
        Get a notification template by name.
        """
        queryset = NotificationTemplate.objects.filter(
            name=name,
            is_active=True,
        )

        if channel:
            queryset = queryset.filter(channel=channel)

        return queryset.first()

    @staticmethod
    def render_template(
        template: NotificationTemplate,
        context: dict,
    ) -> dict:
        """
        Render a notification template with given context.
        Returns rendered subject and body.
        """
        subject = NotificationTemplateService._render_string(
            template.subject, context
        )
        body = NotificationTemplateService._render_string(
            template.body, context
        )
        html_body = ""
        if template.html_body:
            html_body = NotificationTemplateService._render_string(
                template.html_body, context
            )

        return {
            "subject": subject,
            "body": body,
            "html_body": html_body,
        }

    @staticmethod
    def _render_string(template_str: str, context: dict) -> str:
        """
        Render a template string with {{variable}} placeholders.
        """
        result = template_str
        for key, value in context.items():
            placeholder = "{{" + key + "}}"
            result = result.replace(placeholder, str(value))
        return result

    @staticmethod
    def get_templates_by_channel(channel: str):
        """
        Get all active templates for a specific channel.
        """
        return NotificationTemplate.objects.filter(
            channel=channel,
            is_active=True,
        ).order_by("name")


class NotificationService:
    """Service for notification operations."""

    @staticmethod
    @transaction.atomic
    def create_notification(
        user,
        subject: str,
        body: str,
        channel: str = NotificationTemplate.Channel.IN_APP,
        template: NotificationTemplate = None,
        priority: str = Notification.Priority.NORMAL,
        action_url: str = "",
        action_text: str = "",
        metadata: dict = None,
    ) -> Notification:
        """
        Create a new notification for a user.
        """
        notification = Notification.objects.create(
            user=user,
            template=template,
            channel=channel,
            subject=subject,
            body=body,
            status=Notification.Status.PENDING,
            priority=priority,
            action_url=action_url,
            action_text=action_text,
            metadata=metadata or {},
        )

        logger.info(f"Notification created: {notification.id} for user {user.id}")
        return notification

    @staticmethod
    @transaction.atomic
    def send_from_template(
        user,
        template_name: str,
        context: dict,
        channel: str = None,
        priority: str = Notification.Priority.NORMAL,
        action_url: str = "",
        action_text: str = "",
    ) -> Notification:
        """
        Create and send a notification from a template.
        """
        template = NotificationTemplateService.get_template(
            template_name, channel
        )

        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        rendered = NotificationTemplateService.render_template(template, context)

        notification = NotificationService.create_notification(
            user=user,
            subject=rendered["subject"],
            body=rendered["body"],
            channel=channel or template.channel,
            template=template,
            priority=priority,
            action_url=action_url,
            action_text=action_text,
            metadata={"context": context},
        )

        return notification

    @staticmethod
    def send_notification(notification: Notification) -> Notification:
        """
        Send a notification through its channel.
        """
        # Check user preferences
        if not NotificationService._can_send(notification):
            notification.status = Notification.Status.FAILED
            notification.error_message = "User has disabled this notification type"
            notification.save()
            return notification

        # Check quiet hours
        if NotificationService._in_quiet_hours(notification.user):
            # Defer sending - keep as pending
            return notification

        try:
            if notification.channel == NotificationTemplate.Channel.EMAIL:
                NotificationService._send_email(notification)
            elif notification.channel == NotificationTemplate.Channel.PUSH:
                NotificationService._send_push(notification)
            elif notification.channel == NotificationTemplate.Channel.SMS:
                NotificationService._send_sms(notification)
            elif notification.channel == NotificationTemplate.Channel.IN_APP:
                # In-app notifications are just marked as sent
                notification.status = Notification.Status.SENT
                notification.sent_at = timezone.now()
                notification.save()

            logger.info(f"Notification sent: {notification.id}")

        except Exception as e:
            notification.status = Notification.Status.FAILED
            notification.error_message = str(e)
            notification.retry_count += 1
            notification.save()
            logger.error(f"Failed to send notification {notification.id}: {e}")

        return notification

    @staticmethod
    def _can_send(notification: Notification) -> bool:
        """
        Check if notification can be sent based on user preferences.
        """
        try:
            prefs = notification.user.notification_preferences
        except UserNotificationPreference.DoesNotExist:
            return True  # No preferences = all enabled

        # Check channel preference
        if notification.channel == NotificationTemplate.Channel.EMAIL:
            if not prefs.email_enabled:
                return False
        elif notification.channel == NotificationTemplate.Channel.PUSH:
            if not prefs.push_enabled:
                return False
        elif notification.channel == NotificationTemplate.Channel.SMS:
            if not prefs.sms_enabled:
                return False
        elif notification.channel == NotificationTemplate.Channel.IN_APP:
            if not prefs.in_app_enabled:
                return False

        return True

    @staticmethod
    def _in_quiet_hours(user) -> bool:
        """
        Check if user is in quiet hours.
        """
        try:
            prefs = user.notification_preferences
        except UserNotificationPreference.DoesNotExist:
            return False

        if not prefs.quiet_hours_start or not prefs.quiet_hours_end:
            return False

        now = timezone.localtime().time()
        start = prefs.quiet_hours_start
        end = prefs.quiet_hours_end

        # Handle overnight quiet hours
        if start <= end:
            return start <= now <= end
        else:
            return now >= start or now <= end

    @staticmethod
    def _send_email(notification: Notification) -> None:
        """
        Send notification via email.
        """
        from django.core.mail import send_mail
        from django.conf import settings

        html_message = None
        if notification.template and notification.template.html_body:
            context = notification.metadata.get("context", {})
            html_message = NotificationTemplateService._render_string(
                notification.template.html_body, context
            )

        send_mail(
            subject=notification.subject,
            message=notification.body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.user.email],
            html_message=html_message,
            fail_silently=False,
        )

        notification.status = Notification.Status.SENT
        notification.sent_at = timezone.now()
        notification.save()

    @staticmethod
    def _send_push(notification: Notification) -> None:
        """
        Send push notification.
        """
        subscriptions = PushSubscription.objects.filter(
            user=notification.user,
            is_active=True,
        )

        if not subscriptions.exists():
            raise ValueError("No active push subscriptions")

        # Send to all active subscriptions
        for subscription in subscriptions:
            PushService.send_push(subscription, notification)

        notification.status = Notification.Status.SENT
        notification.sent_at = timezone.now()
        notification.save()

    @staticmethod
    def _send_sms(notification: Notification) -> None:
        """
        Send SMS notification.
        Placeholder - would integrate with SMS gateway.
        """
        # SMS sending logic would go here
        notification.status = Notification.Status.SENT
        notification.sent_at = timezone.now()
        notification.save()

    @staticmethod
    def mark_as_delivered(notification: Notification) -> Notification:
        """
        Mark notification as delivered.
        """
        notification.status = Notification.Status.DELIVERED
        notification.delivered_at = timezone.now()
        notification.save()

        return notification

    @staticmethod
    def mark_as_read(notification: Notification) -> Notification:
        """
        Mark notification as read.
        """
        if not notification.read_at:
            notification.status = Notification.Status.READ
            notification.read_at = timezone.now()
            notification.save()

        return notification

    @staticmethod
    def mark_all_as_read(user) -> int:
        """
        Mark all unread notifications for a user as read.
        """
        now = timezone.now()
        count = Notification.objects.filter(
            user=user,
            read_at__isnull=True,
        ).update(
            status=Notification.Status.READ,
            read_at=now,
        )

        return count

    @staticmethod
    def get_user_notifications(
        user,
        unread_only: bool = False,
        channel: str = None,
        limit: int = 50,
    ):
        """
        Get notifications for a user.
        """
        queryset = Notification.objects.filter(user=user)

        if unread_only:
            queryset = queryset.filter(read_at__isnull=True)

        if channel:
            queryset = queryset.filter(channel=channel)

        return queryset.order_by("-created_at")[:limit]

    @staticmethod
    def get_unread_count(user) -> int:
        """
        Get count of unread notifications for a user.
        """
        return Notification.objects.filter(
            user=user,
            read_at__isnull=True,
        ).count()

    @staticmethod
    def delete_old_notifications(days: int = 90) -> int:
        """
        Delete old read notifications.
        """
        cutoff = timezone.now() - timezone.timedelta(days=days)
        deleted, _ = Notification.objects.filter(
            status=Notification.Status.READ,
            read_at__lt=cutoff,
        ).delete()

        if deleted > 0:
            logger.info(f"Deleted {deleted} old notifications")

        return deleted

    @staticmethod
    def retry_failed_notifications(max_retries: int = 3) -> int:
        """
        Retry failed notifications that haven't exceeded max retries.
        """
        failed = Notification.objects.filter(
            status=Notification.Status.FAILED,
            retry_count__lt=max_retries,
        )

        count = 0
        for notification in failed:
            notification.status = Notification.Status.PENDING
            notification.save()
            NotificationService.send_notification(notification)
            count += 1

        return count


class BulkNotificationService:
    """Service for sending bulk notifications."""

    @staticmethod
    @transaction.atomic
    def send_to_users(
        users,
        subject: str,
        body: str,
        channel: str = NotificationTemplate.Channel.IN_APP,
        priority: str = Notification.Priority.NORMAL,
        action_url: str = "",
    ) -> list:
        """
        Send notification to multiple users.
        """
        notifications = []

        for user in users:
            notification = NotificationService.create_notification(
                user=user,
                subject=subject,
                body=body,
                channel=channel,
                priority=priority,
                action_url=action_url,
            )
            notifications.append(notification)

        logger.info(f"Bulk notification created for {len(notifications)} users")
        return notifications

    @staticmethod
    @transaction.atomic
    def send_from_template_to_users(
        users,
        template_name: str,
        context: dict,
        user_context_fn=None,
        channel: str = None,
        priority: str = Notification.Priority.NORMAL,
    ) -> list:
        """
        Send notification from template to multiple users.
        user_context_fn can provide per-user context.
        """
        template = NotificationTemplateService.get_template(
            template_name, channel
        )

        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        notifications = []

        for user in users:
            # Get user-specific context if function provided
            user_context = context.copy()
            if user_context_fn:
                user_context.update(user_context_fn(user))

            # Always include user name
            user_context.setdefault("user_name", user.get_full_name())
            user_context.setdefault("first_name", user.first_name)

            rendered = NotificationTemplateService.render_template(
                template, user_context
            )

            notification = NotificationService.create_notification(
                user=user,
                subject=rendered["subject"],
                body=rendered["body"],
                channel=channel or template.channel,
                template=template,
                priority=priority,
                metadata={"context": user_context},
            )
            notifications.append(notification)

        logger.info(f"Bulk template notification created for {len(notifications)} users")
        return notifications

    @staticmethod
    def send_course_reminder(course, users) -> list:
        """
        Send course reminder notifications.
        """
        context = {
            "course_title": course.title,
            "course_code": course.code,
        }

        def user_context(user):
            return {"user_name": user.get_full_name()}

        return BulkNotificationService.send_from_template_to_users(
            users=users,
            template_name="course_reminder",
            context=context,
            user_context_fn=user_context,
            priority=Notification.Priority.NORMAL,
        )

    @staticmethod
    def send_deadline_reminder(assignment, days_left: int) -> Notification:
        """
        Send deadline reminder for a learning path assignment.
        """
        context = {
            "path_name": assignment.learning_path.name,
            "due_date": assignment.due_date.strftime("%d/%m/%Y"),
            "days_left": days_left,
            "user_name": assignment.user.get_full_name(),
        }

        priority = Notification.Priority.NORMAL
        if days_left <= 3:
            priority = Notification.Priority.HIGH
        if days_left <= 1:
            priority = Notification.Priority.URGENT

        return NotificationService.send_from_template(
            user=assignment.user,
            template_name="deadline_reminder",
            context=context,
            priority=priority,
        )


class UserPreferenceService:
    """Service for user notification preferences."""

    @staticmethod
    def get_or_create_preferences(user) -> UserNotificationPreference:
        """
        Get or create notification preferences for a user.
        """
        prefs, _ = UserNotificationPreference.objects.get_or_create(
            user=user,
        )
        return prefs

    @staticmethod
    def update_preferences(
        user,
        **kwargs,
    ) -> UserNotificationPreference:
        """
        Update user notification preferences.
        """
        prefs = UserPreferenceService.get_or_create_preferences(user)

        for key, value in kwargs.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)

        prefs.save()
        return prefs

    @staticmethod
    def set_quiet_hours(
        user,
        start_time,
        end_time,
    ) -> UserNotificationPreference:
        """
        Set quiet hours for a user.
        """
        prefs = UserPreferenceService.get_or_create_preferences(user)
        prefs.quiet_hours_start = start_time
        prefs.quiet_hours_end = end_time
        prefs.save()

        return prefs

    @staticmethod
    def disable_all_channels(user) -> UserNotificationPreference:
        """
        Disable all notification channels for a user.
        """
        return UserPreferenceService.update_preferences(
            user,
            email_enabled=False,
            push_enabled=False,
            sms_enabled=False,
            in_app_enabled=False,
        )

    @staticmethod
    def enable_all_channels(user) -> UserNotificationPreference:
        """
        Enable all notification channels for a user.
        """
        return UserPreferenceService.update_preferences(
            user,
            email_enabled=True,
            push_enabled=True,
            sms_enabled=True,
            in_app_enabled=True,
        )


class PushService:
    """Service for push notification operations."""

    @staticmethod
    def register_subscription(
        user,
        endpoint: str,
        p256dh_key: str,
        auth_key: str,
        device_name: str = "",
        device_type: str = "",
    ) -> PushSubscription:
        """
        Register a new push subscription for a user.
        """
        # Check if subscription already exists
        existing = PushSubscription.objects.filter(
            user=user,
            endpoint=endpoint,
        ).first()

        if existing:
            existing.p256dh_key = p256dh_key
            existing.auth_key = auth_key
            existing.device_name = device_name
            existing.device_type = device_type
            existing.is_active = True
            existing.save()
            return existing

        subscription = PushSubscription.objects.create(
            user=user,
            endpoint=endpoint,
            p256dh_key=p256dh_key,
            auth_key=auth_key,
            device_name=device_name,
            device_type=device_type,
        )

        logger.info(f"Push subscription registered for user {user.id}")
        return subscription

    @staticmethod
    def unregister_subscription(endpoint: str) -> bool:
        """
        Unregister a push subscription by endpoint.
        """
        deleted, _ = PushSubscription.objects.filter(
            endpoint=endpoint
        ).delete()

        return deleted > 0

    @staticmethod
    def deactivate_user_subscriptions(user) -> int:
        """
        Deactivate all push subscriptions for a user.
        """
        count = PushSubscription.objects.filter(
            user=user,
            is_active=True,
        ).update(is_active=False)

        return count

    @staticmethod
    def get_user_subscriptions(user):
        """
        Get all active subscriptions for a user.
        """
        return PushSubscription.objects.filter(
            user=user,
            is_active=True,
        ).order_by("-last_used_at")

    @staticmethod
    def send_push(
        subscription: PushSubscription,
        notification: Notification,
    ) -> bool:
        """
        Send a push notification to a subscription.
        Placeholder - would use pywebpush or similar library.
        """
        try:
            # In production, this would use pywebpush:
            # from pywebpush import webpush
            # webpush(
            #     subscription_info={
            #         "endpoint": subscription.endpoint,
            #         "keys": {
            #             "p256dh": subscription.p256dh_key,
            #             "auth": subscription.auth_key,
            #         }
            #     },
            #     data=json.dumps({
            #         "title": notification.subject,
            #         "body": notification.body,
            #         "url": notification.action_url,
            #     }),
            #     vapid_private_key=settings.VAPID_PRIVATE_KEY,
            #     vapid_claims={"sub": f"mailto:{settings.VAPID_EMAIL}"},
            # )

            subscription.last_used_at = timezone.now()
            subscription.save()

            logger.info(f"Push sent to subscription {subscription.id}")
            return True

        except Exception as e:
            logger.error(f"Push failed for subscription {subscription.id}: {e}")
            # Mark subscription as inactive if endpoint is invalid
            if "410" in str(e) or "404" in str(e):
                subscription.is_active = False
                subscription.save()
            return False

    @staticmethod
    def cleanup_inactive_subscriptions(days: int = 30) -> int:
        """
        Remove subscriptions not used in specified days.
        """
        cutoff = timezone.now() - timezone.timedelta(days=days)
        deleted, _ = PushSubscription.objects.filter(
            last_used_at__lt=cutoff,
        ).delete()

        if deleted > 0:
            logger.info(f"Deleted {deleted} inactive push subscriptions")

        return deleted
