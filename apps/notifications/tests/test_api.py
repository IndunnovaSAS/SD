"""
Tests for notifications API endpoints.
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.notifications.models import (
    Notification,
    NotificationTemplate,
    UserNotificationPreference,
)


class NotificationAPITests(TestCase):
    """Tests for Notification API endpoints."""

    def setUp(self):
        Notification.objects.all().delete()

        self.client = APIClient()
        self.user = User.objects.create_user(
            email="notiftest@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            document_number="12345678",
            job_position="Developer",
            job_profile="LINIERO",
            hire_date=date(2024, 1, 1),
        )
        self.admin = User.objects.create_user(
            email="notifadmin@example.com",
            password="testpass123",
            first_name="Admin",
            last_name="User",
            document_number="22345678",
            job_position="Admin",
            job_profile="LINIERO",
            hire_date=date(2024, 1, 1),
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

        self.notification = Notification.objects.create(
            user=self.user,
            channel="in_app",
            subject="Test Notification",
            body="This is a test notification",
            status=Notification.Status.SENT,
            sent_at=timezone.now(),
        )

    def test_list_notifications(self):
        """Test listing user's notifications."""
        url = reverse("notifications_api:notification-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)

    def test_mark_notification_read(self):
        """Test marking a notification as read."""
        url = reverse(
            "notifications_api:notification-mark-read",
            args=[self.notification.id],
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.notification.refresh_from_db()
        self.assertIsNotNone(self.notification.read_at)

    def test_mark_all_read(self):
        """Test marking all notifications as read."""
        # Create another unread notification
        Notification.objects.create(
            user=self.user,
            channel="in_app",
            subject="Another notification",
            body="Body",
            status=Notification.Status.SENT,
        )

        url = reverse("notifications_api:notification-mark-all-read")
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"], 2)

    def test_unread_count(self):
        """Test getting unread notification count."""
        url = reverse("notifications_api:notification-unread-count")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_send_notification_staff_only(self):
        """Test that only staff can send notifications."""
        url = reverse("notifications_api:notification-send")
        data = {
            "user_id": self.user.id,
            "subject": "Test",
            "body": "Test body",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_send_notification_as_staff(self):
        """Test sending notification as staff."""
        self.client.force_authenticate(user=self.admin)

        url = reverse("notifications_api:notification-send")
        data = {
            "user_id": self.user.id,
            "subject": "Admin Notification",
            "body": "Sent by admin",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["created"], 1)


class NotificationPreferenceAPITests(TestCase):
    """Tests for notification preference API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="preftest@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            document_number="32345678",
            job_position="Developer",
            job_profile="LINIERO",
            hire_date=date(2024, 1, 1),
        )
        self.client.force_authenticate(user=self.user)

    def test_get_preferences(self):
        """Test getting user preferences (auto-created)."""
        url = reverse("notifications_api:preference-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Preferences should be auto-created
        self.assertTrue(UserNotificationPreference.objects.filter(user=self.user).exists())

    def test_update_preferences(self):
        """Test updating notification preferences."""
        url = reverse("notifications_api:preference-update-preferences")
        data = {
            "email_enabled": False,
            "course_reminders": False,
        }
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["email_enabled"])
        self.assertFalse(response.data["course_reminders"])


class NotificationTemplateAPITests(TestCase):
    """Tests for notification template API endpoints."""

    def setUp(self):
        NotificationTemplate.objects.all().delete()

        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="templateadmin@example.com",
            password="testpass123",
            first_name="Admin",
            last_name="User",
            document_number="42345678",
            job_position="Admin",
            job_profile="LINIERO",
            hire_date=date(2024, 1, 1),
            is_staff=True,
        )
        self.client.force_authenticate(user=self.admin)

        self.template = NotificationTemplate.objects.create(
            name="Welcome Email",
            description="Sent to new users",
            subject="Welcome to SD LMS",
            body="Welcome {{user_name}}!",
            channel="email",
        )

    def test_list_templates(self):
        """Test listing templates."""
        url = reverse("notifications_api:template-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)

    def test_create_template(self):
        """Test creating a template."""
        url = reverse("notifications_api:template-list")
        data = {
            "name": "New Template",
            "description": "A new template",
            "subject": "Subject",
            "body": "Body content",
            "channel": "push",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(NotificationTemplate.objects.count(), 2)
