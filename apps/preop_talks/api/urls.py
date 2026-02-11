"""
API URL configuration for pre-operational talks.
"""

from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import PreopTalkViewSet, TalkTemplateViewSet

app_name = "preop_talks_api"

router = DefaultRouter()
router.register(r"templates", TalkTemplateViewSet, basename="template")
router.register(r"talks", PreopTalkViewSet, basename="talk")

urlpatterns = [
    path("", include(router.urls)),
]
