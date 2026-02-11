"""
Serializers for offline sync API.
"""

from rest_framework import serializers

from apps.sync.models import (
    OfflinePackage,
    PackageDownload,
    SyncConflict,
    SyncLog,
)


class SyncLogListSerializer(serializers.ModelSerializer):
    """List serializer for sync logs."""

    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    direction_display = serializers.CharField(source="get_direction_display", read_only=True)

    class Meta:
        model = SyncLog
        fields = [
            "id",
            "user",
            "user_name",
            "device_id",
            "device_name",
            "direction",
            "direction_display",
            "status",
            "status_display",
            "records_uploaded",
            "records_downloaded",
            "bytes_transferred",
            "created_at",
        ]


class SyncLogSerializer(serializers.ModelSerializer):
    """Full serializer for sync logs."""

    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    conflicts = serializers.SerializerMethodField()

    class Meta:
        model = SyncLog
        fields = [
            "id",
            "user",
            "user_name",
            "device_id",
            "device_name",
            "direction",
            "status",
            "started_at",
            "completed_at",
            "records_uploaded",
            "records_downloaded",
            "bytes_transferred",
            "error_message",
            "error_details",
            "client_timestamp",
            "server_timestamp",
            "metadata",
            "conflicts",
            "created_at",
        ]
        read_only_fields = [
            "user",
            "started_at",
            "completed_at",
            "server_timestamp",
            "created_at",
        ]

    def get_conflicts(self, obj):
        conflicts = obj.conflicts.all()[:10]
        return SyncConflictSerializer(conflicts, many=True).data


class SyncStartSerializer(serializers.Serializer):
    """Serializer for starting a sync operation."""

    device_id = serializers.CharField(max_length=100)
    device_name = serializers.CharField(max_length=200, required=False)
    direction = serializers.ChoiceField(
        choices=SyncLog.Direction.choices,
        default=SyncLog.Direction.BIDIRECTIONAL,
    )
    client_timestamp = serializers.DateTimeField(required=False)
    metadata = serializers.JSONField(required=False, default=dict)


class SyncUploadSerializer(serializers.Serializer):
    """Serializer for uploading sync data."""

    sync_id = serializers.IntegerField()
    data = serializers.JSONField()


class SyncConflictSerializer(serializers.ModelSerializer):
    """Serializer for sync conflicts."""

    resolution_display = serializers.CharField(source="get_resolution_display", read_only=True)
    resolved_by_name = serializers.CharField(source="resolved_by.get_full_name", read_only=True)

    class Meta:
        model = SyncConflict
        fields = [
            "id",
            "sync_log",
            "model_name",
            "record_id",
            "server_data",
            "client_data",
            "resolution",
            "resolution_display",
            "resolved_data",
            "resolved_by",
            "resolved_by_name",
            "resolved_at",
            "created_at",
        ]
        read_only_fields = [
            "sync_log",
            "model_name",
            "record_id",
            "server_data",
            "client_data",
            "resolved_by",
            "resolved_at",
            "created_at",
        ]


class SyncConflictResolveSerializer(serializers.Serializer):
    """Serializer for resolving sync conflicts."""

    resolution = serializers.ChoiceField(
        choices=[
            (SyncConflict.Resolution.SERVER_WINS, "server_wins"),
            (SyncConflict.Resolution.CLIENT_WINS, "client_wins"),
            (SyncConflict.Resolution.MERGED, "merged"),
        ]
    )
    resolved_data = serializers.JSONField(required=False)


class OfflinePackageListSerializer(serializers.ModelSerializer):
    """List serializer for offline packages."""

    course_title = serializers.CharField(source="course.title", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    download_count = serializers.SerializerMethodField()

    class Meta:
        model = OfflinePackage
        fields = [
            "id",
            "name",
            "course",
            "course_title",
            "version",
            "status",
            "status_display",
            "file_size",
            "includes_videos",
            "includes_documents",
            "includes_assessments",
            "download_count",
            "created_at",
        ]

    def get_download_count(self, obj):
        return obj.downloads.count()


class OfflinePackageSerializer(serializers.ModelSerializer):
    """Full serializer for offline packages."""

    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = OfflinePackage
        fields = [
            "id",
            "name",
            "description",
            "course",
            "course_title",
            "version",
            "status",
            "package_file",
            "file_size",
            "checksum",
            "includes_videos",
            "includes_documents",
            "includes_assessments",
            "manifest",
            "build_started_at",
            "build_completed_at",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "version",
            "status",
            "package_file",
            "file_size",
            "checksum",
            "manifest",
            "build_started_at",
            "build_completed_at",
            "error_message",
            "created_at",
            "updated_at",
        ]


class OfflinePackageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating offline packages."""

    class Meta:
        model = OfflinePackage
        fields = [
            "name",
            "description",
            "course",
            "includes_videos",
            "includes_documents",
            "includes_assessments",
        ]


class PackageDownloadSerializer(serializers.ModelSerializer):
    """Serializer for package downloads."""

    package_name = serializers.CharField(source="package.name", read_only=True)
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = PackageDownload
        fields = [
            "id",
            "package",
            "package_name",
            "user",
            "user_name",
            "device_id",
            "downloaded_at",
            "download_completed",
            "last_accessed_at",
        ]
        read_only_fields = [
            "user",
            "downloaded_at",
        ]


class PackageDownloadStartSerializer(serializers.Serializer):
    """Serializer for starting a package download."""

    package_id = serializers.IntegerField()
    device_id = serializers.CharField(max_length=100)
