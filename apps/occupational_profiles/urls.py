"""
URL configuration for occupational_profiles app.
"""

from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .api.views import OccupationalProfileViewSet, UserOccupationalProfileViewSet

app_name = "occupational_profiles"

router = DefaultRouter()
router.register(r"profiles", OccupationalProfileViewSet, basename="profile")
router.register(r"assignments", UserOccupationalProfileViewSet, basename="assignment")

urlpatterns = [
    path("api/", include(router.urls)),
]
