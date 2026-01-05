"""
Tests for sync API endpoints.
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.courses.models import Course
from apps.sync.models import OfflinePackage, PackageDownload, SyncConflict, SyncLog


class SyncLogAPITests(TestCase):
    """Tests for SyncLog API endpoints."""

    def setUp(self):
        SyncLog.objects.all().delete()

        self.client = APIClient()
        self.user = User.objects.create_user(
            email="syncuser@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            document_number="12345678",
            job_position="Developer",
            job_profile="LINIERO",
            hire_date=date(2024, 1, 1),
        )
        self.client.force_authenticate(user=self.user)

        self.sync_log = SyncLog.objects.create(
            user=self.user,
            device_id="device-123",
            device_name="Mi Tablet",
            direction=SyncLog.Direction.BIDIRECTIONAL,
            status=SyncLog.Status.COMPLETED,
            started_at=timezone.now(),
            completed_at=timezone.now(),
            records_uploaded=10,
            records_downloaded=5,
        )

    def test_list_sync_logs(self):
        """Test listing sync logs."""
        url = reverse("sync_api:log-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)

    def test_start_sync(self):
        """Test starting a sync operation."""
        url = reverse("sync_api:log-start")
        data = {
            "device_id": "device-456",
            "device_name": "Mi Teléfono",
            "direction": "upload",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SyncLog.objects.count(), 2)
        self.assertEqual(response.data["status"], SyncLog.Status.IN_PROGRESS)

    def test_complete_sync(self):
        """Test completing a sync operation."""
        # Create in-progress sync
        sync = SyncLog.objects.create(
            user=self.user,
            device_id="device-789",
            status=SyncLog.Status.IN_PROGRESS,
            started_at=timezone.now(),
        )

        url = reverse("sync_api:log-complete", args=[sync.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sync.refresh_from_db()
        self.assertEqual(sync.status, SyncLog.Status.COMPLETED)

    def test_get_last_sync(self):
        """Test getting last sync for device."""
        url = reverse("sync_api:log-last")
        response = self.client.get(url, {"device": "device-123"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["last_sync"])


class SyncConflictAPITests(TestCase):
    """Tests for SyncConflict API endpoints."""

    def setUp(self):
        SyncConflict.objects.all().delete()

        self.client = APIClient()
        self.user = User.objects.create_user(
            email="conflictuser@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            document_number="22345678",
            job_position="Developer",
            job_profile="LINIERO",
            hire_date=date(2024, 1, 1),
        )
        self.client.force_authenticate(user=self.user)

        self.sync_log = SyncLog.objects.create(
            user=self.user,
            device_id="device-123",
            status=SyncLog.Status.PARTIAL,
        )

        self.conflict = SyncConflict.objects.create(
            sync_log=self.sync_log,
            model_name="Course",
            record_id="1",
            server_data={"title": "Server Title"},
            client_data={"title": "Client Title"},
            resolution=SyncConflict.Resolution.PENDING,
        )

    def test_list_conflicts(self):
        """Test listing sync conflicts."""
        url = reverse("sync_api:conflict-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)

    def test_resolve_conflict_server_wins(self):
        """Test resolving conflict with server wins."""
        url = reverse("sync_api:conflict-resolve", args=[self.conflict.id])
        data = {"resolution": "server_wins"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.conflict.refresh_from_db()
        self.assertEqual(self.conflict.resolution, SyncConflict.Resolution.SERVER_WINS)
        self.assertEqual(self.conflict.resolved_data, {"title": "Server Title"})

    def test_get_pending_conflicts(self):
        """Test getting pending conflicts."""
        url = reverse("sync_api:conflict-pending")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class OfflinePackageAPITests(TestCase):
    """Tests for OfflinePackage API endpoints."""

    def setUp(self):
        OfflinePackage.objects.all().delete()

        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="packageadmin@example.com",
            password="testpass123",
            first_name="Admin",
            last_name="User",
            document_number="32345678",
            job_position="Admin",
            job_profile="LINIERO",
            hire_date=date(2024, 1, 1),
            is_staff=True,
        )
        self.client.force_authenticate(user=self.admin)

        # Create a course for the package
        self.course = Course.objects.create(
            code="SYNC-001",
            title="Curso de Prueba",
            description="Descripción",
            duration=60,
            course_type=Course.Type.MANDATORY,
            created_by=self.admin,
        )

        self.package = OfflinePackage.objects.create(
            name="Paquete de Prueba",
            course=self.course,
            version=1,
            status=OfflinePackage.Status.READY,
            file_size=1024000,
            checksum="abc123",
        )

    def test_list_packages(self):
        """Test listing offline packages."""
        url = reverse("sync_api:package-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)

    def test_get_available_packages(self):
        """Test getting available packages."""
        url = reverse("sync_api:package-available")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_build_package(self):
        """Test triggering package build."""
        url = reverse("sync_api:package-build", args=[self.package.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.package.refresh_from_db()
        self.assertEqual(self.package.status, OfflinePackage.Status.BUILDING)
        self.assertEqual(self.package.version, 2)


class PackageDownloadAPITests(TestCase):
    """Tests for PackageDownload API endpoints."""

    def setUp(self):
        PackageDownload.objects.all().delete()

        self.client = APIClient()
        self.user = User.objects.create_user(
            email="downloaduser@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            document_number="42345678",
            job_position="Developer",
            job_profile="LINIERO",
            hire_date=date(2024, 1, 1),
        )
        self.client.force_authenticate(user=self.user)

        self.course = Course.objects.create(
            code="SYNC-002",
            title="Curso de Prueba",
            description="Descripción",
            duration=60,
            course_type=Course.Type.MANDATORY,
            created_by=self.user,
        )

        self.package = OfflinePackage.objects.create(
            name="Paquete de Prueba",
            course=self.course,
            status=OfflinePackage.Status.READY,
        )

    def test_start_download(self):
        """Test starting a package download."""
        url = reverse("sync_api:download-start")
        data = {
            "package_id": self.package.id,
            "device_id": "device-123",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(PackageDownload.objects.count(), 1)

    def test_complete_download(self):
        """Test completing a download."""
        download = PackageDownload.objects.create(
            package=self.package,
            user=self.user,
            device_id="device-123",
            download_completed=False,
        )

        url = reverse("sync_api:download-complete", args=[download.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        download.refresh_from_db()
        self.assertTrue(download.download_completed)

    def test_my_downloads(self):
        """Test getting user's downloads."""
        PackageDownload.objects.create(
            package=self.package,
            user=self.user,
            device_id="device-123",
            download_completed=True,
        )

        url = reverse("sync_api:download-my-downloads")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
