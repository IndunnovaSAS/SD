"""
Admin configuration for certifications app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Certificate, CertificateTemplate, CertificateVerification


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    """Admin configuration for CertificateTemplate model."""

    list_display = ["name", "signer_name", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    """Admin configuration for Certificate model."""

    list_display = [
        "certificate_number",
        "user",
        "course",
        "status",
        "score",
        "issued_at",
        "expires_at",
    ]
    list_filter = ["status", "issued_at", "expires_at"]
    search_fields = ["certificate_number", "user__email", "course__title"]
    readonly_fields = [
        "certificate_number",
        "created_at",
        "updated_at",
        "issued_at",
        "revoked_at",
    ]
    raw_id_fields = ["user"]
    autocomplete_fields = ["course", "template"]

    fieldsets = [
        (
            None,
            {
                "fields": ["certificate_number", "user", "course", "template"],
            },
        ),
        (
            _("Resultado"),
            {
                "fields": ["score", "status"],
            },
        ),
        (
            _("Archivos"),
            {
                "fields": ["certificate_file", "qr_code", "verification_url"],
            },
        ),
        (
            _("Fechas"),
            {
                "fields": ["issued_at", "expires_at", "revoked_at", "revoked_reason"],
            },
        ),
        (
            _("Metadatos"),
            {
                "fields": ["metadata"],
                "classes": ["collapse"],
            },
        ),
    ]


@admin.register(CertificateVerification)
class CertificateVerificationAdmin(admin.ModelAdmin):
    """Admin configuration for CertificateVerification model."""

    list_display = ["certificate", "verified_at", "is_valid", "ip_address"]
    list_filter = ["is_valid", "verified_at"]
    readonly_fields = ["verified_at", "ip_address", "user_agent"]
