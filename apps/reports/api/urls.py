"""
API URL configuration for reports.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DashboardViewSet,
    GeneratedReportViewSet,
    ReportTemplateViewSet,
    ScheduledReportViewSet,
    UserDashboardViewSet,
)

app_name = "reports_api"

router = DefaultRouter()
router.register(r"templates", ReportTemplateViewSet, basename="template")
router.register(r"generated", GeneratedReportViewSet, basename="generated")
router.register(r"scheduled", ScheduledReportViewSet, basename="scheduled")
router.register(r"dashboards", DashboardViewSet, basename="dashboard")
router.register(r"user-dashboard", UserDashboardViewSet, basename="user-dashboard")

urlpatterns = [
    path("", include(router.urls)),
]
