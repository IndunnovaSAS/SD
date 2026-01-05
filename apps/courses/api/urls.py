"""
API URL configuration for courses.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from . import views

app_name = "courses_api"

router = DefaultRouter()
router.register(r"categories", views.CategoryViewSet, basename="category")
router.register(r"courses", views.CourseViewSet, basename="course")
router.register(r"media-assets", views.MediaAssetViewSet, basename="media-asset")
router.register(r"enrollments", views.EnrollmentViewSet, basename="enrollment")
router.register(r"scorm-packages", views.ScormPackageViewSet, basename="scorm-package")
router.register(r"scorm-attempts", views.ScormAttemptViewSet, basename="scorm-attempt")
router.register(r"resources", views.ResourceLibraryViewSet, basename="resource")

# Nested routers for course -> modules -> lessons
courses_router = routers.NestedDefaultRouter(router, r"courses", lookup="course")
courses_router.register(r"modules", views.ModuleViewSet, basename="course-module")
courses_router.register(r"versions", views.CourseVersionViewSet, basename="course-version")

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
    # Course versioning
    path(
        "courses/<int:course_id>/create-version/",
        views.CreateCourseVersionView.as_view(),
        name="create-course-version",
    ),
]
