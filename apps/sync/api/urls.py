"""
API URL configuration for offline sync.
"""

from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import (
    OfflinePackageViewSet,
    PackageDownloadViewSet,
    SyncConflictViewSet,
    SyncLogViewSet,
)

app_name = "sync_api"

router = DefaultRouter()
router.register(r"logs", SyncLogViewSet, basename="log")
router.register(r"conflicts", SyncConflictViewSet, basename="conflict")
router.register(r"packages", OfflinePackageViewSet, basename="package")
router.register(r"downloads", PackageDownloadViewSet, basename="download")

urlpatterns = [
    path("", include(router.urls)),
]
