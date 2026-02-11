"""
API URL configuration for authentication.
"""

from django.urls import include, path

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from . import views

app_name = "accounts_api"

router = DefaultRouter()
router.register(r"users", views.UserViewSet, basename="users")

urlpatterns = [
    # JWT Authentication
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("token/logout/", views.LogoutView.as_view(), name="token_logout"),
    # User management
    path("me/", views.CurrentUserView.as_view(), name="current_user"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("password/change/", views.ChangePasswordView.as_view(), name="change_password"),
    path("import/", views.ImportUsersView.as_view(), name="import_users"),
    # ViewSet routes
    path("", include(router.urls)),
]
