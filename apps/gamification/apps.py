"""
Gamification app configuration.
"""

from django.apps import AppConfig


class GamificationConfig(AppConfig):
    """Configuration for gamification app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.gamification"
    verbose_name = "Gamification"

    def ready(self):
        """Import signals when app is ready."""
        try:
            import apps.gamification.signals  # noqa: F401
        except ImportError:
            pass
