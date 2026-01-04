"""
URL configuration for sync app.
"""

from django.urls import include, path

app_name = "sync"

urlpatterns = [
    path("api/", include("apps.sync.api.urls")),
]
