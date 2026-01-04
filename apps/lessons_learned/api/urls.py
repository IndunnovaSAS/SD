"""
API URL configuration for lessons learned.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    LessonCommentViewSet,
    LessonLearnedViewSet,
)

app_name = "lessons_learned_api"

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"lessons", LessonLearnedViewSet, basename="lesson")
router.register(r"comments", LessonCommentViewSet, basename="comment")

urlpatterns = [
    path("", include(router.urls)),
]
