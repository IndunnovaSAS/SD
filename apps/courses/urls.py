"""
URL configuration for courses app.
"""

from django.urls import include, path

from . import views

app_name = "courses"

urlpatterns = [
    # API
    path("api/", include("apps.courses.api.urls")),
    # Web views
    path("", views.course_list, name="list"),
    path("my-courses/", views.my_courses, name="my_courses"),
    path("<int:course_id>/", views.course_detail, name="detail"),
    path("<int:course_id>/enroll/", views.enroll_course, name="enroll"),
    path(
        "<int:course_id>/lessons/<int:lesson_id>/",
        views.lesson_view,
        name="lesson",
    ),
    path(
        "<int:course_id>/lessons/<int:lesson_id>/progress/",
        views.update_progress,
        name="update_progress",
    ),
]
