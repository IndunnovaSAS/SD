"""
URL configuration for learning_paths app.
"""

from django.urls import include, path

from . import views

app_name = "learning_paths"

urlpatterns = [
    # API
    path("api/", include("apps.learning_paths.api.urls")),
    # Web views
    path("", views.learning_path_list, name="list"),
    path("my-paths/", views.my_learning_paths, name="my_paths"),
    path("create/", views.learning_path_create, name="create"),
    path("<int:path_id>/", views.learning_path_detail, name="detail"),
    path("<int:path_id>/join/", views.join_learning_path, name="join"),
]
