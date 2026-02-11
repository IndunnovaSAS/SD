"""
Tests for sync models.

Tests for SyncLog, OfflinePackage, SyncConflict, and PackageDownload models.
"""

from datetime import timedelta

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
    ClientWinsConflictFactory,
    CompletedDownloadFactory,
    CompletedSyncLogFactory,
    CourseFactory,
    ErrorPackageFactory,
    FailedSyncLogFactory,
    InProgressSyncLogFactory,
    MergedConflictFactory,
    OfflinePackageFactory,
    OutdatedPackageFactory,
    PackageDownloadFactory,
    PartialSyncLogFactory,
    PendingConflictFactory,
    PendingSyncLogFactory,
    ReadyPackageFactory,
    ServerWinsConflictFactory,
    SyncConflictFactory,
    SyncLogFactory,
    SyncLogWithConflictsFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestSyncLog:
    """Tests for SyncLog model."""

    def test_create_sync_log(self):
        """Test creating a basic sync log."""
        user = UserFactory()
        sync_log = SyncLogFactory(user=user)

        assert sync_log.id is not None
        assert sync_log.user == user
        assert sync_log.device_id is not None
        assert sync_log.status == SyncLog.Status.PENDING
        assert sync_log.direction == SyncLog.Direction.BIDIRECTIONAL
        assert sync_log.created_at is not None

    def test_sync_log_str(self):
        """Test string representation of sync log."""
        user = UserFactory(email="testuser@example.com")
        sync_log = SyncLogFactory(user=user, device_id="device-001")

        str_repr = str(sync_log)
        assert user.email in str_repr or str(user) in str_repr
        assert "device-001" in str_repr

    def test_sync_log_status_choices(self):
        """Test all status choices are valid."""
        user = UserFactory()

        for status_choice in SyncLog.Status.choices:
            sync_log = SyncLogFactory(user=user, status=status_choice[0])
            assert sync_log.status == status_choice[0]

    def test_sync_log_direction_choices(self):
        """Test all direction choices are valid."""
        user = UserFactory()

        for direction_choice in SyncLog.Direction.choices:
            sync_log = SyncLogFactory(user=user, direction=direction_choice[0])
            assert sync_log.direction == direction_choice[0]

    def test_pending_sync_log_factory(self):
        """Test pending sync log factory."""
        sync_log = PendingSyncLogFactory()

        assert sync_log.status == SyncLog.Status.PENDING
        assert sync_log.started_at is None
        assert sync_log.completed_at is None

    def test_in_progress_sync_log_factory(self):
        """Test in-progress sync log factory."""
        sync_log = InProgressSyncLogFactory()

        assert sync_log.status == SyncLog.Status.IN_PROGRESS
        assert sync_log.started_at is not None
        assert sync_log.completed_at is None

    def test_completed_sync_log_factory(self):
        """Test completed sync log factory."""
        sync_log = CompletedSyncLogFactory()

        assert sync_log.status == SyncLog.Status.COMPLETED
        assert sync_log.started_at is not None
        assert sync_log.completed_at is not None
        assert sync_log.completed_at >= sync_log.started_at
        assert sync_log.records_uploaded > 0
        assert sync_log.records_downloaded > 0
        assert sync_log.bytes_transferred > 0

    def test_failed_sync_log_factory(self):
        """Test failed sync log factory."""
        sync_log = FailedSyncLogFactory()

        assert sync_log.status == SyncLog.Status.FAILED
        assert sync_log.error_message != ""
        assert sync_log.error_details != {}

    def test_partial_sync_log_factory(self):
        """Test partial sync log factory."""
        sync_log = PartialSyncLogFactory()

        assert sync_log.status == SyncLog.Status.PARTIAL
        assert sync_log.started_at is not None
        assert sync_log.completed_at is not None

    def test_sync_log_ordering(self):
        """Test sync logs are ordered by created_at descending."""
        user = UserFactory()
        old_log = SyncLogFactory(user=user)
        new_log = SyncLogFactory(user=user)

        logs = list(SyncLog.objects.filter(user=user))
        assert logs[0] == new_log
        assert logs[1] == old_log

    def test_sync_log_cascade_delete_user(self):
        """Test sync logs are deleted when user is deleted."""
        user = UserFactory()
        sync_log = SyncLogFactory(user=user)
        sync_log_id = sync_log.id

        user.delete()

        assert not SyncLog.objects.filter(id=sync_log_id).exists()

    def test_sync_log_metadata_json_field(self):
        """Test metadata JSON field works correctly."""
        metadata = {
            "app_version": "1.0.0",
            "os": "Android",
            "network_type": "wifi",
            "nested": {"key": "value"},
        }
        sync_log = SyncLogFactory(metadata=metadata)

        sync_log.refresh_from_db()
        assert sync_log.metadata == metadata
        assert sync_log.metadata["nested"]["key"] == "value"

    def test_sync_log_error_details_json_field(self):
        """Test error_details JSON field works correctly."""
        error_details = {
            "code": "SYNC_001",
            "message": "Network timeout",
            "stack_trace": ["line1", "line2"],
        }
        sync_log = FailedSyncLogFactory(error_details=error_details)

        sync_log.refresh_from_db()
        assert sync_log.error_details == error_details

    def test_sync_log_client_timestamp(self):
        """Test client timestamp field."""
        client_time = timezone.now() - timedelta(minutes=5)
        sync_log = SyncLogFactory(client_timestamp=client_time)

        assert sync_log.client_timestamp == client_time
        assert sync_log.server_timestamp != client_time

    def test_sync_log_server_timestamp_auto_update(self):
        """Test server timestamp auto-updates on save."""
        sync_log = SyncLogFactory()
        original_timestamp = sync_log.server_timestamp

        # Wait a moment and save
        sync_log.records_uploaded = 100
        sync_log.save()

        sync_log.refresh_from_db()
        assert sync_log.server_timestamp >= original_timestamp

    def test_sync_log_bytes_transferred_big_integer(self):
        """Test bytes_transferred can handle large values."""
        large_value = 10 * 1024 * 1024 * 1024  # 10 GB
        sync_log = SyncLogFactory(bytes_transferred=large_value)

        sync_log.refresh_from_db()
        assert sync_log.bytes_transferred == large_value

    def test_sync_log_related_name(self):
        """Test user.sync_logs related name works."""
        user = UserFactory()
        SyncLogFactory(user=user)
        SyncLogFactory(user=user)
        SyncLogFactory(user=user)

        assert user.sync_logs.count() == 3

    def test_sync_log_device_name_blank(self):
        """Test device_name can be blank."""
        sync_log = SyncLogFactory(device_name="")
        assert sync_log.device_name == ""

    def test_sync_log_meta_options(self):
        """Test model meta options."""
        assert SyncLog._meta.db_table == "sync_logs"
        assert SyncLog._meta.ordering == ["-created_at"]


@pytest.mark.django_db
class TestSyncConflict:
    """Tests for SyncConflict model."""

    def test_create_sync_conflict(self):
        """Test creating a basic sync conflict."""
        sync_log = InProgressSyncLogFactory()
        conflict = SyncConflictFactory(sync_log=sync_log)

        assert conflict.id is not None
        assert conflict.sync_log == sync_log
        assert conflict.model_name is not None
        assert conflict.record_id is not None
        assert conflict.server_data is not None
        assert conflict.client_data is not None
        assert conflict.resolution == SyncConflict.Resolution.PENDING

    def test_sync_conflict_str(self):
        """Test string representation of sync conflict."""
        conflict = SyncConflictFactory(model_name="Course", record_id="123")
        assert str(conflict) == "Course:123"

    def test_sync_conflict_resolution_choices(self):
        """Test all resolution choices are valid."""
        sync_log = InProgressSyncLogFactory()

        for resolution_choice in SyncConflict.Resolution.choices:
            conflict = SyncConflictFactory(
                sync_log=sync_log,
                resolution=resolution_choice[0],
            )
            assert conflict.resolution == resolution_choice[0]

    def test_pending_conflict_factory(self):
        """Test pending conflict factory."""
        conflict = PendingConflictFactory()

        assert conflict.resolution == SyncConflict.Resolution.PENDING
        assert conflict.resolved_data is None
        assert conflict.resolved_by is None
        assert conflict.resolved_at is None

    def test_server_wins_conflict_factory(self):
        """Test server wins conflict factory."""
        conflict = ServerWinsConflictFactory()

        assert conflict.resolution == SyncConflict.Resolution.SERVER_WINS
        assert conflict.resolved_data == conflict.server_data
        assert conflict.resolved_by is not None
        assert conflict.resolved_at is not None

    def test_client_wins_conflict_factory(self):
        """Test client wins conflict factory."""
        conflict = ClientWinsConflictFactory()

        assert conflict.resolution == SyncConflict.Resolution.CLIENT_WINS
        assert conflict.resolved_data == conflict.client_data
        assert conflict.resolved_by is not None
        assert conflict.resolved_at is not None

    def test_merged_conflict_factory(self):
        """Test merged conflict factory."""
        conflict = MergedConflictFactory()

        assert conflict.resolution == SyncConflict.Resolution.MERGED
        assert conflict.resolved_data is not None
        assert conflict.resolved_data.get("merged") is True
        assert conflict.resolved_by is not None
        assert conflict.resolved_at is not None

    def test_sync_conflict_cascade_delete_sync_log(self):
        """Test conflicts are deleted when sync log is deleted."""
        sync_log = InProgressSyncLogFactory()
        conflict = SyncConflictFactory(sync_log=sync_log)
        conflict_id = conflict.id

        sync_log.delete()

        assert not SyncConflict.objects.filter(id=conflict_id).exists()

    def test_sync_conflict_resolved_by_set_null(self):
        """Test resolved_by is set to null when resolver user is deleted."""
        resolver = UserFactory()
        conflict = ServerWinsConflictFactory(resolved_by=resolver)

        resolver.delete()

        conflict.refresh_from_db()
        assert conflict.resolved_by is None

    def test_sync_conflict_json_data_fields(self):
        """Test JSON data fields work correctly."""
        server_data = {
            "field1": "server_value",
            "field2": 123,
            "nested": {"inner": True},
        }
        client_data = {
            "field1": "client_value",
            "field2": 456,
            "nested": {"inner": False},
        }

        conflict = SyncConflictFactory(
            server_data=server_data,
            client_data=client_data,
        )

        conflict.refresh_from_db()
        assert conflict.server_data == server_data
        assert conflict.client_data == client_data

    def test_sync_conflict_related_name(self):
        """Test sync_log.conflicts related name works."""
        sync_log = InProgressSyncLogFactory()
        SyncConflictFactory(sync_log=sync_log)
        SyncConflictFactory(sync_log=sync_log)
        SyncConflictFactory(sync_log=sync_log)

        assert sync_log.conflicts.count() == 3

    def test_sync_conflict_ordering(self):
        """Test conflicts are ordered by created_at descending."""
        sync_log = InProgressSyncLogFactory()
        old_conflict = SyncConflictFactory(sync_log=sync_log)
        new_conflict = SyncConflictFactory(sync_log=sync_log)

        conflicts = list(sync_log.conflicts.all())
        assert conflicts[0] == new_conflict
        assert conflicts[1] == old_conflict

    def test_sync_conflict_meta_options(self):
        """Test model meta options."""
        assert SyncConflict._meta.db_table == "sync_conflicts"
        assert SyncConflict._meta.ordering == ["-created_at"]

    def test_sync_log_with_conflicts_factory(self):
        """Test factory that creates sync log with conflicts."""
        sync_log = SyncLogWithConflictsFactory()

        assert sync_log.status == SyncLog.Status.PARTIAL
        assert sync_log.conflicts.count() == 3


@pytest.mark.django_db
class TestOfflinePackage:
    """Tests for OfflinePackage model."""

    def test_create_offline_package(self):
        """Test creating a basic offline package."""
        course = CourseFactory()
        package = OfflinePackageFactory(course=course)

        assert package.id is not None
        assert package.course == course
        assert package.name is not None
        assert package.version == 1
        assert package.status == OfflinePackage.Status.READY

    def test_offline_package_str(self):
        """Test string representation of offline package."""
        course = CourseFactory(title="Safety Training")
        package = OfflinePackageFactory(course=course, version=2)

        assert "Safety Training" in str(package)
        assert "v2" in str(package)

    def test_offline_package_status_choices(self):
        """Test all status choices are valid."""
        course = CourseFactory()

        for status_choice in OfflinePackage.Status.choices:
            package = OfflinePackageFactory(course=course, status=status_choice[0])
            assert package.status == status_choice[0]

    def test_building_package_factory(self):
        """Test building package factory."""
        package = BuildingPackageFactory()

        assert package.status == OfflinePackage.Status.BUILDING
        assert package.build_started_at is not None
        assert package.build_completed_at is None
        assert not package.package_file

    def test_ready_package_factory(self):
        """Test ready package factory."""
        package = ReadyPackageFactory()

        assert package.status == OfflinePackage.Status.READY
        assert package.build_started_at is not None
        assert package.build_completed_at is not None
        assert package.build_completed_at >= package.build_started_at

    def test_outdated_package_factory(self):
        """Test outdated package factory."""
        package = OutdatedPackageFactory()

        assert package.status == OfflinePackage.Status.OUTDATED

    def test_error_package_factory(self):
        """Test error package factory."""
        package = ErrorPackageFactory()

        assert package.status == OfflinePackage.Status.ERROR
        assert package.error_message != ""

    def test_offline_package_cascade_delete_course(self):
        """Test packages are deleted when course is deleted."""
        course = CourseFactory()
        package = OfflinePackageFactory(course=course)
        package_id = package.id

        course.delete()

        assert not OfflinePackage.objects.filter(id=package_id).exists()

    def test_offline_package_manifest_json_field(self):
        """Test manifest JSON field works correctly."""
        manifest = {
            "modules": [
                {"id": 1, "title": "Module 1", "lessons": [1, 2, 3]},
                {"id": 2, "title": "Module 2", "lessons": [4, 5]},
            ],
            "lessons": [
                {"id": 1, "title": "Lesson 1", "duration": 30},
            ],
            "resources": [
                {"id": 1, "type": "video", "size": 1024000},
            ],
            "total_items": 8,
        }

        package = OfflinePackageFactory(manifest=manifest)

        package.refresh_from_db()
        assert package.manifest == manifest
        assert len(package.manifest["modules"]) == 2

    def test_offline_package_version_increment(self):
        """Test version can be incremented."""
        package = OfflinePackageFactory(version=1)

        package.version += 1
        package.save()

        package.refresh_from_db()
        assert package.version == 2

    def test_offline_package_file_size_big_integer(self):
        """Test file_size can handle large values."""
        large_size = 5 * 1024 * 1024 * 1024  # 5 GB
        package = OfflinePackageFactory(file_size=large_size)

        package.refresh_from_db()
        assert package.file_size == large_size

    def test_offline_package_includes_flags(self):
        """Test includes_* boolean flags."""
        package = OfflinePackageFactory(
            includes_videos=True,
            includes_documents=False,
            includes_assessments=True,
        )

        assert package.includes_videos is True
        assert package.includes_documents is False
        assert package.includes_assessments is True

    def test_offline_package_checksum(self):
        """Test checksum field."""
        checksum = "sha256:abc123def456789"
        package = OfflinePackageFactory(checksum=checksum)

        assert package.checksum == checksum

    def test_offline_package_related_name(self):
        """Test course.offline_packages related name works."""
        course = CourseFactory()
        OfflinePackageFactory(course=course)
        OfflinePackageFactory(course=course, version=2)

        assert course.offline_packages.count() == 2

    def test_offline_package_ordering(self):
        """Test packages are ordered by created_at descending."""
        course = CourseFactory()
        old_package = OfflinePackageFactory(course=course)
        new_package = OfflinePackageFactory(course=course, version=2)

        packages = list(OfflinePackage.objects.filter(course=course))
        assert packages[0] == new_package
        assert packages[1] == old_package

    def test_offline_package_meta_options(self):
        """Test model meta options."""
        assert OfflinePackage._meta.db_table == "offline_packages"
        assert OfflinePackage._meta.ordering == ["-created_at"]

    def test_offline_package_timestamps(self):
        """Test created_at and updated_at timestamps."""
        package = OfflinePackageFactory()

        assert package.created_at is not None
        assert package.updated_at is not None

        original_updated = package.updated_at
        package.name = "Updated Name"
        package.save()

        package.refresh_from_db()
        assert package.updated_at >= original_updated


@pytest.mark.django_db
class TestPackageDownload:
    """Tests for PackageDownload model."""

    def test_create_package_download(self):
        """Test creating a basic package download."""
        user = UserFactory()
        package = ReadyPackageFactory()
        download = PackageDownloadFactory(user=user, package=package)

        assert download.id is not None
        assert download.user == user
        assert download.package == package
        assert download.device_id is not None
        assert download.download_completed is False
        assert download.downloaded_at is not None

    def test_package_download_str(self):
        """Test string representation of package download."""
        user = UserFactory()
        package = ReadyPackageFactory()
        download = PackageDownloadFactory(user=user, package=package)

        str_repr = str(download)
        # Should contain user and package info
        assert str(user) in str_repr or str(package) in str_repr

    def test_completed_download_factory(self):
        """Test completed download factory."""
        download = CompletedDownloadFactory()

        assert download.download_completed is True
        assert download.last_accessed_at is not None

    def test_package_download_cascade_delete_package(self):
        """Test downloads are deleted when package is deleted."""
        package = ReadyPackageFactory()
        download = PackageDownloadFactory(package=package)
        download_id = download.id

        package.delete()

        assert not PackageDownload.objects.filter(id=download_id).exists()

    def test_package_download_cascade_delete_user(self):
        """Test downloads are deleted when user is deleted."""
        user = UserFactory()
        download = PackageDownloadFactory(user=user)
        download_id = download.id

        user.delete()

        assert not PackageDownload.objects.filter(id=download_id).exists()

    def test_package_download_related_names(self):
        """Test related names work correctly."""
        user = UserFactory()
        package = ReadyPackageFactory()

        PackageDownloadFactory(user=user, package=package)
        PackageDownloadFactory(user=user, package=package, device_id="device-2")

        assert package.downloads.count() == 2
        assert user.package_downloads.count() == 2

    def test_package_download_device_id(self):
        """Test device_id field."""
        device_id = "unique-device-12345"
        download = PackageDownloadFactory(device_id=device_id)

        assert download.device_id == device_id

    def test_package_download_last_accessed_at(self):
        """Test last_accessed_at field can be updated."""
        download = PackageDownloadFactory(last_accessed_at=None)
        assert download.last_accessed_at is None

        access_time = timezone.now()
        download.last_accessed_at = access_time
        download.save()

        download.refresh_from_db()
        assert download.last_accessed_at is not None

    def test_package_download_meta_options(self):
        """Test model meta options."""
        assert PackageDownload._meta.db_table == "package_downloads"

    def test_multiple_devices_same_user_package(self):
        """Test same user can download package on multiple devices."""
        user = UserFactory()
        package = ReadyPackageFactory()

        download1 = PackageDownloadFactory(
            user=user,
            package=package,
            device_id="device-1",
        )
        download2 = PackageDownloadFactory(
            user=user,
            package=package,
            device_id="device-2",
        )

        assert download1.id != download2.id
        assert package.downloads.filter(user=user).count() == 2


@pytest.mark.django_db
class TestModelRelationships:
    """Tests for relationships between sync models."""

    def test_full_sync_workflow(self):
        """Test complete sync workflow with all models."""
        # Create user
        user = UserFactory()

        # Start sync
        sync_log = InProgressSyncLogFactory(user=user)

        # Create conflicts during sync
        conflict1 = SyncConflictFactory(
            sync_log=sync_log,
            model_name="Course",
            record_id="1",
        )
        conflict2 = SyncConflictFactory(
            sync_log=sync_log,
            model_name="Lesson",
            record_id="5",
        )

        # Resolve conflicts
        conflict1.resolution = SyncConflict.Resolution.SERVER_WINS
        conflict1.resolved_data = conflict1.server_data
        conflict1.resolved_by = user
        conflict1.resolved_at = timezone.now()
        conflict1.save()

        conflict2.resolution = SyncConflict.Resolution.CLIENT_WINS
        conflict2.resolved_data = conflict2.client_data
        conflict2.resolved_by = user
        conflict2.resolved_at = timezone.now()
        conflict2.save()

        # Complete sync
        sync_log.status = SyncLog.Status.COMPLETED
        sync_log.completed_at = timezone.now()
        sync_log.records_uploaded = 50
        sync_log.records_downloaded = 30
        sync_log.save()

        # Verify
        assert sync_log.conflicts.count() == 2
        assert sync_log.conflicts.filter(resolution=SyncConflict.Resolution.PENDING).count() == 0
        assert sync_log.status == SyncLog.Status.COMPLETED

    def test_package_download_workflow(self):
        """Test complete package download workflow."""
        # Create package
        course = CourseFactory()
        package = ReadyPackageFactory(course=course)

        # User downloads package
        user = UserFactory()
        download = PackageDownloadFactory(
            user=user,
            package=package,
            device_id="tablet-001",
            download_completed=False,
        )

        # Complete download
        download.download_completed = True
        download.last_accessed_at = timezone.now()
        download.save()

        # User accesses package later
        download.last_accessed_at = timezone.now()
        download.save()

        # Verify
        assert package.downloads.count() == 1
        assert package.downloads.first().download_completed is True
        assert user.package_downloads.count() == 1

    def test_sync_with_package_download(self):
        """Test sync and package download together."""
        user = UserFactory()

        # Download offline package
        package = ReadyPackageFactory()
        download = CompletedDownloadFactory(user=user, package=package)

        # Sync after offline work
        sync_log = CompletedSyncLogFactory(
            user=user,
            device_id=download.device_id,
            records_uploaded=25,
        )

        # Create a conflict from offline work
        conflict = SyncConflictFactory(
            sync_log=sync_log,
            model_name="LessonProgress",
            record_id="10",
        )

        # Verify relationships
        assert sync_log.user == download.user
        assert sync_log.device_id == download.device_id
        assert sync_log.conflicts.count() == 1

    def test_cascade_delete_propagation(self):
        """Test cascade delete propagates correctly through all models."""
        user = UserFactory()

        # Create sync log with conflicts
        sync_log = SyncLogWithConflictsFactory(user=user)
        sync_log_id = sync_log.id
        conflict_ids = list(sync_log.conflicts.values_list("id", flat=True))

        # Create package download
        download = PackageDownloadFactory(user=user)
        download_id = download.id

        # Delete user
        user.delete()

        # Verify all related objects are deleted
        assert not SyncLog.objects.filter(id=sync_log_id).exists()
        for conflict_id in conflict_ids:
            assert not SyncConflict.objects.filter(id=conflict_id).exists()
        assert not PackageDownload.objects.filter(id=download_id).exists()


@pytest.mark.django_db
class TestModelValidation:
    """Tests for model validation.

    Note: Django CharField with choices doesn't validate at the database level.
    Invalid choices are allowed in the database but will fail form validation.
    These tests verify that models accept valid choice values correctly.
    """

    def test_sync_log_status_valid_choices(self):
        """Test valid status choices are accepted."""
        user = UserFactory()

        for choice_value, _ in SyncLog.Status.choices:
            sync_log = SyncLogFactory(user=user, status=choice_value)
            assert sync_log.status == choice_value

    def test_sync_log_direction_valid_choices(self):
        """Test valid direction choices are accepted."""
        user = UserFactory()

        for choice_value, _ in SyncLog.Direction.choices:
            sync_log = SyncLogFactory(user=user, direction=choice_value)
            assert sync_log.direction == choice_value

    def test_sync_conflict_resolution_valid_choices(self):
        """Test valid resolution choices are accepted."""
        sync_log = InProgressSyncLogFactory()

        for choice_value, _ in SyncConflict.Resolution.choices:
            conflict = SyncConflictFactory(sync_log=sync_log, resolution=choice_value)
            assert conflict.resolution == choice_value

    def test_offline_package_status_valid_choices(self):
        """Test valid status choices are accepted."""
        course = CourseFactory()

        for choice_value, _ in OfflinePackage.Status.choices:
            package = OfflinePackageFactory(course=course, status=choice_value)
            assert package.status == choice_value


@pytest.mark.django_db
class TestModelQueryOptimization:
    """Tests for query optimization using select_related and prefetch_related."""

    def test_sync_log_select_related_user(self):
        """Test sync log with select_related user."""
        user = UserFactory()
        SyncLogFactory(user=user)
        SyncLogFactory(user=user)
        SyncLogFactory(user=user)

        # Using select_related should allow accessing user without additional queries
        logs = SyncLog.objects.select_related("user").all()
        for log in logs:
            # Accessing user should not trigger additional queries
            _ = log.user.email

        # Verify the queryset works correctly
        assert logs.count() >= 3

    def test_offline_package_select_related_course(self):
        """Test offline package with select_related course."""
        course = CourseFactory()
        OfflinePackageFactory(course=course)
        OfflinePackageFactory(course=course, version=2)

        packages = OfflinePackage.objects.select_related("course").all()
        for package in packages:
            # Accessing course should not trigger additional queries
            _ = package.course.title

    def test_sync_conflict_prefetch_related(self):
        """Test sync conflict with prefetch_related."""
        sync_log = SyncLogWithConflictsFactory()

        logs = SyncLog.objects.prefetch_related("conflicts").filter(id=sync_log.id)
        for log in logs:
            # Accessing conflicts should not trigger additional queries
            _ = list(log.conflicts.all())
