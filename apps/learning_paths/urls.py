"""
URL configuration for learning_paths app.
"""

from django.urls import include, path

app_name = "learning_paths"

urlpatterns = [
    path("api/", include("apps.learning_paths.api.urls")),
]
