"""
URL configuration for assessments app.
"""

from django.urls import include, path

from . import views

app_name = "assessments"

urlpatterns = [
    # API
    path("api/", include("apps.assessments.api.urls")),
    # Web views
    path("", views.assessment_list, name="list"),
    path("<int:assessment_id>/", views.assessment_detail, name="detail"),
    path("<int:assessment_id>/start/", views.start_attempt, name="start"),
    path("take/<int:attempt_id>/", views.take_assessment, name="take"),
    path("take/<int:attempt_id>/save/", views.save_answer, name="save_answer"),
    path("take/<int:attempt_id>/submit/", views.submit_attempt, name="submit"),
    path("result/<int:attempt_id>/", views.attempt_result, name="result"),
    path("my-attempts/", views.my_attempts, name="my_attempts"),
]
