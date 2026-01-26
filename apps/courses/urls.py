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
    path("create/", views.course_create, name="create"),
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
    # Category management (Maestros)
    path("categories/", views.category_list, name="category_list"),
    path("categories/create/", views.category_create, name="category_create"),
    path("categories/<int:category_id>/edit/", views.category_edit, name="category_edit"),
    path("categories/<int:category_id>/delete/", views.category_delete, name="category_delete"),
]
