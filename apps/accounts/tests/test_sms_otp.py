"""
Tests for SMS OTP verification system.
"""

from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import SMSOTPCode
from apps.accounts.services import SMSOTPService

User = get_user_model()


class SMSOTPServiceTests(TestCase):
    """Tests for SMSOTPService."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword123",
            first_name="Carlos",
            last_name="Perez",
            document_type="CC",
            document_number="1234567890",
            phone="+573001234567",
            job_position="Liniero",
            hire_date=date(2024, 1, 1),
        )

    def test_generate_code_length(self):
        code = SMSOTPService.generate_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_generate_code_preserves_leading_zeros(self):
        for _ in range(100):
            code = SMSOTPService.generate_code()
            self.assertEqual(len(code), 6)

    def test_create_otp_creates_record(self):
        otp = SMSOTPService.create_otp(self.user)
        self.assertIsNotNone(otp.id)
        self.assertEqual(otp.user, self.user)
        self.assertEqual(len(otp.code), 6)
        self.assertFalse(otp.is_used)
        self.assertFalse(otp.is_expired)

    def test_create_otp_invalidates_previous(self):
        otp1 = SMSOTPService.create_otp(self.user)
        SMSOTPService.create_otp(self.user)
        otp1.refresh_from_db()
        self.assertTrue(otp1.is_used)

    def test_create_otp_sets_expiry(self):
        otp = SMSOTPService.create_otp(self.user)
        expected = timezone.now() + timedelta(minutes=5)
        self.assertAlmostEqual(
            otp.expires_at.timestamp(),
            expected.timestamp(),
            delta=2,
        )

    def test_verify_code_success(self):
        otp = SMSOTPService.create_otp(self.user)
        is_valid, error = SMSOTPService.verify_code(self.user, otp.code)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_verify_code_wrong_code(self):
        SMSOTPService.create_otp(self.user)
        is_valid, error = SMSOTPService.verify_code(self.user, "000000")
        self.assertFalse(is_valid)
        self.assertIn("incorrecto", error)

    def test_verify_code_expired(self):
        otp = SMSOTPService.create_otp(self.user)
        otp.expires_at = timezone.now() - timedelta(minutes=1)
        otp.save()
        is_valid, error = SMSOTPService.verify_code(self.user, otp.code)
        self.assertFalse(is_valid)
        self.assertIn("expirado", error)

    def test_verify_code_already_used(self):
        otp = SMSOTPService.create_otp(self.user)
        otp.mark_used()
        is_valid, error = SMSOTPService.verify_code(self.user, otp.code)
        self.assertFalse(is_valid)
        self.assertIn("pendiente", error)

    def test_verify_code_max_attempts(self):
        otp = SMSOTPService.create_otp(self.user)
        for _ in range(5):
            SMSOTPService.verify_code(self.user, "999999")
        # After 5 attempts the OTP is locked
        is_valid, error = SMSOTPService.verify_code(self.user, otp.code)
        self.assertFalse(is_valid)

    def test_can_resend_initially(self):
        self.assertTrue(SMSOTPService.can_resend(self.user))

    def test_can_resend_respects_cooldown(self):
        SMSOTPService.create_otp(self.user)
        self.assertFalse(SMSOTPService.can_resend(self.user))

    def test_can_resend_after_cooldown(self):
        otp = SMSOTPService.create_otp(self.user)
        otp.created_at = timezone.now() - timedelta(seconds=61)
        otp.save()
        self.assertTrue(SMSOTPService.can_resend(self.user))

    def test_can_resend_hourly_limit(self):
        for i in range(5):
            otp = SMSOTPService.create_otp(self.user)
            otp.created_at = timezone.now() - timedelta(minutes=i * 2 + 2)
            otp.is_used = False
            otp.save()
        self.assertFalse(SMSOTPService.can_resend(self.user))

    def test_get_resend_wait_seconds_no_code(self):
        self.assertEqual(SMSOTPService.get_resend_wait_seconds(self.user), 0)

    def test_get_resend_wait_seconds_with_recent_code(self):
        SMSOTPService.create_otp(self.user)
        wait = SMSOTPService.get_resend_wait_seconds(self.user)
        self.assertGreater(wait, 0)
        self.assertLessEqual(wait, 60)

    @override_settings(SMS_OTP_ENABLED=False)
    def test_user_requires_sms_otp_disabled(self):
        self.assertFalse(SMSOTPService.user_requires_sms_otp(self.user))

    @override_settings(SMS_OTP_ENABLED=True)
    def test_user_requires_sms_otp_with_phone(self):
        self.assertTrue(SMSOTPService.user_requires_sms_otp(self.user))

    @override_settings(SMS_OTP_ENABLED=True, SMS_OTP_NO_PHONE_FALLBACK="skip")
    def test_user_requires_sms_otp_no_phone_skip(self):
        self.user.phone = ""
        self.user.save()
        self.assertFalse(SMSOTPService.user_requires_sms_otp(self.user))

    @override_settings(SMS_OTP_ENABLED=True, SMS_OTP_NO_PHONE_FALLBACK="block")
    def test_user_requires_sms_otp_no_phone_block(self):
        self.user.phone = ""
        self.user.save()
        self.assertTrue(SMSOTPService.user_requires_sms_otp(self.user))

    @patch.object(SMSOTPService, "_send_sms_sync", return_value=True)
    def test_send_otp_calls_sms(self, mock_sms):
        otp, sent = SMSOTPService.send_otp(self.user)
        self.assertTrue(sent)
        self.assertIsNotNone(otp)
        mock_sms.assert_called_once()

    def test_send_otp_no_phone_raises(self):
        self.user.phone = ""
        self.user.save()
        with self.assertRaises(ValueError):
            SMSOTPService.send_otp(self.user)

    def test_cleanup_expired_codes(self):
        otp = SMSOTPService.create_otp(self.user)
        otp.created_at = timezone.now() - timedelta(days=8)
        otp.save()
        deleted = SMSOTPService.cleanup_expired_codes(days=7)
        self.assertEqual(deleted, 1)


class SMSOTPModelTests(TestCase):
    """Tests for SMSOTPCode model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="model@example.com",
            password="testpassword123",
            first_name="Ana",
            last_name="Lopez",
            document_type="CC",
            document_number="9876543210",
            phone="+573009876543",
            job_position="Tecnico",
            hire_date=date(2024, 1, 1),
        )

    def test_str_representation(self):
        otp = SMSOTPService.create_otp(self.user)
        self.assertIn("pendiente", str(otp))
        otp.mark_used()
        self.assertIn("usado", str(otp))

    def test_is_expired_property(self):
        otp = SMSOTPService.create_otp(self.user)
        self.assertFalse(otp.is_expired)
        otp.expires_at = timezone.now() - timedelta(minutes=1)
        otp.save()
        self.assertTrue(otp.is_expired)

    def test_is_valid_property(self):
        otp = SMSOTPService.create_otp(self.user)
        self.assertTrue(otp.is_valid)
        otp.mark_used()
        self.assertFalse(otp.is_valid)

    def test_mark_used(self):
        otp = SMSOTPService.create_otp(self.user)
        otp.mark_used()
        otp.refresh_from_db()
        self.assertTrue(otp.is_used)
        self.assertIsNotNone(otp.used_at)

    def test_increment_attempts(self):
        otp = SMSOTPService.create_otp(self.user)
        self.assertEqual(otp.attempts, 0)
        otp.increment_attempts()
        otp.refresh_from_db()
        self.assertEqual(otp.attempts, 1)


@override_settings(SMS_OTP_ENABLED=True)
class SMSOTPViewTests(TestCase):
    """Integration tests for SMS OTP login flow."""

    def setUp(self):
        self.client = Client()
        self.login_url = reverse("accounts:login")
        self.verify_url = reverse("accounts:verify_sms_otp")
        self.resend_url = reverse("accounts:resend_sms_otp")
        self.user = User.objects.create_user(
            email="view@example.com",
            password="testpassword123",
            first_name="Carlos",
            last_name="Perez",
            document_type="CC",
            document_number="5555555555",
            phone="+573005555555",
            job_position="Liniero",
            hire_date=date(2024, 1, 1),
        )

    @patch.object(SMSOTPService, "_send_sms_sync", return_value=True)
    def test_login_redirects_to_sms_otp(self, mock_sms):
        response = self.client.post(
            self.login_url,
            {"username": "5555555555", "password": "testpassword123"},
        )
        self.assertRedirects(response, self.verify_url)
        self.assertIn("pending_sms_otp_user_id", self.client.session)

    @patch.object(SMSOTPService, "_send_sms_sync", return_value=True)
    def test_login_htmx_returns_otp_partial(self, mock_sms):
        response = self.client.post(
            self.login_url,
            {"username": "5555555555", "password": "testpassword123"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SMS")

    @patch.object(SMSOTPService, "_send_sms_sync", return_value=True)
    def test_verify_sms_otp_success(self, mock_sms):
        # Step 1: Login to trigger OTP
        self.client.post(
            self.login_url,
            {"username": "5555555555", "password": "testpassword123"},
        )
        # Step 2: Get the OTP code from DB
        otp = SMSOTPCode.objects.filter(user=self.user, is_used=False).latest("created_at")
        # Step 3: Submit OTP
        response = self.client.post(self.verify_url, {"code": otp.code})
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_verify_sms_otp_no_session(self):
        response = self.client.get(self.verify_url)
        self.assertRedirects(response, self.login_url)

    @patch.object(SMSOTPService, "_send_sms_sync", return_value=True)
    def test_verify_wrong_code(self, mock_sms):
        self.client.post(
            self.login_url,
            {"username": "5555555555", "password": "testpassword123"},
        )
        response = self.client.post(self.verify_url, {"code": "000000"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "incorrecto")

    @patch.object(SMSOTPService, "_send_sms_sync", return_value=True)
    def test_resend_otp(self, mock_sms):
        # Login to trigger OTP
        self.client.post(
            self.login_url,
            {"username": "5555555555", "password": "testpassword123"},
        )
        # Advance past cooldown
        otp = SMSOTPCode.objects.filter(user=self.user).latest("created_at")
        otp.created_at = timezone.now() - timedelta(seconds=61)
        otp.save()

        response = self.client.post(self.resend_url)
        # Should redirect back to verify page
        self.assertRedirects(response, self.verify_url)
        # New code should exist
        self.assertEqual(
            SMSOTPCode.objects.filter(user=self.user, is_used=False).count(),
            1,
        )

    @override_settings(SMS_OTP_ENABLED=False)
    def test_login_skips_otp_when_disabled(self):
        response = self.client.post(
            self.login_url,
            {"username": "5555555555", "password": "testpassword123"},
        )
        self.assertRedirects(response, reverse("accounts:dashboard"))

    @override_settings(SMS_OTP_ENABLED=True, SMS_OTP_NO_PHONE_FALLBACK="skip")
    def test_login_skips_otp_no_phone_skip_mode(self):
        self.user.phone = ""
        self.user.save()
        response = self.client.post(
            self.login_url,
            {"username": "5555555555", "password": "testpassword123"},
        )
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_resend_no_session_redirects(self):
        response = self.client.post(self.resend_url)
        self.assertRedirects(response, self.login_url)
