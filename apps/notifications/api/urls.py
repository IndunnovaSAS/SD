"""
API URL configuration for notifications.
"""

from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import (
    NotificationTemplateViewSet,
    NotificationViewSet,
    PushSubscriptionViewSet,
    UserNotificationPreferenceViewSet,
)

app_name = "notifications_api"

router = DefaultRouter()
router.register(r"templates", NotificationTemplateViewSet, basename="template")
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"preferences", UserNotificationPreferenceViewSet, basename="preference")
router.register(r"push-subscriptions", PushSubscriptionViewSet, basename="push-subscription")

urlpatterns = [
    path("", include(router.urls)),
]
