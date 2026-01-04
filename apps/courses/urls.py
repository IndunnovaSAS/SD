"""
URL configuration for courses app.
"""

from django.urls import include, path

app_name = "courses"

urlpatterns = [
    path("api/", include("apps.courses.api.urls")),
]
