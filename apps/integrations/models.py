"""
Integration models for SD LMS.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class ExternalSystem(models.Model):
    """
    Configuration for external system integration.
    """

    class Type(models.TextChoices):
        HR = "hr", _("Recursos Humanos")
        ERP = "erp", _("ERP")
        OPERATIONS = "operations", _("Operaciones")
        SSO = "sso", _("Single Sign-On")
        SCORM = "scorm", _("SCORM")
        API = "api", _("API Externa")
        WEBHOOK = "webhook", _("Webhook")

    class Status(models.TextChoices):
        ACTIVE = "active", _("Activo")
        INACTIVE = "inactive", _("Inactivo")
        ERROR = "error", _("Error")
        MAINTENANCE = "maintenance", _("Mantenimiento")

    name = models.CharField(_("Nombre"), max_length=200)
    code = models.CharField(_("Código"), max_length=50, unique=True)
    system_type = models.CharField(
        _("Tipo"),
        max_length=20,
        choices=Type.choices,
    )
    description = models.TextField(_("Descripción"), blank=True)
    base_url = models.URLField(
        _("URL base"),
        blank=True,
    )
    api_version = models.CharField(
        _("Versión de API"),
        max_length=20,
        blank=True,
    )
    auth_type = models.CharField(
        _("Tipo de autenticación"),
        max_length=50,
        blank=True,
        help_text=_("basic, bearer, oauth2, api_key, etc."),
    )
    credentials = models.JSONField(
        _("Credenciales"),
        default=dict,
        blank=True,
        help_text=_("Credenciales encriptadas"),
    )
    headers = models.JSONField(
        _("Headers adicionales"),
        default=dict,
        blank=True,
    )
    settings = models.JSONField(
        _("Configuración"),
        default=dict,
        blank=True,
    )
    status = models.CharField(
        _("Estado"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    last_sync_at = models.DateTimeField(
        _("Última sincronización"),
        null=True,
        blank=True,
    )
    last_error = models.TextField(_("Último error"), blank=True)
    is_active = models.BooleanField(_("Activo"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "external_systems"
        verbose_name = _("Sistema externo")
        verbose_name_plural = _("Sistemas externos")

    def __str__(self):
        return self.name


class IntegrationLog(models.Model):
    """
    Log of integration operations.
    """

    class Direction(models.TextChoices):
        INBOUND = "inbound", _("Entrante")
        OUTBOUND = "outbound", _("Saliente")

    class Status(models.TextChoices):
        SUCCESS = "success", _("Exitoso")
        ERROR = "error", _("Error")
        PARTIAL = "partial", _("Parcial")

    external_system = models.ForeignKey(
        ExternalSystem,
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name=_("Sistema externo"),
    )
    operation = models.CharField(
        _("Operación"),
        max_length=100,
    )
    direction = models.CharField(
        _("Dirección"),
        max_length=20,
        choices=Direction.choices,
    )
    status = models.CharField(
        _("Estado"),
        max_length=20,
        choices=Status.choices,
    )
    request_data = models.JSONField(
        _("Datos de solicitud"),
        default=dict,
        blank=True,
    )
    response_data = models.JSONField(
        _("Datos de respuesta"),
        default=dict,
        blank=True,
    )
    http_status = models.PositiveSmallIntegerField(
        _("Código HTTP"),
        null=True,
        blank=True,
    )
    duration_ms = models.PositiveIntegerField(
        _("Duración (ms)"),
        null=True,
        blank=True,
    )
    error_message = models.TextField(_("Mensaje de error"), blank=True)
    records_processed = models.PositiveIntegerField(
        _("Registros procesados"),
        default=0,
    )
    records_failed = models.PositiveIntegerField(
        _("Registros fallidos"),
        default=0,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "integration_logs"
        verbose_name = _("Log de integración")
        verbose_name_plural = _("Logs de integración")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.external_system} - {self.operation} - {self.created_at}"


class DataMapping(models.Model):
    """
    Field mapping between external systems and LMS.
    """

    external_system = models.ForeignKey(
        ExternalSystem,
        on_delete=models.CASCADE,
        related_name="mappings",
        verbose_name=_("Sistema externo"),
    )
    entity_type = models.CharField(
        _("Tipo de entidad"),
        max_length=100,
        help_text=_("Ej: user, course, enrollment"),
    )
    external_field = models.CharField(
        _("Campo externo"),
        max_length=200,
    )
    internal_field = models.CharField(
        _("Campo interno"),
        max_length=200,
    )
    transformation = models.CharField(
        _("Transformación"),
        max_length=100,
        blank=True,
        help_text=_("Función de transformación a aplicar"),
    )
    is_required = models.BooleanField(_("Requerido"), default=False)
    default_value = models.CharField(
        _("Valor por defecto"),
        max_length=200,
        blank=True,
    )
    is_active = models.BooleanField(_("Activo"), default=True)

    class Meta:
        db_table = "data_mappings"
        verbose_name = _("Mapeo de datos")
        verbose_name_plural = _("Mapeos de datos")
        unique_together = [["external_system", "entity_type", "external_field"]]

    def __str__(self):
        return f"{self.external_system} - {self.external_field} -> {self.internal_field}"


class Webhook(models.Model):
    """
    Webhook configuration for external notifications.
    """

    class Event(models.TextChoices):
        USER_CREATED = "user_created", _("Usuario creado")
        USER_UPDATED = "user_updated", _("Usuario actualizado")
        ENROLLMENT_CREATED = "enrollment_created", _("Inscripción creada")
        COURSE_COMPLETED = "course_completed", _("Curso completado")
        CERTIFICATE_ISSUED = "certificate_issued", _("Certificado emitido")
        ASSESSMENT_PASSED = "assessment_passed", _("Evaluación aprobada")
        ASSESSMENT_FAILED = "assessment_failed", _("Evaluación reprobada")

    name = models.CharField(_("Nombre"), max_length=200)
    url = models.URLField(_("URL"))
    events = models.JSONField(
        _("Eventos"),
        default=list,
        help_text=_("Lista de eventos que activan el webhook"),
    )
    secret_key = models.CharField(
        _("Clave secreta"),
        max_length=255,
        blank=True,
        help_text=_("Para firmar las solicitudes"),
    )
    headers = models.JSONField(
        _("Headers adicionales"),
        default=dict,
        blank=True,
    )
    is_active = models.BooleanField(_("Activo"), default=True)
    retry_count = models.PositiveSmallIntegerField(
        _("Reintentos"),
        default=3,
    )
    timeout_seconds = models.PositiveSmallIntegerField(
        _("Timeout (segundos)"),
        default=30,
    )
    last_triggered_at = models.DateTimeField(
        _("Última ejecución"),
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="webhooks_created",
        verbose_name=_("Creado por"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "webhooks"
        verbose_name = _("Webhook")
        verbose_name_plural = _("Webhooks")

    def __str__(self):
        return self.name


class WebhookDelivery(models.Model):
    """
    Log of webhook delivery attempts.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pendiente")
        SUCCESS = "success", _("Exitoso")
        FAILED = "failed", _("Fallido")
        RETRYING = "retrying", _("Reintentando")

    webhook = models.ForeignKey(
        Webhook,
        on_delete=models.CASCADE,
        related_name="deliveries",
        verbose_name=_("Webhook"),
    )
    event = models.CharField(_("Evento"), max_length=100)
    payload = models.JSONField(_("Payload"))
    status = models.CharField(
        _("Estado"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    http_status = models.PositiveSmallIntegerField(
        _("Código HTTP"),
        null=True,
        blank=True,
    )
    response_body = models.TextField(_("Respuesta"), blank=True)
    attempt_count = models.PositiveSmallIntegerField(
        _("Intentos"),
        default=0,
    )
    next_retry_at = models.DateTimeField(
        _("Próximo reintento"),
        null=True,
        blank=True,
    )
    duration_ms = models.PositiveIntegerField(
        _("Duración (ms)"),
        null=True,
        blank=True,
    )
    error_message = models.TextField(_("Mensaje de error"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(
        _("Fecha de entrega"),
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "webhook_deliveries"
        verbose_name = _("Entrega de webhook")
        verbose_name_plural = _("Entregas de webhook")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.webhook} - {self.event} - {self.status}"
