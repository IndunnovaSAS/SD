"""
Main notification service for notification operations.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.notifications.models import (
    Notification,
    NotificationTemplate,
    PushSubscription,
    UserNotificationPreference,
)
from apps.notifications.services.templates import NotificationTemplateService

logger = logging.getLogger(__name__)


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
        # Import here to avoid circular imports
        from apps.notifications.services.push import PushService

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
                NotificationService._send_push(notification, PushService)
            elif notification.channel == NotificationTemplate.Channel.SMS:
                NotificationService._send_sms(notification)
            elif notification.channel == NotificationTemplate.Channel.IN_APP:
                # In-app notifications are just marked as sent
                notification.status = Notification.Status.SENT
                notification.sent_at = timezone.now()
                notification.save()

            logger.info(f"Notification sent: {notification.id}")

        except ValueError as e:
            # Errores de validacion o configuracion (ej: sin suscripciones push)
            notification.status = Notification.Status.FAILED
            notification.error_message = str(e)
            notification.retry_count += 1
            notification.save()
            logger.warning(f"Error de validacion enviando notificacion {notification.id}: {e}")
        except ConnectionError as e:
            # Errores de conexion (temporales, podrian reintentarse)
            notification.status = Notification.Status.FAILED
            notification.error_message = f"Error de conexion: {e}"
            notification.retry_count += 1
            notification.save()
            logger.error(f"Error de conexion enviando notificacion {notification.id}: {e}")
        except Exception as e:
            notification.status = Notification.Status.FAILED
            notification.error_message = "Error inesperado al enviar notificacion."
            notification.retry_count += 1
            notification.save()
            logger.exception(f"Error inesperado enviando notificacion {notification.id}: {e}")

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
    def _send_push(notification: Notification, PushService) -> None:
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
