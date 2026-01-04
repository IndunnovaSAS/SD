"""
Signals for accounts app.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for user creation and updates.
    """
    if created:
        # Auto-assign default role based on job_profile
        pass  # Will be implemented with role assignment logic
