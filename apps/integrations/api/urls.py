"""
API URL configuration for integrations.
"""

from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import (
    DataMappingViewSet,
    ExternalSystemViewSet,
    IntegrationLogViewSet,
    WebhookDeliveryViewSet,
    WebhookViewSet,
)

app_name = "integrations_api"

router = DefaultRouter()
router.register(r"systems", ExternalSystemViewSet, basename="system")
router.register(r"logs", IntegrationLogViewSet, basename="log")
router.register(r"mappings", DataMappingViewSet, basename="mapping")
router.register(r"webhooks", WebhookViewSet, basename="webhook")
router.register(r"deliveries", WebhookDeliveryViewSet, basename="delivery")

urlpatterns = [
    path("", include(router.urls)),
]
