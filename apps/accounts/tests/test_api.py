"""
Tests for accounts API.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class JWTAuthenticationTests(APITestCase):
    """Tests for JWT authentication endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword123",
            first_name="Test",
            last_name="User",
            document_type="CC",
            document_number="12345678",
            hire_date=date(2024, 1, 1),
        )
        self.token_url = reverse("accounts_api:token_obtain_pair")
        self.token_refresh_url = reverse("accounts_api:token_refresh")
        self.token_verify_url = reverse("accounts_api:token_verify")

    def test_obtain_token_pair(self):
        """Test obtaining JWT token pair."""
        response = self.client.post(
            self.token_url,
            {"document_number": "12345678", "password": "testpassword123"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_obtain_token_invalid_credentials(self):
        """Test token request with invalid credentials."""
        response = self.client.post(
            self.token_url,
            {"document_number": "12345678", "password": "wrongpassword"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token(self):
        """Test refreshing JWT token."""
        # First get tokens
        response = self.client.post(
            self.token_url,
            {"document_number": "12345678", "password": "testpassword123"},
        )
        refresh_token = response.data["refresh"]

        # Refresh the token
        response = self.client.post(
            self.token_refresh_url,
            {"refresh": refresh_token},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_verify_token(self):
        """Test verifying JWT token."""
        # First get tokens
        response = self.client.post(
            self.token_url,
            {"document_number": "12345678", "password": "testpassword123"},
        )
        access_token = response.data["access"]

        # Verify the token
        response = self.client.post(
            self.token_verify_url,
            {"token": access_token},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CurrentUserAPITests(APITestCase):
    """Tests for current user API endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword123",
            first_name="Test",
            last_name="User",
            document_type="CC",
            document_number="12345678",
            hire_date=date(2024, 1, 1),
        )
        self.me_url = reverse("accounts_api:current_user")

    def test_get_current_user_unauthenticated(self):
        """Test accessing current user without authentication."""
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_current_user_authenticated(self):
        """Test accessing current user with authentication."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "test@example.com")
        self.assertEqual(response.data["first_name"], "Test")

    def test_update_current_user(self):
        """Test updating current user profile."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.me_url,
            {"first_name": "Updated", "phone": "3001234567"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.phone, "3001234567")


class ChangePasswordAPITests(APITestCase):
    """Tests for change password API endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword123",
            first_name="Test",
            last_name="User",
            document_type="CC",
            document_number="12345678",
            hire_date=date(2024, 1, 1),
        )
        self.change_password_url = reverse("accounts_api:change_password")

    def test_change_password_success(self):
        """Test changing password successfully."""
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            self.change_password_url,
            {
                "old_password": "testpassword123",
                "new_password": "newpassword456!",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_change_password_wrong_old_password(self):
        """Test changing password with wrong old password."""
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            self.change_password_url,
            {
                "old_password": "wrongpassword",
                "new_password": "newpassword456!",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserViewSetTests(APITestCase):
    """Tests for UserViewSet."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpassword123",
            first_name="Admin",
            last_name="User",
            document_type="CC",
            document_number="00000000",
            hire_date=date(2024, 1, 1),
        )
        self.regular_user = User.objects.create_user(
            email="regular@example.com",
            password="regularpassword123",
            first_name="Regular",
            last_name="User",
            document_type="CC",
            document_number="11111111",
            hire_date=date(2024, 1, 1),
        )
        self.users_url = reverse("accounts_api:users-list")

    def test_list_users_authenticated(self):
        """Test listing users as authenticated user."""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_activate_action(self):
        """Test activating a user."""
        self.regular_user.is_active = False
        self.regular_user.save()

        self.client.force_authenticate(user=self.admin_user)
        url = reverse("accounts_api:users-activate", kwargs={"pk": self.regular_user.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.is_active)

    def test_user_deactivate_action(self):
        """Test deactivating a user."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("accounts_api:users-deactivate", kwargs={"pk": self.regular_user.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.regular_user.refresh_from_db()
        self.assertFalse(self.regular_user.is_active)
