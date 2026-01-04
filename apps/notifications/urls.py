"""
URL configuration for notifications app.
"""

from django.urls import include, path

app_name = "notifications"

urlpatterns = [
    path("api/", include("apps.notifications.api.urls")),
]
