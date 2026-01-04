"""
API URL configuration for user management.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"", views.UserViewSet, basename="user")

app_name = "users_api"

urlpatterns = [
    path("", include(router.urls)),
    path("import/", views.ImportUsersView.as_view(), name="import_users"),
]
