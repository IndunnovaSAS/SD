"""
URL configuration for reports app.
"""

from django.urls import include, path

app_name = "reports"

urlpatterns = [
    path("api/", include("apps.reports.api.urls")),
]
