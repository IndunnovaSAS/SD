"""
API URL configuration for courses.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from . import views

app_name = "courses_api"

router = DefaultRouter()
router.register(r"courses", views.CourseViewSet, basename="course")
router.register(r"media-assets", views.MediaAssetViewSet, basename="media-asset")
router.register(r"enrollments", views.EnrollmentViewSet, basename="enrollment")

# Nested routers for course -> modules -> lessons
courses_router = routers.NestedDefaultRouter(router, r"courses", lookup="course")
courses_router.register(r"modules", views.ModuleViewSet, basename="course-module")

modules_router = routers.NestedDefaultRouter(courses_router, r"modules", lookup="module")
modules_router.register(r"lessons", views.LessonViewSet, basename="module-lesson")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(courses_router.urls)),
    path("", include(modules_router.urls)),
    # User-specific endpoints
    path("my-enrollments/", views.MyEnrollmentsView.as_view(), name="my-enrollments"),
    path(
        "enrollments/<int:enrollment_id>/progress/",
        views.LessonProgressView.as_view(),
        name="enrollment-progress",
    ),
    path(
        "enrollments/<int:enrollment_id>/lessons/<int:lesson_id>/progress/",
        views.LessonProgressView.as_view(),
        name="lesson-progress",
    ),
]
