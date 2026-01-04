"""
URL configuration for preop_talks app.
"""

from django.urls import include, path

app_name = "preop_talks"

urlpatterns = [
    path("api/", include("apps.preop_talks.api.urls")),
]
