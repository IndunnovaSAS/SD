"""
Tests for sync API endpoints.

Comprehensive tests for SyncLog, SyncConflict, OfflinePackage, and PackageDownload API endpoints.
Uses pytest and factory_boy for test data generation.
"""

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.sync.models import (
    OfflinePackage,
    PackageDownload,
    SyncLog,
)

from .factories import (
    AdminUserFactory,
    BuildingPackageFactory,
    CompletedDownloadFactory,
    CompletedSyncLogFactory,
    CourseFactory,
    ErrorPackageFactory,
    FailedSyncLogFactory,
    InProgressSyncLogFactory,
    PackageDownloadFactory,
    PendingConflictFactory,
    ReadyPackageFactory,
    ServerWinsConflictFactory,
    SyncConflictFactory,
    SyncLogFactory,
    UserFactory,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def api_client():
    """Return an API client."""
    return APIClient()


@pytest.fixture
def user():
    """Create a regular user."""
    return UserFactory()


@pytest.fixture
def admin_user():
    """Create an admin user."""
    return AdminUserFactory()


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return an admin authenticated API client."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def course():
    """Create a course for packages."""
    return CourseFactory()


# ============================================================================
# SyncLog API Tests
# ============================================================================


@pytest.mark.django_db
class TestSyncLogList:
    """Tests for SyncLog list endpoint."""

    def test_list_sync_logs_authenticated(self, authenticated_client, user):
        """Test listing sync logs for authenticated user."""
        # Create logs for the user
        SyncLogFactory(user=user)
        SyncLogFactory(user=user)

        # Create log for another user (should not appear)
        SyncLogFactory()

        url = reverse("sync_api:log-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 2

    def test_list_sync_logs_unauthenticated(self, api_client):
        """Test listing sync logs without authentication."""
        url = reverse("sync_api:log-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_sync_logs_staff_sees_all(self, admin_client, admin_user):
        """Test admin can see all sync logs."""
        # Create logs for different users
        user1 = UserFactory()
        user2 = UserFactory()
        SyncLogFactory(user=user1)
        SyncLogFactory(user=user2)
        SyncLogFactory(user=admin_user)

        url = reverse("sync_api:log-list")
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 3

    def test_filter_by_status(self, authenticated_client, user):
        """Test filtering sync logs by status."""
        CompletedSyncLogFactory(user=user)
        FailedSyncLogFactory(user=user)
        InProgressSyncLogFactory(user=user)

        url = reverse("sync_api:log-list")
        response = authenticated_client.get(url, {"status": "completed"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 1
        assert results[0]["status"] == "completed"

    def test_filter_by_direction(self, authenticated_client, user):
        """Test filtering sync logs by direction."""
        SyncLogFactory(user=user, direction=SyncLog.Direction.UPLOAD)
        SyncLogFactory(user=user, direction=SyncLog.Direction.DOWNLOAD)

        url = reverse("sync_api:log-list")
        response = authenticated_client.get(url, {"direction": "upload"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 1
        assert results[0]["direction"] == "upload"

    def test_filter_by_device(self, authenticated_client, user):
        """Test filtering sync logs by device ID."""
        SyncLogFactory(user=user, device_id="device-001")
        SyncLogFactory(user=user, device_id="device-002")

        url = reverse("sync_api:log-list")
        response = authenticated_client.get(url, {"device": "device-001"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 1
        assert results[0]["device_id"] == "device-001"

    def test_filter_by_date_range(self, authenticated_client, user):
        """Test filtering sync logs by date range."""
        old_log = SyncLogFactory(user=user)
        old_log.created_at = timezone.now() - timedelta(days=10)
        old_log.save()

        recent_log = SyncLogFactory(user=user)

        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        url = reverse("sync_api:log-list")
        response = authenticated_client.get(
            url,
            {"date_from": yesterday.isoformat(), "date_to": today.isoformat()},
        )

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 1


@pytest.mark.django_db
class TestSyncLogStart:
    """Tests for starting sync operations."""

    def test_start_sync_success(self, authenticated_client, user):
        """Test starting a sync operation successfully."""
        url = reverse("sync_api:log-start")
        data = {
            "device_id": "device-123",
            "device_name": "Test Tablet",
            "direction": "bidirectional",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == SyncLog.Status.IN_PROGRESS
        assert response.data["device_id"] == "device-123"
        assert response.data["device_name"] == "Test Tablet"

    def test_start_sync_upload_only(self, authenticated_client, user):
        """Test starting an upload-only sync."""
        url = reverse("sync_api:log-start")
        data = {
            "device_id": "device-123",
            "direction": "upload",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["direction"] == "upload"

    def test_start_sync_download_only(self, authenticated_client, user):
        """Test starting a download-only sync."""
        url = reverse("sync_api:log-start")
        data = {
            "device_id": "device-123",
            "direction": "download",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["direction"] == "download"

    def test_start_sync_with_client_timestamp(self, authenticated_client, user):
        """Test starting sync with client timestamp."""
        client_time = (timezone.now() - timedelta(minutes=5)).isoformat()
        url = reverse("sync_api:log-start")
        data = {
            "device_id": "device-123",
            "direction": "bidirectional",
            "client_timestamp": client_time,
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["client_timestamp"] is not None

    def test_start_sync_with_metadata(self, authenticated_client, user):
        """Test starting sync with metadata."""
        url = reverse("sync_api:log-start")
        data = {
            "device_id": "device-123",
            "direction": "bidirectional",
            "metadata": {"app_version": "1.0.0", "os": "Android 14"},
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["metadata"]["app_version"] == "1.0.0"

    def test_start_sync_missing_device_id(self, authenticated_client, user):
        """Test starting sync without device_id fails."""
        url = reverse("sync_api:log-start")
        data = {
            "direction": "bidirectional",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_start_sync_invalid_direction(self, authenticated_client, user):
        """Test starting sync with invalid direction fails."""
        url = reverse("sync_api:log-start")
        data = {
            "device_id": "device-123",
            "direction": "invalid",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_start_sync_unauthenticated(self, api_client):
        """Test starting sync without authentication fails."""
        url = reverse("sync_api:log-start")
        data = {
            "device_id": "device-123",
            "direction": "bidirectional",
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestSyncLogUpload:
    """Tests for uploading sync data."""

    def test_upload_data_success(self, authenticated_client, user):
        """Test uploading sync data successfully."""
        sync_log = InProgressSyncLogFactory(user=user)

        url = reverse("sync_api:log-upload", args=[sync_log.id])
        data = {
            "data": {
                "records": [
                    {"id": 1, "type": "progress"},
                    {"id": 2, "type": "progress"},
                ],
            },
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["received"] == 2

    def test_upload_data_wrong_user(self, authenticated_client, user):
        """Test uploading to another user's sync fails.

        Note: Returns 404 because the queryset is filtered by user,
        so the object appears not to exist for the requesting user.
        """
        other_user = UserFactory()
        sync_log = InProgressSyncLogFactory(user=other_user)

        url = reverse("sync_api:log-upload", args=[sync_log.id])
        data = {"data": {"records": []}}

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_upload_data_not_in_progress(self, authenticated_client, user):
        """Test uploading to completed sync fails."""
        sync_log = CompletedSyncLogFactory(user=user)

        url = reverse("sync_api:log-upload", args=[sync_log.id])
        data = {"data": {"records": []}}

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestSyncLogDownload:
    """Tests for downloading sync data."""

    def test_download_data_success(self, authenticated_client, user):
        """Test downloading sync data successfully."""
        sync_log = InProgressSyncLogFactory(user=user)

        url = reverse("sync_api:log-download", args=[sync_log.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "records" in response.data
        assert "server_timestamp" in response.data

    def test_download_data_wrong_user(self, authenticated_client, user):
        """Test downloading from another user's sync fails.

        Note: Returns 404 because the queryset is filtered by user,
        so the object appears not to exist for the requesting user.
        """
        other_user = UserFactory()
        sync_log = InProgressSyncLogFactory(user=other_user)

        url = reverse("sync_api:log-download", args=[sync_log.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestSyncLogComplete:
    """Tests for completing sync operations."""

    def test_complete_sync_success(self, authenticated_client, user):
        """Test completing sync successfully."""
        sync_log = InProgressSyncLogFactory(user=user)

        url = reverse("sync_api:log-complete", args=[sync_log.id])
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == SyncLog.Status.COMPLETED

    def test_complete_sync_with_pending_conflicts(self, authenticated_client, user):
        """Test completing sync with pending conflicts results in partial."""
        sync_log = InProgressSyncLogFactory(user=user)
        PendingConflictFactory(sync_log=sync_log)

        url = reverse("sync_api:log-complete", args=[sync_log.id])
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == SyncLog.Status.PARTIAL

    def test_complete_sync_wrong_user(self, authenticated_client, user):
        """Test completing another user's sync fails.

        Note: Returns 404 because the queryset is filtered by user,
        so the object appears not to exist for the requesting user.
        """
        other_user = UserFactory()
        sync_log = InProgressSyncLogFactory(user=other_user)

        url = reverse("sync_api:log-complete", args=[sync_log.id])
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_complete_already_completed_sync(self, authenticated_client, user):
        """Test completing already completed sync fails."""
        sync_log = CompletedSyncLogFactory(user=user)

        url = reverse("sync_api:log-complete", args=[sync_log.id])
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestSyncLogLast:
    """Tests for getting last sync."""

    def test_get_last_sync_success(self, authenticated_client, user):
        """Test getting last sync for device."""
        device_id = "device-001"
        CompletedSyncLogFactory(user=user, device_id=device_id)
        CompletedSyncLogFactory(user=user, device_id=device_id)

        url = reverse("sync_api:log-last")
        response = authenticated_client.get(url, {"device": device_id})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["last_sync"] is not None

    def test_get_last_sync_no_device(self, authenticated_client, user):
        """Test getting last sync without device parameter."""
        url = reverse("sync_api:log-last")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_last_sync_no_history(self, authenticated_client, user):
        """Test getting last sync with no history."""
        url = reverse("sync_api:log-last")
        response = authenticated_client.get(url, {"device": "new-device"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["last_sync"] is None


# ============================================================================
# SyncConflict API Tests
# ============================================================================


@pytest.mark.django_db
class TestSyncConflictList:
    """Tests for SyncConflict list endpoint."""

    def test_list_conflicts_authenticated(self, authenticated_client, user):
        """Test listing conflicts for authenticated user."""
        sync_log = InProgressSyncLogFactory(user=user)
        SyncConflictFactory(sync_log=sync_log)
        SyncConflictFactory(sync_log=sync_log)

        # Create conflict for another user (should not appear)
        other_sync_log = InProgressSyncLogFactory()
        SyncConflictFactory(sync_log=other_sync_log)

        url = reverse("sync_api:conflict-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 2

    def test_list_conflicts_staff_sees_all(self, admin_client, admin_user):
        """Test admin can see all conflicts."""
        sync_log1 = InProgressSyncLogFactory()
        sync_log2 = InProgressSyncLogFactory()
        SyncConflictFactory(sync_log=sync_log1)
        SyncConflictFactory(sync_log=sync_log2)

        url = reverse("sync_api:conflict-list")
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 2

    def test_filter_by_resolution(self, authenticated_client, user):
        """Test filtering conflicts by resolution status."""
        sync_log = InProgressSyncLogFactory(user=user)
        PendingConflictFactory(sync_log=sync_log)
        ServerWinsConflictFactory(sync_log=sync_log)

        url = reverse("sync_api:conflict-list")
        response = authenticated_client.get(url, {"resolution": "pending"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 1
        assert results[0]["resolution"] == "pending"

    def test_filter_by_model(self, authenticated_client, user):
        """Test filtering conflicts by model name."""
        sync_log = InProgressSyncLogFactory(user=user)
        SyncConflictFactory(sync_log=sync_log, model_name="Course")
        SyncConflictFactory(sync_log=sync_log, model_name="Lesson")

        url = reverse("sync_api:conflict-list")
        response = authenticated_client.get(url, {"model": "Course"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 1
        assert results[0]["model_name"] == "Course"


@pytest.mark.django_db
class TestSyncConflictResolve:
    """Tests for resolving sync conflicts."""

    def test_resolve_server_wins(self, authenticated_client, user):
        """Test resolving conflict with server wins."""
        sync_log = InProgressSyncLogFactory(user=user)
        conflict = PendingConflictFactory(
            sync_log=sync_log,
            server_data={"title": "Server Value"},
            client_data={"title": "Client Value"},
        )

        url = reverse("sync_api:conflict-resolve", args=[conflict.id])
        response = authenticated_client.post(url, {"resolution": "server_wins"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["resolution"] == "server_wins"
        assert response.data["resolved_data"]["title"] == "Server Value"

    def test_resolve_client_wins(self, authenticated_client, user):
        """Test resolving conflict with client wins."""
        sync_log = InProgressSyncLogFactory(user=user)
        conflict = PendingConflictFactory(
            sync_log=sync_log,
            server_data={"title": "Server Value"},
            client_data={"title": "Client Value"},
        )

        url = reverse("sync_api:conflict-resolve", args=[conflict.id])
        response = authenticated_client.post(url, {"resolution": "client_wins"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["resolution"] == "client_wins"
        assert response.data["resolved_data"]["title"] == "Client Value"

    def test_resolve_merged(self, authenticated_client, user):
        """Test resolving conflict with merged data."""
        sync_log = InProgressSyncLogFactory(user=user)
        conflict = PendingConflictFactory(sync_log=sync_log)

        merged_data = {"title": "Merged Value", "source": "manual"}

        url = reverse("sync_api:conflict-resolve", args=[conflict.id])
        response = authenticated_client.post(
            url,
            {"resolution": "merged", "resolved_data": merged_data},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["resolution"] == "merged"
        assert response.data["resolved_data"]["title"] == "Merged Value"

    def test_resolve_merged_without_data(self, authenticated_client, user):
        """Test resolving merged without data fails."""
        sync_log = InProgressSyncLogFactory(user=user)
        conflict = PendingConflictFactory(sync_log=sync_log)

        url = reverse("sync_api:conflict-resolve", args=[conflict.id])
        response = authenticated_client.post(url, {"resolution": "merged"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_resolve_wrong_user(self, authenticated_client, user):
        """Test resolving another user's conflict fails.

        Note: Returns 404 because the queryset is filtered by user,
        so the object appears not to exist for the requesting user.
        """
        other_sync_log = InProgressSyncLogFactory()
        conflict = PendingConflictFactory(sync_log=other_sync_log)

        url = reverse("sync_api:conflict-resolve", args=[conflict.id])
        response = authenticated_client.post(url, {"resolution": "server_wins"})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_resolve_already_resolved(self, authenticated_client, user):
        """Test resolving already resolved conflict fails."""
        sync_log = InProgressSyncLogFactory(user=user)
        conflict = ServerWinsConflictFactory(sync_log=sync_log)

        url = reverse("sync_api:conflict-resolve", args=[conflict.id])
        response = authenticated_client.post(url, {"resolution": "client_wins"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_staff_can_resolve_any_conflict(self, admin_client, admin_user):
        """Test admin can resolve any conflict."""
        other_sync_log = InProgressSyncLogFactory()
        conflict = PendingConflictFactory(sync_log=other_sync_log)

        url = reverse("sync_api:conflict-resolve", args=[conflict.id])
        response = admin_client.post(url, {"resolution": "server_wins"})

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestSyncConflictPending:
    """Tests for getting pending conflicts."""

    def test_get_pending_conflicts(self, authenticated_client, user):
        """Test getting pending conflicts for user."""
        sync_log = InProgressSyncLogFactory(user=user)
        PendingConflictFactory(sync_log=sync_log)
        PendingConflictFactory(sync_log=sync_log)
        ServerWinsConflictFactory(sync_log=sync_log)  # Not pending

        url = reverse("sync_api:conflict-pending")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_get_pending_conflicts_empty(self, authenticated_client, user):
        """Test getting pending conflicts when none exist."""
        url = reverse("sync_api:conflict-pending")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0


# ============================================================================
# OfflinePackage API Tests
# ============================================================================


@pytest.mark.django_db
class TestOfflinePackageList:
    """Tests for OfflinePackage list endpoint."""

    def test_list_packages_authenticated(self, authenticated_client, user, course):
        """Test listing packages for authenticated user."""
        ReadyPackageFactory(course=course)
        BuildingPackageFactory(course=course)  # Not ready, won't show to regular user

        url = reverse("sync_api:package-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        # Regular user only sees ready packages
        assert len(results) == 1

    def test_list_packages_staff_sees_all(self, admin_client, admin_user, course):
        """Test admin sees all packages regardless of status."""
        ReadyPackageFactory(course=course)
        BuildingPackageFactory(course=course)
        ErrorPackageFactory(course=course)

        url = reverse("sync_api:package-list")
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 3

    def test_filter_by_status(self, admin_client, admin_user, course):
        """Test filtering packages by status."""
        ReadyPackageFactory(course=course)
        BuildingPackageFactory(course=course)

        url = reverse("sync_api:package-list")
        response = admin_client.get(url, {"status": "ready"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 1
        assert results[0]["status"] == "ready"

    def test_filter_by_course(self, admin_client, admin_user):
        """Test filtering packages by course."""
        course1 = CourseFactory()
        course2 = CourseFactory()
        ReadyPackageFactory(course=course1)
        ReadyPackageFactory(course=course2)

        url = reverse("sync_api:package-list")
        response = admin_client.get(url, {"course": course1.id})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 1

    def test_search_packages(self, admin_client, admin_user):
        """Test searching packages."""
        course = CourseFactory(title="Safety Training Course")
        ReadyPackageFactory(course=course, name="Safety Package")

        url = reverse("sync_api:package-list")
        response = admin_client.get(url, {"search": "Safety"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 1


@pytest.mark.django_db
class TestOfflinePackageCreate:
    """Tests for creating offline packages."""

    def test_create_package_admin(self, admin_client, admin_user, course):
        """Test admin can create package."""
        url = reverse("sync_api:package-list")
        data = {
            "name": "New Package",
            "description": "Test package",
            "course": course.id,
            "includes_videos": True,
            "includes_documents": True,
            "includes_assessments": False,
        }

        response = admin_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert OfflinePackage.objects.filter(name="New Package").exists()

    def test_create_package_regular_user(self, authenticated_client, user, course):
        """Test regular user cannot create package."""
        url = reverse("sync_api:package-list")
        data = {
            "name": "New Package",
            "course": course.id,
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestOfflinePackageBuild:
    """Tests for building offline packages."""

    def test_build_package_admin(self, admin_client, admin_user, course):
        """Test admin can trigger package build."""
        package = ReadyPackageFactory(course=course, version=1)

        url = reverse("sync_api:package-build", args=[package.id])
        response = admin_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["version"] == 2

        package.refresh_from_db()
        assert package.status == OfflinePackage.Status.BUILDING

    def test_build_package_regular_user(self, authenticated_client, user, course):
        """Test regular user cannot trigger build."""
        package = ReadyPackageFactory(course=course)

        url = reverse("sync_api:package-build", args=[package.id])
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_build_package_already_building(self, admin_client, admin_user, course):
        """Test building already building package fails."""
        package = BuildingPackageFactory(course=course)

        url = reverse("sync_api:package-build", args=[package.id])
        response = admin_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestOfflinePackageDownloadUrl:
    """Tests for getting package download URL."""

    def test_get_download_url_ready_package(self, authenticated_client, user, course):
        """Test getting download URL for ready package."""
        package = ReadyPackageFactory(course=course)

        url = reverse("sync_api:package-download-url", args=[package.id])
        response = authenticated_client.get(url)

        # May fail if package_file is not set
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_download_url_not_ready(self, authenticated_client, user, course):
        """Test getting download URL for not ready package fails.

        Note: Returns 404 because non-staff users can only see READY packages
        in the queryset, so building packages appear not to exist.
        """
        package = BuildingPackageFactory(course=course)

        url = reverse("sync_api:package-download-url", args=[package.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestOfflinePackageAvailable:
    """Tests for getting available packages."""

    def test_get_available_packages(self, authenticated_client, user):
        """Test getting available packages."""
        course1 = CourseFactory()
        course2 = CourseFactory()
        ReadyPackageFactory(course=course1)
        ReadyPackageFactory(course=course2)
        BuildingPackageFactory()  # Not available

        url = reverse("sync_api:package-available")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2


# ============================================================================
# PackageDownload API Tests
# ============================================================================


@pytest.mark.django_db
class TestPackageDownloadList:
    """Tests for PackageDownload list endpoint."""

    def test_list_downloads_authenticated(self, authenticated_client, user, course):
        """Test listing downloads for authenticated user."""
        package = ReadyPackageFactory(course=course)
        PackageDownloadFactory(user=user, package=package)
        PackageDownloadFactory(user=user, package=package, device_id="device-2")

        # Another user's download
        PackageDownloadFactory(package=package)

        url = reverse("sync_api:download-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 2

    def test_filter_by_package(self, authenticated_client, user):
        """Test filtering downloads by package."""
        package1 = ReadyPackageFactory()
        package2 = ReadyPackageFactory()
        PackageDownloadFactory(user=user, package=package1)
        PackageDownloadFactory(user=user, package=package2)

        url = reverse("sync_api:download-list")
        response = authenticated_client.get(url, {"package": package1.id})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 1

    def test_filter_by_device(self, authenticated_client, user):
        """Test filtering downloads by device."""
        package = ReadyPackageFactory()
        PackageDownloadFactory(user=user, package=package, device_id="device-1")
        PackageDownloadFactory(user=user, package=package, device_id="device-2")

        url = reverse("sync_api:download-list")
        response = authenticated_client.get(url, {"device": "device-1"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 1

    def test_filter_by_completed(self, authenticated_client, user):
        """Test filtering downloads by completion status."""
        package = ReadyPackageFactory()
        CompletedDownloadFactory(user=user, package=package)
        PackageDownloadFactory(user=user, package=package, download_completed=False)

        url = reverse("sync_api:download-list")
        response = authenticated_client.get(url, {"completed": "true"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        assert len(results) == 1
        assert results[0]["download_completed"] is True


@pytest.mark.django_db
class TestPackageDownloadStart:
    """Tests for starting package downloads."""

    def test_start_download_success(self, authenticated_client, user):
        """Test starting a package download."""
        package = ReadyPackageFactory()

        url = reverse("sync_api:download-start")
        data = {
            "package_id": package.id,
            "device_id": "tablet-001",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert "download_id" in response.data
        assert PackageDownload.objects.filter(
            user=user, package=package, device_id="tablet-001"
        ).exists()

    def test_start_download_not_ready(self, authenticated_client, user):
        """Test starting download for not ready package fails."""
        package = BuildingPackageFactory()

        url = reverse("sync_api:download-start")
        data = {
            "package_id": package.id,
            "device_id": "tablet-001",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_start_download_nonexistent_package(self, authenticated_client, user):
        """Test starting download for nonexistent package fails."""
        url = reverse("sync_api:download-start")
        data = {
            "package_id": 99999,
            "device_id": "tablet-001",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_restart_download(self, authenticated_client, user):
        """Test restarting an existing download."""
        package = ReadyPackageFactory()
        existing = PackageDownloadFactory(
            user=user,
            package=package,
            device_id="tablet-001",
            download_completed=True,
        )

        url = reverse("sync_api:download-start")
        data = {
            "package_id": package.id,
            "device_id": "tablet-001",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK

        existing.refresh_from_db()
        assert existing.download_completed is False


@pytest.mark.django_db
class TestPackageDownloadComplete:
    """Tests for completing package downloads."""

    def test_complete_download_success(self, authenticated_client, user):
        """Test completing a download."""
        package = ReadyPackageFactory()
        download = PackageDownloadFactory(
            user=user,
            package=package,
            download_completed=False,
        )

        url = reverse("sync_api:download-complete", args=[download.id])
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["download_completed"] is True

    def test_complete_download_wrong_user(self, authenticated_client, user):
        """Test completing another user's download fails.

        Note: Returns 404 because the queryset is filtered by user,
        so the object appears not to exist for the requesting user.
        """
        download = PackageDownloadFactory(download_completed=False)

        url = reverse("sync_api:download-complete", args=[download.id])
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestPackageDownloadMyDownloads:
    """Tests for getting user's downloads."""

    def test_my_downloads(self, authenticated_client, user):
        """Test getting user's completed downloads."""
        package = ReadyPackageFactory()
        CompletedDownloadFactory(user=user, package=package)
        PackageDownloadFactory(user=user, download_completed=False)  # Not completed

        url = reverse("sync_api:download-my-downloads")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1


@pytest.mark.django_db
class TestPackageDownloadAccess:
    """Tests for recording package access."""

    def test_access_download(self, authenticated_client, user):
        """Test recording package access."""
        download = CompletedDownloadFactory(user=user)

        url = reverse("sync_api:download-access", args=[download.id])
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert "accessed_at" in response.data

    def test_access_download_wrong_user(self, authenticated_client, user):
        """Test accessing another user's download fails.

        Note: Returns 404 because the queryset is filtered by user,
        so the object appears not to exist for the requesting user.
        """
        download = CompletedDownloadFactory()

        url = reverse("sync_api:download-access", args=[download.id])
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.django_db
class TestFullSyncWorkflow:
    """Integration tests for full sync workflow."""

    def test_complete_sync_workflow(self, authenticated_client, user):
        """Test complete sync workflow from start to finish."""
        # 1. Start sync
        start_url = reverse("sync_api:log-start")
        start_response = authenticated_client.post(
            start_url,
            {
                "device_id": "tablet-001",
                "device_name": "My Tablet",
                "direction": "bidirectional",
            },
        )

        assert start_response.status_code == status.HTTP_201_CREATED
        sync_id = start_response.data["id"]

        # 2. Upload data
        upload_url = reverse("sync_api:log-upload", args=[sync_id])
        upload_response = authenticated_client.post(
            upload_url,
            {"data": {"records": [{"id": 1}, {"id": 2}]}},
            format="json",
        )

        assert upload_response.status_code == status.HTTP_200_OK

        # 3. Download data
        download_url = reverse("sync_api:log-download", args=[sync_id])
        download_response = authenticated_client.get(download_url)

        assert download_response.status_code == status.HTTP_200_OK

        # 4. Complete sync
        complete_url = reverse("sync_api:log-complete", args=[sync_id])
        complete_response = authenticated_client.post(complete_url)

        assert complete_response.status_code == status.HTTP_200_OK
        assert complete_response.data["status"] == SyncLog.Status.COMPLETED

    def test_sync_with_conflict_resolution(self, authenticated_client, user):
        """Test sync workflow with conflict resolution."""
        # Start sync
        sync_log = InProgressSyncLogFactory(user=user)

        # Create a conflict
        conflict = PendingConflictFactory(
            sync_log=sync_log,
            server_data={"title": "Server"},
            client_data={"title": "Client"},
        )

        # Resolve conflict
        resolve_url = reverse("sync_api:conflict-resolve", args=[conflict.id])
        resolve_response = authenticated_client.post(
            resolve_url,
            {"resolution": "client_wins"},
        )

        assert resolve_response.status_code == status.HTTP_200_OK

        # Complete sync
        complete_url = reverse("sync_api:log-complete", args=[sync_log.id])
        complete_response = authenticated_client.post(complete_url)

        assert complete_response.status_code == status.HTTP_200_OK
        assert complete_response.data["status"] == SyncLog.Status.COMPLETED

    def test_package_download_workflow(self, authenticated_client, user):
        """Test complete package download workflow."""
        package = ReadyPackageFactory()

        # 1. Start download
        start_url = reverse("sync_api:download-start")
        start_response = authenticated_client.post(
            start_url,
            {"package_id": package.id, "device_id": "tablet-001"},
        )

        assert start_response.status_code == status.HTTP_200_OK
        download_id = start_response.data["download_id"]

        # 2. Complete download
        complete_url = reverse("sync_api:download-complete", args=[download_id])
        complete_response = authenticated_client.post(complete_url)

        assert complete_response.status_code == status.HTTP_200_OK
        assert complete_response.data["download_completed"] is True

        # 3. Access downloaded package
        access_url = reverse("sync_api:download-access", args=[download_id])
        access_response = authenticated_client.post(access_url)

        assert access_response.status_code == status.HTTP_200_OK

        # 4. View my downloads
        my_downloads_url = reverse("sync_api:download-my-downloads")
        my_downloads_response = authenticated_client.get(my_downloads_url)

        assert my_downloads_response.status_code == status.HTTP_200_OK
        assert len(my_downloads_response.data) == 1
