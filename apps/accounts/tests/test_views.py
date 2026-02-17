"""
Tests for accounts views.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class LoginViewTests(TestCase):
    """Tests for login view."""

    def setUp(self):
        self.client = Client()
        self.login_url = reverse("accounts:login")
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword123",
            first_name="Test",
            last_name="User",
            document_type="CC",
            document_number="12345678",
            hire_date=date(2024, 1, 1),
        )

    def test_login_page_loads(self):
        """Test that login page loads correctly."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")

    def test_login_with_valid_credentials(self):
        """Test login with valid credentials redirects to dashboard."""
        response = self.client.post(
            self.login_url,
            {"username": "12345678", "password": "testpassword123"},
        )
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials shows error."""
        response = self.client.post(
            self.login_url,
            {"username": "12345678", "password": "wrongpassword"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Credenciales inválidas")

    def test_authenticated_user_redirected(self):
        """Test authenticated user is redirected from login page."""
        self.client.login(username="12345678", password="testpassword123")
        response = self.client.get(self.login_url)
        self.assertRedirects(response, reverse("accounts:dashboard"))


class DashboardViewTests(TestCase):
    """Tests for dashboard view."""

    def setUp(self):
        self.client = Client()
        self.dashboard_url = reverse("accounts:dashboard")
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword123",
            first_name="Test",
            last_name="User",
            document_type="CC",
            document_number="12345678",
            hire_date=date(2024, 1, 1),
        )

    def test_dashboard_requires_login(self):
        """Test dashboard requires authentication."""
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.dashboard_url}")

    def test_dashboard_accessible_when_logged_in(self):
        """Test dashboard is accessible when logged in."""
        self.client.login(username="12345678", password="testpassword123")
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)


class ProfileViewTests(TestCase):
    """Tests for profile views."""

    def setUp(self):
        self.client = Client()
        self.profile_url = reverse("accounts:profile")
        self.profile_edit_url = reverse("accounts:profile_edit")
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword123",
            first_name="Test",
            last_name="User",
            document_type="CC",
            document_number="12345678",
            hire_date=date(2024, 1, 1),
        )
        self.client.login(username="12345678", password="testpassword123")

    def test_profile_page_loads(self):
        """Test profile page loads correctly."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test User")

    def test_profile_edit_page_loads(self):
        """Test profile edit page loads correctly."""
        response = self.client.get(self.profile_edit_url)
        self.assertEqual(response.status_code, 200)

    def test_profile_update(self):
        """Test profile can be updated."""
        response = self.client.post(
            self.profile_edit_url,
            {
                "first_name": "Updated",
                "last_name": "Name",
                "phone": "3001234567",
            },
        )
        self.assertRedirects(response, self.profile_url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.last_name, "Name")


class PasswordResetViewTests(TestCase):
    """Tests for password reset views."""

    def setUp(self):
        self.client = Client()
        self.password_reset_url = reverse("accounts:password_reset")
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword123",
            first_name="Test",
            last_name="User",
            document_type="CC",
            document_number="12345678",
            hire_date=date(2024, 1, 1),
        )

    def test_password_reset_page_loads(self):
        """Test password reset page loads correctly."""
        response = self.client.get(self.password_reset_url)
        self.assertEqual(response.status_code, 200)

    def test_password_reset_request_sent(self):
        """Test password reset request is processed."""
        response = self.client.post(
            self.password_reset_url,
            {"email": "test@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Revise su correo")


class LogoutViewTests(TestCase):
    """Tests for logout view."""

    def setUp(self):
        self.client = Client()
        self.logout_url = reverse("accounts:logout")
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword123",
            first_name="Test",
            last_name="User",
            document_type="CC",
            document_number="12345678",
            hire_date=date(2024, 1, 1),
        )

    def test_logout_confirmation_page(self):
        """Test logout confirmation page loads."""
        self.client.login(username="12345678", password="testpassword123")
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "¿Desea cerrar sesión?")

    def test_logout_post(self):
        """Test logout via POST."""
        self.client.login(username="12345678", password="testpassword123")
        response = self.client.post(self.logout_url)
        self.assertRedirects(response, reverse("accounts:login"))
