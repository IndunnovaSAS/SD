"""
Service for push notification operations.
"""

import logging

from django.utils import timezone

from apps.notifications.models import Notification, PushSubscription

logger = logging.getLogger(__name__)


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

        except ConnectionError as e:
            logger.error(f"Error de conexion enviando push a suscripcion {subscription.id}: {e}")
            # Errores de conexion son temporales, no desactivar
            return False
        except ValueError as e:
            logger.warning(f"Error de configuracion para push {subscription.id}: {e}")
            return False
        except Exception as e:
            error_str = str(e)
            # Verificar si el endpoint ya no es valido (410 Gone o 404 Not Found)
            if "410" in error_str or "404" in error_str:
                logger.warning(f"Suscripcion {subscription.id} ya no es valida, desactivando: {e}")
                subscription.is_active = False
                subscription.save()
            else:
                logger.exception(f"Error inesperado enviando push a suscripcion {subscription.id}: {e}")
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
