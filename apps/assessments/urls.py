"""
URL configuration for assessments app.
"""

from django.urls import include, path

app_name = "assessments"

urlpatterns = [
    path("api/", include("apps.assessments.api.urls")),
]
