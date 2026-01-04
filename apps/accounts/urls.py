"""
URL configuration for accounts app (web views).
"""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    # Authentication
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("verify-2fa/", views.verify_2fa_view, name="verify_2fa"),
    # Password management
    path("password/change/", views.change_password, name="change_password"),
    path("password/reset/", views.password_reset_request, name="password_reset"),
    path(
        "password/reset/<uidb64>/<token>/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
    # Profile
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    # Two-Factor Authentication
    path("2fa/setup/", views.setup_2fa, name="setup_2fa"),
    path("2fa/disable/", views.disable_2fa, name="disable_2fa"),
    # Lockout
    path("lockout/", views.lockout_view, name="lockout"),
]
