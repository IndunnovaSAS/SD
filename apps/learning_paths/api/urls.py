"""
API URL configuration for learning paths.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "learning_paths_api"

router = DefaultRouter()
router.register(r"paths", views.LearningPathViewSet, basename="path")
router.register(r"assignments", views.PathAssignmentViewSet, basename="assignment")

urlpatterns = [
    path("", include(router.urls)),
    path("my-paths/", views.MyLearningPathsView.as_view(), name="my-paths"),
    path("paths/<int:pk>/join/", views.JoinLearningPathView.as_view(), name="join-path"),
]
