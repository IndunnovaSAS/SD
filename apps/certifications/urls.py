"""
URL configuration for certifications app.
"""

from django.urls import include, path

app_name = "certifications"

urlpatterns = [
    path("api/", include("apps.certifications.api.urls")),
]
