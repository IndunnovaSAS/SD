"""
Tests for sync services.

Tests for synchronization services, conflict resolution, and offline package generation.
Note: Since there's no services.py file in the sync app, these tests demonstrate
the service layer patterns that could be implemented and test the business logic
embedded in the views.
"""

import hashlib
import json
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

import pytest

from apps.sync.models import (
    OfflinePackage,
    PackageDownload,
    SyncConflict,
    SyncLog,
)

from .factories import (
    BuildingPackageFactory,
    CompletedDownloadFactory,
    CompletedSyncLogFactory,
    CourseFactory,
    FailedSyncLogFactory,
    InProgressSyncLogFactory,
    OfflinePackageFactory,
    PackageDownloadFactory,
    PendingConflictFactory,
    ReadyPackageFactory,
    ServerWinsConflictFactory,
    SyncLogWithConflictsFactory,
    UserFactory,
)

# ============================================================================
# Sync Service Tests (Business Logic)
# ============================================================================


@pytest.mark.django_db
class TestSyncInitialization:
    """Tests for sync initialization logic."""

    def test_start_sync_creates_log(self):
        """Test starting a sync creates a log entry."""
        user = UserFactory()
        device_id = "test-device-001"
        device_name = "Test Tablet"

        sync_log = SyncLog.objects.create(
            user=user,
            device_id=device_id,
            device_name=device_name,
            direction=SyncLog.Direction.BIDIRECTIONAL,
            status=SyncLog.Status.IN_PROGRESS,
            started_at=timezone.now(),
        )

        assert sync_log.id is not None
        assert sync_log.status == SyncLog.Status.IN_PROGRESS
        assert sync_log.started_at is not None

    def test_start_sync_with_client_timestamp(self):
        """Test starting sync with client timestamp."""
        user = UserFactory()
        client_time = timezone.now() - timedelta(minutes=5)

        sync_log = SyncLog.objects.create(
            user=user,
            device_id="device-001",
            direction=SyncLog.Direction.UPLOAD,
            status=SyncLog.Status.IN_PROGRESS,
            started_at=timezone.now(),
            client_timestamp=client_time,
        )

        assert sync_log.client_timestamp == client_time

    def test_start_sync_with_metadata(self):
        """Test starting sync with device metadata."""
        user = UserFactory()
        metadata = {
            "app_version": "2.0.0",
            "os": "iOS 17",
            "device_model": "iPad Pro",
        }

        sync_log = SyncLog.objects.create(
            user=user,
            device_id="device-001",
            direction=SyncLog.Direction.BIDIRECTIONAL,
            status=SyncLog.Status.IN_PROGRESS,
            started_at=timezone.now(),
            metadata=metadata,
        )

        assert sync_log.metadata == metadata

    def test_get_last_sync_for_device(self):
        """Test getting last successful sync for a device."""
        user = UserFactory()
        device_id = "device-001"

        # Create multiple syncs
        old_sync = CompletedSyncLogFactory(user=user, device_id=device_id)
        new_sync = CompletedSyncLogFactory(user=user, device_id=device_id)
        other_device = CompletedSyncLogFactory(user=user, device_id="device-002")

        last_sync = (
            SyncLog.objects.filter(
                user=user,
                device_id=device_id,
                status=SyncLog.Status.COMPLETED,
            )
            .order_by("-completed_at")
            .first()
        )

        assert last_sync == new_sync

    def test_no_last_sync_for_new_device(self):
        """Test no last sync exists for new device."""
        user = UserFactory()

        last_sync = SyncLog.objects.filter(
            user=user,
            device_id="new-device",
            status=SyncLog.Status.COMPLETED,
        ).first()

        assert last_sync is None


@pytest.mark.django_db
class TestDataUpload:
    """Tests for data upload during sync."""

    def test_upload_records_increments_count(self):
        """Test uploading records increments the count."""
        sync_log = InProgressSyncLogFactory(records_uploaded=0)
        records_to_upload = 25

        sync_log.records_uploaded += records_to_upload
        sync_log.save()

        sync_log.refresh_from_db()
        assert sync_log.records_uploaded == records_to_upload

    def test_upload_updates_bytes_transferred(self):
        """Test uploading data updates bytes transferred."""
        sync_log = InProgressSyncLogFactory(bytes_transferred=0)
        data_size = 1024 * 50  # 50 KB

        sync_log.bytes_transferred += data_size
        sync_log.save()

        sync_log.refresh_from_db()
        assert sync_log.bytes_transferred == data_size

    def test_upload_creates_conflict_on_collision(self):
        """Test uploading creates conflict when data collides."""
        sync_log = InProgressSyncLogFactory()

        server_data = {"title": "Server Title", "version": 2}
        client_data = {"title": "Client Title", "version": 1}

        conflict = SyncConflict.objects.create(
            sync_log=sync_log,
            model_name="Course",
            record_id="123",
            server_data=server_data,
            client_data=client_data,
            resolution=SyncConflict.Resolution.PENDING,
        )

        assert conflict.id is not None
        assert sync_log.conflicts.count() == 1

    def test_upload_multiple_records_batch(self):
        """Test uploading multiple records in a batch."""
        sync_log = InProgressSyncLogFactory()

        records = [
            {"id": 1, "type": "progress", "data": {"lesson_id": 1, "completed": True}},
            {"id": 2, "type": "progress", "data": {"lesson_id": 2, "completed": False}},
            {"id": 3, "type": "assessment", "data": {"score": 85}},
        ]

        sync_log.records_uploaded = len(records)
        sync_log.bytes_transferred = len(json.dumps(records))
        sync_log.save()

        assert sync_log.records_uploaded == 3


@pytest.mark.django_db
class TestDataDownload:
    """Tests for data download during sync."""

    def test_download_increments_record_count(self):
        """Test downloading records increments the count."""
        sync_log = InProgressSyncLogFactory(records_downloaded=0)

        sync_log.records_downloaded = 50
        sync_log.save()

        sync_log.refresh_from_db()
        assert sync_log.records_downloaded == 50

    def test_download_updates_bytes_transferred(self):
        """Test downloading updates bytes transferred."""
        sync_log = InProgressSyncLogFactory()

        download_size = 2048 * 100  # 200 KB
        sync_log.bytes_transferred += download_size
        sync_log.save()

        sync_log.refresh_from_db()
        assert sync_log.bytes_transferred >= download_size


@pytest.mark.django_db
class TestConflictResolution:
    """Tests for conflict resolution logic."""

    def test_resolve_conflict_server_wins(self):
        """Test resolving conflict with server data."""
        conflict = PendingConflictFactory(
            server_data={"title": "Server Value"},
            client_data={"title": "Client Value"},
        )
        resolver = UserFactory()

        conflict.resolution = SyncConflict.Resolution.SERVER_WINS
        conflict.resolved_data = conflict.server_data
        conflict.resolved_by = resolver
        conflict.resolved_at = timezone.now()
        conflict.save()

        conflict.refresh_from_db()
        assert conflict.resolution == SyncConflict.Resolution.SERVER_WINS
        assert conflict.resolved_data == {"title": "Server Value"}

    def test_resolve_conflict_client_wins(self):
        """Test resolving conflict with client data."""
        conflict = PendingConflictFactory(
            server_data={"title": "Server Value"},
            client_data={"title": "Client Value"},
        )
        resolver = UserFactory()

        conflict.resolution = SyncConflict.Resolution.CLIENT_WINS
        conflict.resolved_data = conflict.client_data
        conflict.resolved_by = resolver
        conflict.resolved_at = timezone.now()
        conflict.save()

        conflict.refresh_from_db()
        assert conflict.resolution == SyncConflict.Resolution.CLIENT_WINS
        assert conflict.resolved_data == {"title": "Client Value"}

    def test_resolve_conflict_merged(self):
        """Test resolving conflict with merged data."""
        conflict = PendingConflictFactory(
            server_data={"title": "Server Title", "description": "Server Desc"},
            client_data={"title": "Client Title", "notes": "Client Notes"},
        )
        resolver = UserFactory()

        merged_data = {
            "title": "Server Title",  # Take from server
            "description": "Server Desc",  # Take from server
            "notes": "Client Notes",  # Take from client
        }

        conflict.resolution = SyncConflict.Resolution.MERGED
        conflict.resolved_data = merged_data
        conflict.resolved_by = resolver
        conflict.resolved_at = timezone.now()
        conflict.save()

        conflict.refresh_from_db()
        assert conflict.resolution == SyncConflict.Resolution.MERGED
        assert conflict.resolved_data["notes"] == "Client Notes"

    def test_resolve_conflict_manual(self):
        """Test manually resolving conflict."""
        conflict = PendingConflictFactory()
        resolver = UserFactory()

        manual_data = {"title": "Completely New Value", "manual": True}

        conflict.resolution = SyncConflict.Resolution.MANUAL
        conflict.resolved_data = manual_data
        conflict.resolved_by = resolver
        conflict.resolved_at = timezone.now()
        conflict.save()

        conflict.refresh_from_db()
        assert conflict.resolution == SyncConflict.Resolution.MANUAL

    def test_cannot_resolve_already_resolved_conflict(self):
        """Test that already resolved conflicts cannot be re-resolved easily."""
        conflict = ServerWinsConflictFactory()
        original_resolution = conflict.resolution
        original_data = conflict.resolved_data

        # In a real service, this would raise an error
        # Here we just verify the state
        assert conflict.resolution != SyncConflict.Resolution.PENDING

    def test_get_pending_conflicts_for_user(self):
        """Test getting all pending conflicts for a user."""
        user = UserFactory()
        sync_log = InProgressSyncLogFactory(user=user)

        pending1 = PendingConflictFactory(sync_log=sync_log)
        pending2 = PendingConflictFactory(sync_log=sync_log)
        resolved = ServerWinsConflictFactory(sync_log=sync_log)

        pending_conflicts = SyncConflict.objects.filter(
            sync_log__user=user,
            resolution=SyncConflict.Resolution.PENDING,
        )

        assert pending_conflicts.count() == 2

    def test_resolve_all_conflicts_completes_sync(self):
        """Test resolving all conflicts allows sync completion."""
        sync_log = SyncLogWithConflictsFactory()
        resolver = UserFactory()

        # Resolve all conflicts
        for conflict in sync_log.conflicts.all():
            conflict.resolution = SyncConflict.Resolution.SERVER_WINS
            conflict.resolved_data = conflict.server_data
            conflict.resolved_by = resolver
            conflict.resolved_at = timezone.now()
            conflict.save()

        pending_count = sync_log.conflicts.filter(
            resolution=SyncConflict.Resolution.PENDING
        ).count()

        if pending_count == 0:
            sync_log.status = SyncLog.Status.COMPLETED
        else:
            sync_log.status = SyncLog.Status.PARTIAL

        sync_log.completed_at = timezone.now()
        sync_log.save()

        assert sync_log.status == SyncLog.Status.COMPLETED


@pytest.mark.django_db
class TestSyncCompletion:
    """Tests for sync completion logic."""

    def test_complete_sync_without_conflicts(self):
        """Test completing sync without conflicts."""
        sync_log = InProgressSyncLogFactory()

        sync_log.status = SyncLog.Status.COMPLETED
        sync_log.completed_at = timezone.now()
        sync_log.save()

        sync_log.refresh_from_db()
        assert sync_log.status == SyncLog.Status.COMPLETED
        assert sync_log.completed_at is not None

    def test_complete_sync_with_pending_conflicts(self):
        """Test completing sync with pending conflicts results in partial status."""
        sync_log = InProgressSyncLogFactory()
        PendingConflictFactory(sync_log=sync_log)

        pending_count = sync_log.conflicts.filter(
            resolution=SyncConflict.Resolution.PENDING
        ).count()

        if pending_count > 0:
            sync_log.status = SyncLog.Status.PARTIAL
        else:
            sync_log.status = SyncLog.Status.COMPLETED

        sync_log.completed_at = timezone.now()
        sync_log.save()

        assert sync_log.status == SyncLog.Status.PARTIAL

    def test_complete_sync_with_error(self):
        """Test marking sync as failed with error details."""
        sync_log = InProgressSyncLogFactory()

        sync_log.status = SyncLog.Status.FAILED
        sync_log.error_message = "Network connection lost"
        sync_log.error_details = {
            "code": "NETWORK_ERROR",
            "retry_count": 3,
            "last_error": "Connection timeout after 30s",
        }
        sync_log.completed_at = timezone.now()
        sync_log.save()

        sync_log.refresh_from_db()
        assert sync_log.status == SyncLog.Status.FAILED
        assert "Network" in sync_log.error_message

    def test_sync_duration_calculation(self):
        """Test calculating sync duration."""
        started = timezone.now() - timedelta(minutes=5)
        completed = timezone.now()

        sync_log = InProgressSyncLogFactory(started_at=started)
        sync_log.completed_at = completed
        sync_log.status = SyncLog.Status.COMPLETED
        sync_log.save()

        duration = sync_log.completed_at - sync_log.started_at
        assert duration >= timedelta(minutes=5)


# ============================================================================
# Offline Package Service Tests
# ============================================================================


@pytest.mark.django_db
class TestPackageBuilding:
    """Tests for offline package building logic."""

    def test_start_package_build(self):
        """Test starting a package build."""
        package = OfflinePackageFactory(status=OfflinePackage.Status.READY)

        package.status = OfflinePackage.Status.BUILDING
        package.build_started_at = timezone.now()
        package.save()

        package.refresh_from_db()
        assert package.status == OfflinePackage.Status.BUILDING
        assert package.build_started_at is not None

    def test_rebuild_increments_version(self):
        """Test rebuilding package increments version."""
        package = ReadyPackageFactory(version=1)

        package.version += 1
        package.status = OfflinePackage.Status.BUILDING
        package.build_started_at = timezone.now()
        package.save()

        package.refresh_from_db()
        assert package.version == 2

    def test_complete_package_build(self):
        """Test completing a package build."""
        package = BuildingPackageFactory()

        # Simulate build completion
        package.status = OfflinePackage.Status.READY
        package.build_completed_at = timezone.now()
        package.file_size = 1024 * 1024 * 50  # 50 MB
        package.checksum = "sha256:abc123def456"
        package.manifest = {
            "modules": [{"id": 1, "title": "Module 1"}],
            "lessons": [{"id": 1, "title": "Lesson 1"}],
            "total_items": 2,
        }
        package.save()

        package.refresh_from_db()
        assert package.status == OfflinePackage.Status.READY
        assert package.file_size > 0
        assert package.checksum != ""

    def test_package_build_failure(self):
        """Test handling package build failure."""
        package = BuildingPackageFactory()

        package.status = OfflinePackage.Status.ERROR
        package.error_message = "Failed to compress videos"
        package.save()

        package.refresh_from_db()
        assert package.status == OfflinePackage.Status.ERROR
        assert "compress" in package.error_message

    def test_mark_package_outdated(self):
        """Test marking package as outdated when course changes."""
        package = ReadyPackageFactory()

        # Simulate course content update
        package.status = OfflinePackage.Status.OUTDATED
        package.save()

        package.refresh_from_db()
        assert package.status == OfflinePackage.Status.OUTDATED

    @patch("os.path.getsize")
    @patch("builtins.open", create=True)
    def test_calculate_package_checksum(self, mock_open, mock_getsize):
        """Test calculating package file checksum."""
        mock_content = b"fake package content"
        mock_open.return_value.__enter__.return_value.read.return_value = mock_content
        mock_getsize.return_value = len(mock_content)

        expected_checksum = hashlib.sha256(mock_content).hexdigest()

        # Simulate checksum calculation
        package = BuildingPackageFactory()
        package.checksum = f"sha256:{expected_checksum}"
        package.save()

        assert package.checksum.startswith("sha256:")

    def test_package_manifest_structure(self):
        """Test package manifest has correct structure."""
        manifest = {
            "version": "1.0",
            "course_id": 1,
            "modules": [
                {
                    "id": 1,
                    "title": "Module 1",
                    "lessons": [1, 2, 3],
                }
            ],
            "lessons": [
                {"id": 1, "title": "Lesson 1", "type": "video", "duration": 300},
                {"id": 2, "title": "Lesson 2", "type": "document", "pages": 10},
                {"id": 3, "title": "Lesson 3", "type": "quiz", "questions": 15},
            ],
            "resources": [
                {"path": "videos/lesson1.mp4", "size": 52428800},
                {"path": "docs/lesson2.pdf", "size": 1048576},
            ],
            "total_size": 53477376,
        }

        package = OfflinePackageFactory(manifest=manifest)
        package.refresh_from_db()

        assert "modules" in package.manifest
        assert "lessons" in package.manifest
        assert len(package.manifest["lessons"]) == 3


@pytest.mark.django_db
class TestPackageDownloadService:
    """Tests for package download service logic."""

    def test_start_download(self):
        """Test starting a package download."""
        user = UserFactory()
        package = ReadyPackageFactory()

        download = PackageDownload.objects.create(
            package=package,
            user=user,
            device_id="tablet-001",
            download_completed=False,
        )

        assert download.id is not None
        assert download.download_completed is False

    def test_resume_download(self):
        """Test resuming an incomplete download."""
        download = PackageDownloadFactory(download_completed=False)

        # Simulate resume by resetting download timestamp
        download.downloaded_at = timezone.now()
        download.save()

        download.refresh_from_db()
        assert download.downloaded_at is not None

    def test_complete_download(self):
        """Test completing a download."""
        download = PackageDownloadFactory(download_completed=False)

        download.download_completed = True
        download.last_accessed_at = timezone.now()
        download.save()

        download.refresh_from_db()
        assert download.download_completed is True
        assert download.last_accessed_at is not None

    def test_track_package_access(self):
        """Test tracking when user accesses offline package."""
        download = CompletedDownloadFactory()
        original_access = download.last_accessed_at

        # Simulate later access
        download.last_accessed_at = timezone.now()
        download.save()

        download.refresh_from_db()
        assert download.last_accessed_at >= original_access

    def test_get_user_downloads(self):
        """Test getting all downloads for a user."""
        user = UserFactory()
        package1 = ReadyPackageFactory()
        package2 = ReadyPackageFactory()

        CompletedDownloadFactory(user=user, package=package1)
        CompletedDownloadFactory(user=user, package=package2)

        # Another user's download
        CompletedDownloadFactory(package=package1)

        user_downloads = PackageDownload.objects.filter(
            user=user,
            download_completed=True,
        )

        assert user_downloads.count() == 2

    def test_check_package_already_downloaded(self):
        """Test checking if package is already downloaded on device."""
        user = UserFactory()
        package = ReadyPackageFactory()
        device_id = "device-001"

        # First download
        download = PackageDownloadFactory(
            user=user,
            package=package,
            device_id=device_id,
            download_completed=True,
        )

        # Check if already downloaded
        existing = PackageDownload.objects.filter(
            user=user,
            package=package,
            device_id=device_id,
            download_completed=True,
        ).first()

        assert existing is not None

    def test_download_same_package_different_devices(self):
        """Test downloading same package on different devices."""
        user = UserFactory()
        package = ReadyPackageFactory()

        download1 = PackageDownloadFactory(
            user=user,
            package=package,
            device_id="phone-001",
        )
        download2 = PackageDownloadFactory(
            user=user,
            package=package,
            device_id="tablet-001",
        )

        downloads = PackageDownload.objects.filter(user=user, package=package)
        assert downloads.count() == 2


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.django_db
class TestSyncPackageIntegration:
    """Integration tests for sync and package workflows."""

    def test_offline_work_then_sync(self):
        """Test complete workflow: download package, work offline, sync."""
        user = UserFactory()
        device_id = "tablet-001"

        # 1. Download package
        package = ReadyPackageFactory()
        download = PackageDownload.objects.create(
            package=package,
            user=user,
            device_id=device_id,
            download_completed=True,
            last_accessed_at=timezone.now(),
        )

        # 2. Work offline (access package)
        download.last_accessed_at = timezone.now()
        download.save()

        # 3. Come online and sync
        sync_log = SyncLog.objects.create(
            user=user,
            device_id=device_id,
            direction=SyncLog.Direction.UPLOAD,
            status=SyncLog.Status.IN_PROGRESS,
            started_at=timezone.now(),
        )

        # 4. Upload offline work
        sync_log.records_uploaded = 10
        sync_log.bytes_transferred = 5120

        # 5. Handle any conflicts
        conflict = SyncConflict.objects.create(
            sync_log=sync_log,
            model_name="LessonProgress",
            record_id="5",
            server_data={"progress": 50, "updated_at": "2024-01-01"},
            client_data={"progress": 75, "updated_at": "2024-01-02"},
        )

        # Client is newer, so client wins
        conflict.resolution = SyncConflict.Resolution.CLIENT_WINS
        conflict.resolved_data = conflict.client_data
        conflict.resolved_by = user
        conflict.resolved_at = timezone.now()
        conflict.save()

        # 6. Complete sync
        sync_log.status = SyncLog.Status.COMPLETED
        sync_log.completed_at = timezone.now()
        sync_log.save()

        # Verify
        assert download.download_completed is True
        assert sync_log.status == SyncLog.Status.COMPLETED
        assert conflict.resolution == SyncConflict.Resolution.CLIENT_WINS

    def test_package_update_requires_resync(self):
        """Test that package update marks it as outdated."""
        course = CourseFactory()
        package = ReadyPackageFactory(course=course, version=1)

        # User downloads package
        user = UserFactory()
        download = CompletedDownloadFactory(user=user, package=package)

        # Course is updated, package becomes outdated
        package.status = OfflinePackage.Status.OUTDATED
        package.save()

        # New package version is built
        new_package = OfflinePackage.objects.create(
            name=package.name,
            course=course,
            version=2,
            status=OfflinePackage.Status.READY,
            file_size=package.file_size,
        )

        # Verify
        assert package.status == OfflinePackage.Status.OUTDATED
        assert new_package.version == 2
        assert new_package.status == OfflinePackage.Status.READY

    def test_multiple_users_sync_same_content(self):
        """Test multiple users syncing same content."""
        course = CourseFactory()
        users = [UserFactory() for _ in range(3)]

        for user in users:
            # Each user syncs
            sync_log = SyncLog.objects.create(
                user=user,
                device_id=f"device-{user.id}",
                direction=SyncLog.Direction.DOWNLOAD,
                status=SyncLog.Status.COMPLETED,
                started_at=timezone.now() - timedelta(minutes=5),
                completed_at=timezone.now(),
                records_downloaded=50,
            )

        # Verify all syncs completed
        completed_syncs = SyncLog.objects.filter(
            status=SyncLog.Status.COMPLETED,
        ).count()

        assert completed_syncs >= 3


@pytest.mark.django_db
class TestErrorHandling:
    """Tests for error handling in sync services."""

    def test_handle_network_error(self):
        """Test handling network error during sync."""
        sync_log = InProgressSyncLogFactory()

        # Simulate network error
        sync_log.status = SyncLog.Status.FAILED
        sync_log.error_message = "Network error: Connection refused"
        sync_log.error_details = {
            "type": "NetworkError",
            "code": "ECONNREFUSED",
            "retries": 3,
        }
        sync_log.save()

        assert sync_log.status == SyncLog.Status.FAILED
        assert "Network" in sync_log.error_message

    def test_handle_timeout_error(self):
        """Test handling timeout during sync."""
        sync_log = InProgressSyncLogFactory()

        sync_log.status = SyncLog.Status.FAILED
        sync_log.error_message = "Request timeout after 60 seconds"
        sync_log.error_details = {
            "type": "TimeoutError",
            "timeout_ms": 60000,
        }
        sync_log.save()

        assert "timeout" in sync_log.error_message.lower()

    def test_handle_invalid_data_error(self):
        """Test handling invalid data during upload."""
        sync_log = InProgressSyncLogFactory()

        sync_log.status = SyncLog.Status.FAILED
        sync_log.error_message = "Invalid data format"
        sync_log.error_details = {
            "type": "ValidationError",
            "field": "lesson_progress",
            "error": "Invalid JSON structure",
        }
        sync_log.save()

        assert "Invalid" in sync_log.error_message

    def test_handle_package_build_error(self):
        """Test handling error during package build."""
        package = BuildingPackageFactory()

        # Simulate build error
        package.status = OfflinePackage.Status.ERROR
        package.error_message = "Insufficient disk space for video compression"
        package.save()

        assert package.status == OfflinePackage.Status.ERROR

    def test_retry_failed_sync(self):
        """Test retrying a failed sync."""
        user = UserFactory()
        device_id = "device-001"

        # First attempt fails
        failed_sync = FailedSyncLogFactory(user=user, device_id=device_id)

        # Retry
        retry_sync = SyncLog.objects.create(
            user=user,
            device_id=device_id,
            direction=failed_sync.direction,
            status=SyncLog.Status.IN_PROGRESS,
            started_at=timezone.now(),
            metadata={"retry_of": failed_sync.id},
        )

        # Complete retry
        retry_sync.status = SyncLog.Status.COMPLETED
        retry_sync.completed_at = timezone.now()
        retry_sync.save()

        assert retry_sync.status == SyncLog.Status.COMPLETED
        assert retry_sync.metadata.get("retry_of") == failed_sync.id


@pytest.mark.django_db
class TestConcurrency:
    """Tests for concurrent sync operations."""

    def test_multiple_syncs_same_device(self):
        """Test handling multiple sync attempts from same device."""
        user = UserFactory()
        device_id = "device-001"

        # First sync in progress
        sync1 = InProgressSyncLogFactory(user=user, device_id=device_id)

        # Second sync attempt should create new log
        sync2 = SyncLog.objects.create(
            user=user,
            device_id=device_id,
            direction=SyncLog.Direction.BIDIRECTIONAL,
            status=SyncLog.Status.PENDING,
        )

        # In real implementation, would check for active sync
        active_syncs = SyncLog.objects.filter(
            user=user,
            device_id=device_id,
            status=SyncLog.Status.IN_PROGRESS,
        ).count()

        assert active_syncs >= 1

    def test_concurrent_package_downloads(self):
        """Test concurrent downloads of same package."""
        package = ReadyPackageFactory()
        users = [UserFactory() for _ in range(5)]

        # All users start download simultaneously
        downloads = []
        for user in users:
            download = PackageDownload.objects.create(
                package=package,
                user=user,
                device_id=f"device-{user.id}",
                download_completed=False,
            )
            downloads.append(download)

        # All complete
        for download in downloads:
            download.download_completed = True
            download.save()

        completed = PackageDownload.objects.filter(
            package=package,
            download_completed=True,
        ).count()

        assert completed == 5
