"""
ViewSets for offline sync API.
"""

from django.db.models import Q
from django.utils import timezone

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.sync.models import (
    OfflinePackage,
    PackageDownload,
    SyncConflict,
    SyncLog,
)

from .serializers import (
    OfflinePackageCreateSerializer,
    OfflinePackageListSerializer,
    OfflinePackageSerializer,
    PackageDownloadSerializer,
    PackageDownloadStartSerializer,
    SyncConflictResolveSerializer,
    SyncConflictSerializer,
    SyncLogListSerializer,
    SyncLogSerializer,
    SyncStartSerializer,
    SyncUploadSerializer,
)


class SyncLogViewSet(viewsets.ModelViewSet):
    """ViewSet for managing sync logs."""

    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post"]

    def get_queryset(self):
        queryset = SyncLog.objects.select_related("user")

        # Regular users see only their logs
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)

        # Filter by status
        sync_status = self.request.query_params.get("status")
        if sync_status:
            queryset = queryset.filter(status=sync_status)

        # Filter by direction
        direction = self.request.query_params.get("direction")
        if direction:
            queryset = queryset.filter(direction=direction)

        # Filter by device
        device_id = self.request.query_params.get("device")
        if device_id:
            queryset = queryset.filter(device_id=device_id)

        # Filter by date range
        date_from = self.request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "list":
            return SyncLogListSerializer
        if self.action == "start":
            return SyncStartSerializer
        if self.action == "upload":
            return SyncUploadSerializer
        return SyncLogSerializer

    @action(detail=False, methods=["post"])
    def start(self, request):
        """Start a new sync operation."""
        serializer = SyncStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sync_log = SyncLog.objects.create(
            user=request.user,
            device_id=serializer.validated_data["device_id"],
            device_name=serializer.validated_data.get("device_name", ""),
            direction=serializer.validated_data["direction"],
            status=SyncLog.Status.IN_PROGRESS,
            started_at=timezone.now(),
            client_timestamp=serializer.validated_data.get("client_timestamp"),
            metadata=serializer.validated_data.get("metadata", {}),
        )

        return Response(
            SyncLogSerializer(sync_log).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def upload(self, request, pk=None):
        """Upload sync data."""
        sync_log = self.get_object()

        if sync_log.user != request.user:
            return Response(
                {"error": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if sync_log.status != SyncLog.Status.IN_PROGRESS:
            return Response(
                {"error": "La sincronización no está en progreso"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data.get("data", {})

        # In a real implementation, process the uploaded data here
        # Check for conflicts, merge data, etc.
        records_count = len(data.get("records", []))

        sync_log.records_uploaded += records_count
        sync_log.save()

        return Response(
            {
                "received": records_count,
                "sync_id": sync_log.id,
            }
        )

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """Download sync data for client."""
        sync_log = self.get_object()

        if sync_log.user != request.user:
            return Response(
                {"error": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # In a real implementation, gather data to send to client
        # For now, return empty data structure
        return Response(
            {
                "sync_id": sync_log.id,
                "records": [],
                "server_timestamp": timezone.now().isoformat(),
            }
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Complete a sync operation."""
        sync_log = self.get_object()

        if sync_log.user != request.user:
            return Response(
                {"error": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if sync_log.status != SyncLog.Status.IN_PROGRESS:
            return Response(
                {"error": "La sincronización no está en progreso"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check for unresolved conflicts
        pending_conflicts = sync_log.conflicts.filter(
            resolution=SyncConflict.Resolution.PENDING
        ).count()

        if pending_conflicts > 0:
            sync_log.status = SyncLog.Status.PARTIAL
        else:
            sync_log.status = SyncLog.Status.COMPLETED

        sync_log.completed_at = timezone.now()
        sync_log.save()

        return Response(SyncLogSerializer(sync_log).data)

    @action(detail=False, methods=["get"])
    def last(self, request):
        """Get last sync for current user and device."""
        device_id = request.query_params.get("device")

        if not device_id:
            return Response(
                {"error": "device es requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sync_log = (
            SyncLog.objects.filter(
                user=request.user,
                device_id=device_id,
                status=SyncLog.Status.COMPLETED,
            )
            .order_by("-completed_at")
            .first()
        )

        if not sync_log:
            return Response({"last_sync": None})

        return Response(
            {
                "last_sync": SyncLogSerializer(sync_log).data,
            }
        )


class SyncConflictViewSet(viewsets.ModelViewSet):
    """ViewSet for managing sync conflicts."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SyncConflictSerializer
    http_method_names = ["get", "post"]

    def get_queryset(self):
        queryset = SyncConflict.objects.select_related("sync_log", "sync_log__user", "resolved_by")

        # Regular users see only their conflicts
        if not self.request.user.is_staff:
            queryset = queryset.filter(sync_log__user=self.request.user)

        # Filter by resolution status
        resolution = self.request.query_params.get("resolution")
        if resolution:
            queryset = queryset.filter(resolution=resolution)

        # Filter by model
        model_name = self.request.query_params.get("model")
        if model_name:
            queryset = queryset.filter(model_name=model_name)

        return queryset.order_by("-created_at")

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Resolve a sync conflict."""
        conflict = self.get_object()

        if conflict.sync_log.user != request.user and not request.user.is_staff:
            return Response(
                {"error": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if conflict.resolution != SyncConflict.Resolution.PENDING:
            return Response(
                {"error": "El conflicto ya fue resuelto"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SyncConflictResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resolution = serializer.validated_data["resolution"]

        if resolution == SyncConflict.Resolution.SERVER_WINS:
            conflict.resolved_data = conflict.server_data
        elif resolution == SyncConflict.Resolution.CLIENT_WINS:
            conflict.resolved_data = conflict.client_data
        elif resolution == SyncConflict.Resolution.MERGED:
            resolved_data = serializer.validated_data.get("resolved_data")
            if not resolved_data:
                return Response(
                    {"error": "resolved_data es requerido para fusión"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            conflict.resolved_data = resolved_data

        conflict.resolution = resolution
        conflict.resolved_by = request.user
        conflict.resolved_at = timezone.now()
        conflict.save()

        return Response(SyncConflictSerializer(conflict).data)

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """Get pending conflicts for current user."""
        conflicts = SyncConflict.objects.filter(
            sync_log__user=request.user,
            resolution=SyncConflict.Resolution.PENDING,
        ).order_by("-created_at")

        return Response(SyncConflictSerializer(conflicts, many=True).data)


class OfflinePackageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing offline packages."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = OfflinePackage.objects.select_related("course")

        # Filter by status
        package_status = self.request.query_params.get("status")
        if package_status:
            queryset = queryset.filter(status=package_status)

        # Filter by course
        course_id = self.request.query_params.get("course")
        if course_id:
            queryset = queryset.filter(course_id=course_id)

        # Only show ready packages for non-staff
        if not self.request.user.is_staff:
            queryset = queryset.filter(status=OfflinePackage.Status.READY)

        # Search
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(course__title__icontains=search)
            )

        return queryset.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "list":
            return OfflinePackageListSerializer
        if self.action == "create":
            return OfflinePackageCreateSerializer
        return OfflinePackageSerializer

    def create(self, request, *args, **kwargs):
        """Only staff can create packages."""
        if not request.user.is_staff:
            return Response(
                {"error": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def build(self, request, pk=None):
        """Trigger package build."""
        if not request.user.is_staff:
            return Response(
                {"error": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )

        package = self.get_object()

        if package.status == OfflinePackage.Status.BUILDING:
            return Response(
                {"error": "El paquete ya está en construcción"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Increment version if rebuilding
        if package.status in [OfflinePackage.Status.READY, OfflinePackage.Status.OUTDATED]:
            package.version += 1

        package.status = OfflinePackage.Status.BUILDING
        package.build_started_at = timezone.now()
        package.build_completed_at = None
        package.error_message = ""
        package.save()

        # In a real implementation, queue a background task
        return Response(
            {
                "message": "Construcción del paquete iniciada",
                "package_id": package.id,
                "version": package.version,
            }
        )

    @action(detail=True, methods=["get"])
    def download_url(self, request, pk=None):
        """Get download URL for a package."""
        package = self.get_object()

        if package.status != OfflinePackage.Status.READY:
            return Response(
                {"error": "El paquete no está listo"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not package.package_file:
            return Response(
                {"error": "El archivo del paquete no existe"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "url": package.package_file.url,
                "checksum": package.checksum,
                "file_size": package.file_size,
            }
        )

    @action(detail=False, methods=["get"])
    def available(self, request):
        """Get available packages for download."""
        packages = (
            OfflinePackage.objects.filter(status=OfflinePackage.Status.READY)
            .select_related("course")
            .order_by("course__title")
        )

        return Response(OfflinePackageListSerializer(packages, many=True).data)


class PackageDownloadViewSet(viewsets.ModelViewSet):
    """ViewSet for managing package downloads."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PackageDownloadSerializer
    http_method_names = ["get", "post"]

    def get_queryset(self):
        queryset = PackageDownload.objects.select_related("package", "user")

        # Regular users see only their downloads
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)

        # Filter by package
        package_id = self.request.query_params.get("package")
        if package_id:
            queryset = queryset.filter(package_id=package_id)

        # Filter by device
        device_id = self.request.query_params.get("device")
        if device_id:
            queryset = queryset.filter(device_id=device_id)

        # Filter by completed
        completed = self.request.query_params.get("completed")
        if completed is not None:
            queryset = queryset.filter(download_completed=completed.lower() == "true")

        return queryset.order_by("-downloaded_at")

    @action(detail=False, methods=["post"])
    def start(self, request):
        """Start a package download."""
        serializer = PackageDownloadStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        package_id = serializer.validated_data["package_id"]
        device_id = serializer.validated_data["device_id"]

        try:
            package = OfflinePackage.objects.get(
                id=package_id,
                status=OfflinePackage.Status.READY,
            )
        except OfflinePackage.DoesNotExist:
            return Response(
                {"error": "Paquete no encontrado o no disponible"},
                status=status.HTTP_404_NOT_FOUND,
            )

        download, created = PackageDownload.objects.get_or_create(
            package=package,
            user=request.user,
            device_id=device_id,
            defaults={"download_completed": False},
        )

        if not created:
            download.download_completed = False
            download.downloaded_at = timezone.now()
            download.save()

        return Response(
            {
                "download_id": download.id,
                "url": package.package_file.url if package.package_file else None,
                "checksum": package.checksum,
                "file_size": package.file_size,
            }
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark a download as complete."""
        download = self.get_object()

        if download.user != request.user:
            return Response(
                {"error": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )

        download.download_completed = True
        download.last_accessed_at = timezone.now()
        download.save()

        return Response(PackageDownloadSerializer(download).data)

    @action(detail=False, methods=["get"])
    def my_downloads(self, request):
        """Get current user's downloads."""
        downloads = (
            PackageDownload.objects.filter(
                user=request.user,
                download_completed=True,
            )
            .select_related("package")
            .order_by("-last_accessed_at")
        )

        return Response(PackageDownloadSerializer(downloads, many=True).data)

    @action(detail=True, methods=["post"])
    def access(self, request, pk=None):
        """Record package access."""
        download = self.get_object()

        if download.user != request.user:
            return Response(
                {"error": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )

        download.last_accessed_at = timezone.now()
        download.save()

        return Response({"accessed_at": download.last_accessed_at})
