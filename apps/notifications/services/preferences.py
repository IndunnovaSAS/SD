"""
Service for user notification preferences.
"""

from apps.notifications.models import UserNotificationPreference


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


# Alias for backward compatibility
NotificationPreferenceService = UserPreferenceService
