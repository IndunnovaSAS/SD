"""
Tests for certification services.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.certifications.models import (
    Certificate,
    CertificateTemplate,
    CertificateVerification,
)
from apps.certifications.services import CertificateService, CertificateTemplateService
from apps.courses.models import Course, Enrollment


def mock_generate_certificate_file(certificate):
    """Mock that skips PDF/QR generation and just sets the certificate as issued."""
    certificate.status = Certificate.Status.ISSUED
    certificate.issued_at = timezone.now()
    certificate.verification_url = f"https://example.com/verify/{certificate.certificate_number}/"
    certificate.save()
    return certificate


class CertificateServiceTest(TestCase):
    """Tests for CertificateService."""

    def setUp(self):
        """Set up test data."""
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            first_name="Admin",
            last_name="User",
            document_number="123456789",
            job_position="Administrator",
            hire_date=date(2020, 1, 1),
            is_staff=True,
        )
        self.user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Juan",
            last_name="Pérez",
            document_number="987654321",
            job_position="Technician",
            hire_date=date(2021, 6, 15),
        )

        # Create course
        self.course = Course.objects.create(
            code="TEST-001",
            title="Test Course",
            duration=60,
            created_by=self.admin,
            status=Course.Status.PUBLISHED,
            validity_months=12,
        )

        # Create enrollment (completed)
        self.enrollment = Enrollment.objects.create(
            user=self.user,
            course=self.course,
            status=Enrollment.Status.COMPLETED,
            progress=100,
        )

        # Create template
        self.template = CertificateTemplate.objects.create(
            name="Default Template",
            signer_name="Director de Capacitación",
            signer_title="S.D. S.A.S.",
            is_active=True,
        )

    def test_generate_certificate_number(self):
        """Test certificate number generation."""
        number = CertificateService.generate_certificate_number()

        self.assertTrue(number.startswith("SD-"))
        # Format: SD-YYYYMM-XXXXXXXX = 3 + 6 + 1 + 8 = 18 characters
        self.assertEqual(len(number), 18)

    def test_calculate_expiry_date(self):
        """Test expiry date calculation."""
        expiry = CertificateService.calculate_expiry_date(self.course)

        expected = timezone.now() + timedelta(days=12 * 30)
        self.assertIsNotNone(expiry)
        # Allow 1 day tolerance
        self.assertAlmostEqual(
            expiry.timestamp(),
            expected.timestamp(),
            delta=86400,
        )

    def test_calculate_expiry_no_validity(self):
        """Test no expiry when course has no validity period."""
        self.course.validity_months = None
        self.course.save()

        expiry = CertificateService.calculate_expiry_date(self.course)

        self.assertIsNone(expiry)

    def test_can_issue_certificate(self):
        """Test checking if certificate can be issued."""
        result = CertificateService.can_issue_certificate(self.user, self.course)

        self.assertTrue(result["can_issue"])
        self.assertIsNone(result["reason"])
        self.assertEqual(result["enrollment"], self.enrollment)

    def test_cannot_issue_not_enrolled(self):
        """Test cannot issue when not enrolled."""
        other_user = User.objects.create_user(
            email="other@test.com",
            password="testpass123",
            first_name="Other",
            last_name="User",
            document_number="111111111",
            job_position="Technician",
            hire_date=date(2022, 1, 1),
        )

        result = CertificateService.can_issue_certificate(other_user, self.course)

        self.assertFalse(result["can_issue"])
        self.assertIn("no está inscrito", result["reason"])

    def test_cannot_issue_not_completed(self):
        """Test cannot issue when course not completed."""
        self.enrollment.status = Enrollment.Status.IN_PROGRESS
        self.enrollment.save()

        result = CertificateService.can_issue_certificate(self.user, self.course)

        self.assertFalse(result["can_issue"])
        self.assertIn("no ha completado", result["reason"])

    def test_cannot_issue_duplicate(self):
        """Test cannot issue duplicate valid certificate."""
        # Create existing valid certificate
        Certificate.objects.create(
            user=self.user,
            course=self.course,
            certificate_number="SD-TEST-00000001",
            status=Certificate.Status.ISSUED,
            issued_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=365),
        )

        result = CertificateService.can_issue_certificate(self.user, self.course)

        self.assertFalse(result["can_issue"])
        self.assertIn("Ya existe un certificado", result["reason"])

    @patch.object(CertificateService, 'generate_certificate_file', side_effect=mock_generate_certificate_file)
    def test_issue_certificate(self, mock_gen):
        """Test issuing a certificate."""
        certificate = CertificateService.issue_certificate(
            user=self.user,
            course=self.course,
            template=self.template,
        )

        self.assertIsNotNone(certificate)
        self.assertEqual(certificate.user, self.user)
        self.assertEqual(certificate.course, self.course)
        self.assertEqual(certificate.status, Certificate.Status.ISSUED)
        self.assertTrue(certificate.certificate_number.startswith("SD-"))
        self.assertIsNotNone(certificate.issued_at)

    @patch.object(CertificateService, 'generate_certificate_file', side_effect=mock_generate_certificate_file)
    def test_issue_certificate_with_score(self, mock_gen):
        """Test issuing certificate with specific score."""
        certificate = CertificateService.issue_certificate(
            user=self.user,
            course=self.course,
            score=95.5,
        )

        self.assertEqual(float(certificate.score), 95.5)

    @patch.object(CertificateService, 'generate_certificate_file', side_effect=mock_generate_certificate_file)
    def test_verify_certificate_valid(self, mock_gen):
        """Test verifying a valid certificate."""
        certificate = CertificateService.issue_certificate(
            user=self.user,
            course=self.course,
        )

        result = CertificateService.verify_certificate(
            certificate.certificate_number,
            ip_address="127.0.0.1",
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["certificate"]["number"], certificate.certificate_number)
        self.assertEqual(result["certificate"]["user_name"], "Juan Pérez")

        # Check verification was logged
        self.assertEqual(CertificateVerification.objects.count(), 1)

    def test_verify_certificate_not_found(self):
        """Test verifying non-existent certificate."""
        result = CertificateService.verify_certificate("SD-INVALID-00000000")

        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "Certificado no encontrado")

    @patch.object(CertificateService, 'generate_certificate_file', side_effect=mock_generate_certificate_file)
    def test_verify_certificate_revoked(self, mock_gen):
        """Test verifying revoked certificate."""
        certificate = CertificateService.issue_certificate(
            user=self.user,
            course=self.course,
        )
        CertificateService.revoke_certificate(
            certificate,
            reason="Datos incorrectos",
        )

        result = CertificateService.verify_certificate(certificate.certificate_number)

        self.assertFalse(result["valid"])
        self.assertIn("revocado", result["reason"])

    def test_verify_certificate_expired(self):
        """Test verifying expired certificate."""
        certificate = Certificate.objects.create(
            user=self.user,
            course=self.course,
            certificate_number="SD-TEST-EXPIRED1",
            status=Certificate.Status.ISSUED,
            issued_at=timezone.now() - timedelta(days=400),
            expires_at=timezone.now() - timedelta(days=30),
        )

        result = CertificateService.verify_certificate(certificate.certificate_number)

        self.assertFalse(result["valid"])
        self.assertIn("expirado", result["reason"])

        # Check certificate was marked as expired
        certificate.refresh_from_db()
        self.assertEqual(certificate.status, Certificate.Status.EXPIRED)

    @patch.object(CertificateService, 'generate_certificate_file', side_effect=mock_generate_certificate_file)
    def test_revoke_certificate(self, mock_gen):
        """Test revoking a certificate."""
        certificate = CertificateService.issue_certificate(
            user=self.user,
            course=self.course,
        )

        revoked = CertificateService.revoke_certificate(
            certificate,
            reason="Fraude detectado",
            revoked_by=self.admin,
        )

        self.assertEqual(revoked.status, Certificate.Status.REVOKED)
        self.assertIsNotNone(revoked.revoked_at)
        self.assertEqual(revoked.revoked_reason, "Fraude detectado")

    @patch.object(CertificateService, 'generate_certificate_file', side_effect=mock_generate_certificate_file)
    def test_revoke_already_revoked(self, mock_gen):
        """Test cannot revoke already revoked certificate."""
        certificate = CertificateService.issue_certificate(
            user=self.user,
            course=self.course,
        )
        CertificateService.revoke_certificate(certificate, "First revoke")

        with self.assertRaises(ValueError):
            CertificateService.revoke_certificate(certificate, "Second revoke")

    @patch.object(CertificateService, 'generate_certificate_file', side_effect=mock_generate_certificate_file)
    def test_reissue_certificate(self, mock_gen):
        """Test reissuing a certificate."""
        original = CertificateService.issue_certificate(
            user=self.user,
            course=self.course,
        )
        original_number = original.certificate_number

        new_cert = CertificateService.reissue_certificate(
            original,
            reason="Nombre corregido",
        )

        # Original should be revoked
        original.refresh_from_db()
        self.assertEqual(original.status, Certificate.Status.REVOKED)

        # New certificate should be issued
        self.assertNotEqual(new_cert.certificate_number, original_number)
        self.assertEqual(new_cert.status, Certificate.Status.ISSUED)
        self.assertEqual(new_cert.metadata["reissued_from"], original_number)

    def test_get_expiring_certificates(self):
        """Test getting certificates expiring soon."""
        # Create certificate expiring in 15 days
        certificate = Certificate.objects.create(
            user=self.user,
            course=self.course,
            certificate_number="SD-TEST-EXPIRING",
            status=Certificate.Status.ISSUED,
            issued_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=15),
        )

        expiring = CertificateService.get_expiring_certificates(days_ahead=30)

        self.assertEqual(expiring.count(), 1)
        self.assertEqual(expiring.first().id, certificate.id)

    @patch.object(CertificateService, 'generate_certificate_file', side_effect=mock_generate_certificate_file)
    def test_get_user_certificates(self, mock_gen):
        """Test getting user's certificates."""
        CertificateService.issue_certificate(self.user, self.course)

        certificates = CertificateService.get_user_certificates(self.user)

        self.assertEqual(certificates.count(), 1)

    def test_check_and_expire_certificates(self):
        """Test batch expiry check."""
        # Create expired certificate
        Certificate.objects.create(
            user=self.user,
            course=self.course,
            certificate_number="SD-TEST-TOEXPIRE",
            status=Certificate.Status.ISSUED,
            issued_at=timezone.now() - timedelta(days=400),
            expires_at=timezone.now() - timedelta(days=1),
        )

        count = CertificateService.check_and_expire_certificates()

        self.assertEqual(count, 1)

    @patch.object(CertificateService, 'generate_certificate_file', side_effect=mock_generate_certificate_file)
    def test_get_certificate_statistics(self, mock_gen):
        """Test getting certificate statistics."""
        CertificateService.issue_certificate(self.user, self.course)

        stats = CertificateService.get_certificate_statistics()

        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["issued"], 1)
        self.assertEqual(stats["active_rate"], 100)


class CertificateTemplateServiceTest(TestCase):
    """Tests for CertificateTemplateService."""

    def setUp(self):
        """Set up test data."""
        self.template = CertificateTemplate.objects.create(
            name="Test Template",
            description="A test template",
            signer_name="Director",
            signer_title="CEO",
            is_active=True,
        )

    def test_duplicate_template(self):
        """Test duplicating a template."""
        new_template = CertificateTemplateService.duplicate_template(self.template)

        self.assertNotEqual(new_template.id, self.template.id)
        self.assertEqual(new_template.name, "Test Template (Copia)")
        self.assertFalse(new_template.is_active)  # Duplicates start inactive

    def test_duplicate_template_custom_name(self):
        """Test duplicating with custom name."""
        new_template = CertificateTemplateService.duplicate_template(
            self.template,
            new_name="Custom Name",
        )

        self.assertEqual(new_template.name, "Custom Name")
