"""
API URL configuration for assessments.
"""

from django.urls import include, path

from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    AnswerViewSet,
    AssessmentAttemptViewSet,
    AssessmentViewSet,
    QuestionViewSet,
)

app_name = "assessments_api"

router = DefaultRouter()
router.register(r"assessments", AssessmentViewSet, basename="assessment")
router.register(r"attempts", AssessmentAttemptViewSet, basename="attempt")

# Nested router for questions under assessments
assessments_router = routers.NestedDefaultRouter(router, r"assessments", lookup="assessment")
assessments_router.register(r"questions", QuestionViewSet, basename="assessment-questions")

# Nested router for answers under questions
questions_router = routers.NestedDefaultRouter(assessments_router, r"questions", lookup="question")
questions_router.register(r"answers", AnswerViewSet, basename="question-answers")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(assessments_router.urls)),
    path("", include(questions_router.urls)),
]
