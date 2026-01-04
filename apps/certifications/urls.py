"""
URL configuration for certifications app.
"""

from django.urls import include, path

from . import views

app_name = "certifications"

urlpatterns = [
    # API
    path("api/", include("apps.certifications.api.urls")),
    # Web views
    path("", views.my_certificates, name="my_certificates"),
    path("<int:certificate_id>/", views.certificate_detail, name="detail"),
    path("<int:certificate_id>/download/", views.certificate_download, name="download"),
    path("verify/", views.verify_certificate, name="verify"),
    path("verify/<str:certificate_number>/", views.verify_certificate, name="verify_number"),
]
