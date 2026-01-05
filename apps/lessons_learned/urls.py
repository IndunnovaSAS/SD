"""
URL configuration for lessons_learned app.
"""

from django.urls import path

from apps.lessons_learned import views

app_name = "lessons_learned"

urlpatterns = [
    # Lesson list and detail
    path("", views.lesson_list, name="list"),
    path("grid/", views.lesson_grid, name="grid"),
    path("<int:lesson_id>/", views.lesson_detail, name="detail"),

    # Create and edit
    path("create/", views.lesson_create, name="create"),
    path("<int:lesson_id>/edit/", views.lesson_edit, name="edit"),

    # Review workflow
    path("<int:lesson_id>/submit-review/", views.submit_for_review, name="submit-review"),
    path("<int:lesson_id>/approve/", views.approve_lesson, name="approve"),
    path("<int:lesson_id>/reject/", views.reject_lesson, name="reject"),

    # Comments
    path("<int:lesson_id>/comments/", views.add_comment, name="add-comment"),

    # My lessons
    path("my-lessons/", views.my_lessons, name="my-lessons"),
]
