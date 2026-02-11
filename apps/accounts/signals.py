"""
Signals for accounts app.
"""

import logging
from datetime import date

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import JobHistory, User

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=User)
def track_job_profile_changes(sender, instance, **kwargs):
    """
    Track changes to job_profile and job_position for history (USR-08).

    When a user's job profile changes:
    - Record the change in JobHistory
    - Note: Learning path re-assignment is handled separately
    """
    if not instance.pk:
        # New user, no previous data
        return

    try:
        old_user = User.objects.get(pk=instance.pk)
    except User.DoesNotExist:
        return

    # Check if job profile, position, or employment type changed
    profile_changed = old_user.job_profile != instance.job_profile
    position_changed = old_user.job_position != instance.job_position
    employment_changed = old_user.employment_type != instance.employment_type

    if profile_changed or position_changed or employment_changed:
        JobHistory.objects.create(
            user=instance,
            previous_position=old_user.job_position,
            new_position=instance.job_position,
            previous_profile=old_user.job_profile,
            new_profile=instance.job_profile,
            previous_employment_type=old_user.employment_type,
            new_employment_type=instance.employment_type,
            change_date=date.today(),
            reason="Cambio de perfil ocupacional registrado automáticamente",
        )
        logger.info(
            f"Job profile change recorded for {instance.document_number}: "
            f"{old_user.job_profile} → {instance.job_profile}"
        )


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
            if hasattr(instance, "job_profile") and instance.job_profile:
                # Role assignment logic can be extended here
                logger.debug(f"User {instance.email} has job_profile: {instance.job_profile}")
        except Exception as e:
            logger.warning(f"Error checking job_profile for {instance.email}: {e}")

        # Audit log for new user creation
        logger.info(f"New user created: {instance.email} (ID: {instance.id})")
    else:
        # Log significant updates
        update_fields = kwargs.get("update_fields")

        if update_fields:
            significant_fields = {"email", "is_active", "is_staff", "is_superuser"}
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
