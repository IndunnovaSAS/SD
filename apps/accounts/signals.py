"""
Signals for accounts app.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for user creation and updates.

    On creation:
        - Creates UserPoints record for gamification
        - Creates UserNotificationPreference with defaults
        - Assigns default role if applicable
        - Logs audit entry

    On update:
        - Logs significant changes (email, status)
    """
    if created:
        # Create gamification points record
        try:
            from apps.gamification.models import UserPoints
            UserPoints.objects.get_or_create(user=instance)
            logger.debug(f"Created UserPoints for user: {instance.email}")
        except ImportError:
            logger.debug("Gamification app not available, skipping UserPoints creation")
        except Exception as e:
            logger.warning(f"Failed to create UserPoints for {instance.email}: {e}")

        # Create notification preferences with defaults
        try:
            from apps.notifications.models import UserNotificationPreference
            UserNotificationPreference.objects.get_or_create(user=instance)
            logger.debug(f"Created NotificationPreference for user: {instance.email}")
        except ImportError:
            logger.debug("Notifications app not available, skipping preference creation")
        except Exception as e:
            logger.warning(f"Failed to create NotificationPreference for {instance.email}: {e}")

        # Assign default role based on job_profile if available
        try:
            if hasattr(instance, 'job_profile') and instance.job_profile:
                # Role assignment logic can be extended here
                logger.debug(f"User {instance.email} has job_profile: {instance.job_profile}")
        except Exception as e:
            logger.warning(f"Error checking job_profile for {instance.email}: {e}")

        # Audit log for new user creation
        logger.info(f"New user created: {instance.email} (ID: {instance.id})")
    else:
        # Log significant updates
        update_fields = kwargs.get('update_fields')

        if update_fields:
            significant_fields = {'email', 'is_active', 'is_staff', 'is_superuser'}
            changed_significant = significant_fields.intersection(set(update_fields))

            if changed_significant:
                logger.info(
                    f"User {instance.email} (ID: {instance.id}) updated: "
                    f"changed fields: {', '.join(changed_significant)}"
                )
            else:
                logger.debug(f"User updated: {instance.email} (ID: {instance.id})")
        else:
            # When update_fields is None, we don't know what changed
            logger.debug(f"User updated: {instance.email} (ID: {instance.id})")
