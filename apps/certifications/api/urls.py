"""
API URL configuration for certifications.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CertificateTemplateViewSet, CertificateViewSet

app_name = "certifications_api"

router = DefaultRouter()
router.register(r"templates", CertificateTemplateViewSet, basename="template")
router.register(r"certificates", CertificateViewSet, basename="certificate")

urlpatterns = [
    path("", include(router.urls)),
]
