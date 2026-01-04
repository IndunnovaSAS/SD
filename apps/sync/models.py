"""
Offline sync models for SD LMS.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class SyncLog(models.Model):
    """
    Log of sync operations.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pendiente")
        IN_PROGRESS = "in_progress", _("En progreso")
        COMPLETED = "completed", _("Completado")
        FAILED = "failed", _("Fallido")
        PARTIAL = "partial", _("Parcial")

    class Direction(models.TextChoices):
        UPLOAD = "upload", _("Subida")
        DOWNLOAD = "download", _("Descarga")
        BIDIRECTIONAL = "bidirectional", _("Bidireccional")

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="sync_logs",
        verbose_name=_("Usuario"),
    )
    device_id = models.CharField(
        _("ID del dispositivo"),
        max_length=100,
    )
    device_name = models.CharField(
        _("Nombre del dispositivo"),
        max_length=200,
        blank=True,
    )
    direction = models.CharField(
        _("Dirección"),
        max_length=20,
        choices=Direction.choices,
        default=Direction.BIDIRECTIONAL,
    )
    status = models.CharField(
        _("Estado"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    started_at = models.DateTimeField(
        _("Fecha de inicio"),
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(
        _("Fecha de completado"),
        null=True,
        blank=True,
    )
    records_uploaded = models.PositiveIntegerField(
        _("Registros subidos"),
        default=0,
    )
    records_downloaded = models.PositiveIntegerField(
        _("Registros descargados"),
        default=0,
    )
    bytes_transferred = models.PositiveBigIntegerField(
        _("Bytes transferidos"),
        default=0,
    )
    error_message = models.TextField(_("Mensaje de error"), blank=True)
    error_details = models.JSONField(_("Detalles del error"), default=dict, blank=True)
    client_timestamp = models.DateTimeField(
        _("Timestamp del cliente"),
        null=True,
        blank=True,
    )
    server_timestamp = models.DateTimeField(
        _("Timestamp del servidor"),
        auto_now=True,
    )
    metadata = models.JSONField(_("Metadatos"), default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sync_logs"
        verbose_name = _("Log de sincronización")
        verbose_name_plural = _("Logs de sincronización")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.device_id} - {self.created_at}"


class SyncConflict(models.Model):
    """
    Conflict resolution for sync operations.
    """

    class Resolution(models.TextChoices):
        PENDING = "pending", _("Pendiente")
        SERVER_WINS = "server_wins", _("Servidor gana")
        CLIENT_WINS = "client_wins", _("Cliente gana")
        MERGED = "merged", _("Fusionado")
        MANUAL = "manual", _("Manual")

    sync_log = models.ForeignKey(
        SyncLog,
        on_delete=models.CASCADE,
        related_name="conflicts",
        verbose_name=_("Log de sincronización"),
    )
    model_name = models.CharField(
        _("Nombre del modelo"),
        max_length=100,
    )
    record_id = models.CharField(
        _("ID del registro"),
        max_length=100,
    )
    server_data = models.JSONField(
        _("Datos del servidor"),
    )
    client_data = models.JSONField(
        _("Datos del cliente"),
    )
    resolution = models.CharField(
        _("Resolución"),
        max_length=20,
        choices=Resolution.choices,
        default=Resolution.PENDING,
    )
    resolved_data = models.JSONField(
        _("Datos resueltos"),
        null=True,
        blank=True,
    )
    resolved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sync_conflicts_resolved",
        verbose_name=_("Resuelto por"),
    )
    resolved_at = models.DateTimeField(
        _("Fecha de resolución"),
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sync_conflicts"
        verbose_name = _("Conflicto de sincronización")
        verbose_name_plural = _("Conflictos de sincronización")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.model_name}:{self.record_id}"


class OfflinePackage(models.Model):
    """
    Pre-packaged content for offline use.
    """

    class Status(models.TextChoices):
        BUILDING = "building", _("Construyendo")
        READY = "ready", _("Listo")
        OUTDATED = "outdated", _("Desactualizado")
        ERROR = "error", _("Error")

    name = models.CharField(_("Nombre"), max_length=200)
    description = models.TextField(_("Descripción"), blank=True)
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="offline_packages",
        verbose_name=_("Curso"),
    )
    version = models.PositiveIntegerField(_("Versión"), default=1)
    status = models.CharField(
        _("Estado"),
        max_length=20,
        choices=Status.choices,
        default=Status.BUILDING,
    )
    package_file = models.FileField(
        _("Archivo del paquete"),
        upload_to="offline_packages/",
        blank=True,
        null=True,
    )
    file_size = models.PositiveBigIntegerField(
        _("Tamaño del archivo"),
        null=True,
        blank=True,
    )
    checksum = models.CharField(
        _("Checksum"),
        max_length=64,
        blank=True,
    )
    includes_videos = models.BooleanField(
        _("Incluye videos"),
        default=True,
    )
    includes_documents = models.BooleanField(
        _("Incluye documentos"),
        default=True,
    )
    includes_assessments = models.BooleanField(
        _("Incluye evaluaciones"),
        default=True,
    )
    manifest = models.JSONField(
        _("Manifiesto"),
        default=dict,
        blank=True,
        help_text=_("Lista de contenidos incluidos"),
    )
    build_started_at = models.DateTimeField(
        _("Inicio de construcción"),
        null=True,
        blank=True,
    )
    build_completed_at = models.DateTimeField(
        _("Fin de construcción"),
        null=True,
        blank=True,
    )
    error_message = models.TextField(_("Mensaje de error"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "offline_packages"
        verbose_name = _("Paquete offline")
        verbose_name_plural = _("Paquetes offline")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.course.title} v{self.version}"


class PackageDownload(models.Model):
    """
    Track package downloads by users.
    """

    package = models.ForeignKey(
        OfflinePackage,
        on_delete=models.CASCADE,
        related_name="downloads",
        verbose_name=_("Paquete"),
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="package_downloads",
        verbose_name=_("Usuario"),
    )
    device_id = models.CharField(
        _("ID del dispositivo"),
        max_length=100,
    )
    downloaded_at = models.DateTimeField(
        _("Fecha de descarga"),
        auto_now_add=True,
    )
    download_completed = models.BooleanField(
        _("Descarga completada"),
        default=False,
    )
    last_accessed_at = models.DateTimeField(
        _("Último acceso"),
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "package_downloads"
        verbose_name = _("Descarga de paquete")
        verbose_name_plural = _("Descargas de paquete")

    def __str__(self):
        return f"{self.user} - {self.package}"
