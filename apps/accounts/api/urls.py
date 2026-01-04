"""
API URL configuration for authentication.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

app_name = "accounts_api"

urlpatterns = [
    # JWT Authentication
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # User management
    path("me/", views.CurrentUserView.as_view(), name="current_user"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("password/change/", views.ChangePasswordView.as_view(), name="change_password"),
]
