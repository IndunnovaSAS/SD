"""
Signals for occupational_profiles app.

Handles automatic learning path assignment when a user is assigned a profile.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserOccupationalProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=UserOccupationalProfile)
def assign_learning_paths_on_profile_assignment(sender, instance, created, **kwargs):
    """
    Auto-assign learning paths when a user is assigned an occupational profile.

    This implements PER-02: Each profile links to learning paths that are
    automatically assigned when the profile is assigned to a user.
    """
    if not instance.is_active:
        return

    from apps.learning_paths.models import PathAssignment

    user = instance.user
    profile = instance.profile

    # Get all learning paths linked to this profile
    learning_paths = profile.learning_paths.filter(status="active")

    for learning_path in learning_paths:
        # Check if assignment already exists
        assignment, created_assignment = PathAssignment.objects.get_or_create(
            user=user,
            learning_path=learning_path,
            defaults={
                "assigned_by": instance.assigned_by,
                "status": "assigned",
            },
        )

        if created_assignment:
            logger.info(
                f"Auto-assigned learning path '{learning_path.name}' to user "
                f"{user.document_number} based on profile '{profile.name}'"
            )
        else:
            # If assignment exists but was overdue/completed, don't change it
            logger.debug(
                f"Learning path '{learning_path.name}' already assigned to "
                f"user {user.document_number}"
            )
