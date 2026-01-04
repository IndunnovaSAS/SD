"""
Serializers for certifications API.
"""

from rest_framework import serializers

from apps.certifications.models import (
    Certificate,
    CertificateTemplate,
    CertificateVerification,
)


class CertificateTemplateSerializer(serializers.ModelSerializer):
    """Serializer for CertificateTemplate model."""

    class Meta:
        model = CertificateTemplate
        fields = [
            "id",
            "name",
            "description",
            "template_file",
            "background_image",
            "logo",
            "signature_image",
            "signer_name",
            "signer_title",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CertificateTemplateListSerializer(serializers.ModelSerializer):
    """Simplified serializer for template lists."""

    class Meta:
        model = CertificateTemplate
        fields = ["id", "name", "description", "is_active"]


class CertificateSerializer(serializers.ModelSerializer):
    """Serializer for Certificate model."""

    user_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source="user.email", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    template_name = serializers.CharField(source="template.name", read_only=True)

    class Meta:
        model = Certificate
        fields = [
            "id",
            "user",
            "user_name",
            "user_email",
            "course",
            "course_title",
            "template",
            "template_name",
            "certificate_number",
            "status",
            "score",
            "certificate_file",
            "issued_at",
            "expires_at",
            "revoked_at",
            "revoked_reason",
            "verification_url",
            "qr_code",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "certificate_number",
            "certificate_file",
            "issued_at",
            "revoked_at",
            "verification_url",
            "qr_code",
            "created_at",
            "updated_at",
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name()


class CertificateListSerializer(serializers.ModelSerializer):
    """Simplified serializer for certificate lists."""

    user_name = serializers.SerializerMethodField()
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = Certificate
        fields = [
            "id",
            "user",
            "user_name",
            "course_title",
            "certificate_number",
            "status",
            "score",
            "issued_at",
            "expires_at",
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name()


class CertificateCreateSerializer(serializers.Serializer):
    """Serializer for creating a certificate."""

    user_id = serializers.IntegerField()
    course_id = serializers.IntegerField()
    template_id = serializers.IntegerField(required=False, allow_null=True)
    score = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )


class CertificateVerifySerializer(serializers.Serializer):
    """Serializer for verifying a certificate."""

    certificate_number = serializers.CharField()


class CertificateRevokeSerializer(serializers.Serializer):
    """Serializer for revoking a certificate."""

    reason = serializers.CharField(required=True)


class CertificateVerificationSerializer(serializers.ModelSerializer):
    """Serializer for CertificateVerification model."""

    certificate_number = serializers.CharField(
        source="certificate.certificate_number", read_only=True
    )

    class Meta:
        model = CertificateVerification
        fields = [
            "id",
            "certificate",
            "certificate_number",
            "verified_at",
            "ip_address",
            "is_valid",
        ]
        read_only_fields = ["id", "verified_at"]


class MyCertificateSerializer(serializers.ModelSerializer):
    """Serializer for user's own certificates."""

    course_title = serializers.CharField(source="course.title", read_only=True)
    course_code = serializers.CharField(source="course.code", read_only=True)

    class Meta:
        model = Certificate
        fields = [
            "id",
            "course",
            "course_title",
            "course_code",
            "certificate_number",
            "status",
            "score",
            "certificate_file",
            "issued_at",
            "expires_at",
            "verification_url",
            "qr_code",
        ]
