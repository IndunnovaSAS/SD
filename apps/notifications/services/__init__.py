"""
Notification services module.

This module provides services for notification operations including:
- NotificationService: Main service for creating and sending notifications
- NotificationTemplateService: Service for managing notification templates
- BulkNotificationService: Service for sending bulk notifications
- UserPreferenceService: Service for managing user notification preferences
- PushService: Service for push notification operations
"""

from apps.notifications.services.bulk import BulkNotificationService
from apps.notifications.services.notification import NotificationService
from apps.notifications.services.preferences import (
    NotificationPreferenceService,
    UserPreferenceService,
)
from apps.notifications.services.push import PushService
from apps.notifications.services.templates import NotificationTemplateService

__all__ = [
    "NotificationService",
    "NotificationTemplateService",
    "BulkNotificationService",
    "UserPreferenceService",
    "NotificationPreferenceService",  # Alias for backward compatibility
    "PushService",
]
