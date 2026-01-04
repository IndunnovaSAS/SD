"""
URL configuration for integrations app.
"""

from django.urls import include, path

app_name = "integrations"

urlpatterns = [
    path("api/", include("apps.integrations.api.urls")),
]
