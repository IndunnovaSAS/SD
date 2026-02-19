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
    # Parametrizacion hub
    path("parametrizacion/", views.parametrizacion_hub, name="parametrizacion"),
    # Course admin management (Parametrizacion)
    path("admin-courses/", views.course_admin_list, name="course_admin_list"),
    path(
        "admin-courses/<int:course_id>/edit-params/",
        views.course_edit_params,
        name="course_edit_params",
    ),
    path(
        "admin-courses/<int:course_id>/toggle-status/",
        views.course_toggle_status,
        name="course_toggle_status",
    ),
    path(
        "admin-courses/<int:course_id>/edit/",
        views.course_full_edit,
        name="course_full_edit",
    ),
    path(
        "admin-courses/<int:course_id>/delete/",
        views.course_delete,
        name="course_delete",
    ),
    # Job Profile Type management (Parametrizacion)
    path("profiles/create/", views.profile_type_create, name="profile_type_create"),
    path("profiles/<int:profile_id>/edit/", views.profile_type_edit, name="profile_type_edit"),
    path(
        "profiles/<int:profile_id>/delete/", views.profile_type_delete, name="profile_type_delete"
    ),
    path(
        "profiles/<int:profile_id>/toggle/",
        views.profile_type_toggle_active,
        name="profile_type_toggle",
    ),
    # Category management (Maestros)
    path("categories/", views.category_list, name="category_list"),
    path("categories/create/", views.category_create, name="category_create"),
    path("categories/<int:category_id>/edit/", views.category_edit, name="category_edit"),
    path("categories/<int:category_id>/delete/", views.category_delete, name="category_delete"),
    path(
        "categories/<int:category_id>/toggle/", views.category_toggle_active, name="category_toggle"
    ),
    # Course Builder
    path(
        "admin-courses/<int:course_id>/builder/",
        views.course_builder,
        name="course_builder",
    ),
    path(
        "admin-courses/<int:course_id>/builder/update-info/",
        views.builder_update_course_info,
        name="builder_update_course_info",
    ),
    path(
        "admin-courses/<int:course_id>/builder/modules/add/",
        views.builder_add_module,
        name="builder_add_module",
    ),
    path(
        "admin-courses/<int:course_id>/builder/modules/<int:module_id>/edit/",
        views.builder_edit_module,
        name="builder_edit_module",
    ),
    path(
        "admin-courses/<int:course_id>/builder/modules/<int:module_id>/delete/",
        views.builder_delete_module,
        name="builder_delete_module",
    ),
    path(
        "admin-courses/<int:course_id>/builder/modules/reorder/",
        views.builder_reorder_modules,
        name="builder_reorder_modules",
    ),
    path(
        "admin-courses/<int:course_id>/builder/modules/<int:module_id>/lessons/add/",
        views.builder_add_lesson,
        name="builder_add_lesson",
    ),
    path(
        "admin-courses/<int:course_id>/builder/modules/<int:module_id>/lessons/<int:lesson_id>/edit/",
        views.builder_edit_lesson,
        name="builder_edit_lesson",
    ),
    path(
        "admin-courses/<int:course_id>/builder/modules/<int:module_id>/lessons/<int:lesson_id>/delete/",
        views.builder_delete_lesson,
        name="builder_delete_lesson",
    ),
    path(
        "admin-courses/<int:course_id>/builder/modules/<int:module_id>/lessons/reorder/",
        views.builder_reorder_lessons,
        name="builder_reorder_lessons",
    ),
    path(
        "admin-courses/<int:course_id>/builder/modules/<int:module_id>/lessons/<int:lesson_id>/assign-quiz/",
        views.builder_assign_quiz,
        name="builder_assign_quiz",
    ),
    path(
        "admin-courses/<int:course_id>/builder/quiz/create/",
        views.builder_create_quiz,
        name="builder_create_quiz",
    ),
]
