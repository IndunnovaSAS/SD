"""
URL configuration for lessons_learned app.
"""

from django.urls import include, path

app_name = "lessons_learned"

urlpatterns = [
    path("api/", include("apps.lessons_learned.api.urls")),
]
