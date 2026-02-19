"""
Pre-operational talks models for SD LMS.
"""

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class TalkTemplate(models.Model):
    """
    Template for pre-operational talks.
    """

    class Type(models.TextChoices):
        DAILY = "daily", _("Diario")
        WEEKLY = "weekly", _("Semanal")
        SPECIAL = "special", _("Especial")
        EMERGENCY = "emergency", _("Emergencia")

    title = models.CharField(_("Título"), max_length=200)
    description = models.TextField(_("Descripción"))
    talk_type = models.CharField(
        _("Tipo"),
        max_length=20,
        choices=Type.choices,
        default=Type.DAILY,
    )
    content = models.TextField(_("Contenido"))
    key_points = models.JSONField(
        verbose_name=_("Puntos clave"),
        default=list,
    )
    safety_topics = models.JSONField(
        verbose_name=_("Temas de seguridad"),
        default=list,
    )
    estimated_duration = models.PositiveIntegerField(
        _("Duración estimada (minutos)"),
        default=15,
    )
    requires_signature = models.BooleanField(
        _("Requiere firma"),
        default=True,
    )
    target_activities = models.JSONField(
        verbose_name=_("Actividades objetivo"),
        default=list,
        help_text=_("Tipos de actividades para las que aplica"),
    )
    recurrence_months = models.PositiveIntegerField(
        _("Recurrencia (meses)"),
        default=2,
        help_text=_("Cada cuántos meses se recicla esta plantilla"),
    )
    is_active = models.BooleanField(_("Activo"), default=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="talk_templates_created",
        verbose_name=_("Creado por"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "talk_templates"
        verbose_name = _("Plantilla de charla")
        verbose_name_plural = _("Plantillas de charla")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class PreopTalk(models.Model):
    """
    Instance of a pre-operational talk.
    """

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", _("Programada")
        IN_PROGRESS = "in_progress", _("En progreso")
        COMPLETED = "completed", _("Completada")
        CANCELLED = "cancelled", _("Cancelada")

    template = models.ForeignKey(
        TalkTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instances",
        verbose_name=_("Plantilla"),
    )
    title = models.CharField(_("Título"), max_length=200)
    content = models.TextField(_("Contenido"))
    key_points = models.JSONField(
        verbose_name=_("Puntos clave"),
        default=list,
    )
    status = models.CharField(
        _("Estado"),
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )
    project_name = models.CharField(
        _("Nombre del proyecto"),
        max_length=200,
    )
    location = models.CharField(
        _("Ubicación"),
        max_length=300,
    )
    work_activity = models.CharField(
        _("Actividad de trabajo"),
        max_length=200,
    )
    weather_conditions = models.CharField(
        _("Condiciones climáticas"),
        max_length=200,
        blank=True,
    )
    special_risks = models.TextField(
        _("Riesgos especiales"),
        blank=True,
    )
    scheduled_at = models.DateTimeField(_("Fecha programada"))
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
    duration = models.PositiveIntegerField(
        _("Duración (minutos)"),
        null=True,
        blank=True,
    )
    conducted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="talks_conducted",
        verbose_name=_("Realizada por"),
    )
    supervisor = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="talks_supervised",
        verbose_name=_("Supervisor"),
    )
    notes = models.TextField(_("Notas"), blank=True)
    gps_latitude = models.DecimalField(
        _("Latitud GPS"),
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    gps_longitude = models.DecimalField(
        _("Longitud GPS"),
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "preop_talks"
        verbose_name = _("Charla pre-operacional")
        verbose_name_plural = _("Charlas pre-operacionales")
        ordering = ["-scheduled_at"]

    def __str__(self):
        return f"{self.title} - {self.scheduled_at.date()}"

    @property
    def attendee_count(self):
        return self.attendees.count()

    @property
    def signed_attendees_count(self):
        return self.attendees.filter(signed_at__isnull=False).count()


class TalkAttendee(models.Model):
    """
    Attendee of a pre-operational talk.
    """

    talk = models.ForeignKey(
        PreopTalk,
        on_delete=models.CASCADE,
        related_name="attendees",
        verbose_name=_("Charla"),
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="talk_attendances",
        verbose_name=_("Usuario"),
    )
    signature = models.ImageField(
        _("Firma"),
        upload_to="talks/signatures/",
        blank=True,
        null=True,
    )
    signed_at = models.DateTimeField(
        _("Fecha de firma"),
        null=True,
        blank=True,
    )
    understood_content = models.BooleanField(
        _("Entendió el contenido"),
        default=True,
    )
    comments = models.TextField(
        _("Comentarios"),
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "talk_attendees"
        verbose_name = _("Asistente")
        verbose_name_plural = _("Asistentes")
        unique_together = [["talk", "user"]]

    def __str__(self):
        return f"{self.user} - {self.talk}"


class TalkAttachment(models.Model):
    """
    Attachment for a pre-operational talk.
    """

    talk = models.ForeignKey(
        PreopTalk,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name=_("Charla"),
    )
    file = models.FileField(
        _("Archivo"),
        upload_to="talks/attachments/",
    )
    file_type = models.CharField(_("Tipo"), max_length=50)
    original_name = models.CharField(_("Nombre original"), max_length=255)
    description = models.CharField(_("Descripción"), max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "talk_attachments"
        verbose_name = _("Adjunto")
        verbose_name_plural = _("Adjuntos")

    def __str__(self):
        return self.original_name


class Alert(models.Model):
    """
    Divulgación/alerta con enlace único para verificación de lectura.
    Permite enviar información importante y verificar que fue comprendida.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", _("Borrador")
        ACTIVE = "active", _("Activo")
        EXPIRED = "expired", _("Expirado")
        ARCHIVED = "archived", _("Archivado")

    class Priority(models.TextChoices):
        LOW = "low", _("Baja")
        MEDIUM = "medium", _("Media")
        HIGH = "high", _("Alta")
        CRITICAL = "critical", _("Crítica")

    title = models.CharField(_("Título"), max_length=200)
    content = models.TextField(_("Contenido"))
    unique_link = models.UUIDField(
        _("Enlace único"),
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    status = models.CharField(
        _("Estado"),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    priority = models.CharField(
        _("Prioridad"),
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    attachment = models.FileField(
        _("Archivo adjunto"),
        upload_to="alerts/attachments/%Y/%m/",
        blank=True,
        null=True,
    )
    requires_verification = models.BooleanField(
        _("Requiere verificación"),
        default=True,
        help_text=_("Si el usuario debe responder preguntas para confirmar lectura"),
    )
    target_profiles = models.JSONField(
        verbose_name=_("Perfiles objetivo"),
        default=list,
        blank=True,
        help_text=_("Perfiles ocupacionales que deben ver esta alerta"),
    )
    published_at = models.DateTimeField(
        _("Fecha de publicación"),
        null=True,
        blank=True,
    )
    expires_at = models.DateTimeField(
        _("Fecha de expiración"),
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="alerts_created",
        verbose_name=_("Creado por"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "alerts"
        verbose_name = _("Alerta/Divulgación")
        verbose_name_plural = _("Alertas/Divulgaciones")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_expired(self):
        from django.utils import timezone

        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    @property
    def access_count(self):
        return self.accesses.count()

    @property
    def verified_count(self):
        return self.accesses.filter(verified=True).count()


class AlertVerificationQuestion(models.Model):
    """
    Pregunta de verificación para confirmar comprensión de una alerta.
    Cada alerta puede tener 1-2 preguntas simples.
    """

    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        related_name="verification_questions",
        verbose_name=_("Alerta"),
    )
    question_text = models.CharField(
        _("Pregunta"),
        max_length=500,
    )
    correct_answer = models.CharField(
        _("Respuesta correcta"),
        max_length=200,
        help_text=_("Respuesta esperada para verificar comprensión"),
    )
    order = models.PositiveIntegerField(
        _("Orden"),
        default=0,
    )

    class Meta:
        db_table = "alert_verification_questions"
        verbose_name = _("Pregunta de verificación")
        verbose_name_plural = _("Preguntas de verificación")
        ordering = ["order"]

    def __str__(self):
        return f"{self.alert.title} - Q{self.order + 1}"


class AlertAccess(models.Model):
    """
    Registro de acceso y verificación de una alerta por un usuario.
    """

    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        related_name="accesses",
        verbose_name=_("Alerta"),
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="alert_accesses",
        verbose_name=_("Usuario"),
    )
    accessed_at = models.DateTimeField(
        _("Fecha de acceso"),
        auto_now_add=True,
    )
    verified = models.BooleanField(
        _("Verificado"),
        default=False,
    )
    verified_at = models.DateTimeField(
        _("Fecha de verificación"),
        null=True,
        blank=True,
    )
    answers = models.JSONField(
        verbose_name=_("Respuestas"),
        default=dict,
        blank=True,
        help_text=_("Respuestas a las preguntas de verificación"),
    )
    ip_address = models.GenericIPAddressField(
        _("Dirección IP"),
        null=True,
        blank=True,
    )
    user_agent = models.TextField(
        _("User Agent"),
        blank=True,
    )

    class Meta:
        db_table = "alert_accesses"
        verbose_name = _("Acceso a alerta")
        verbose_name_plural = _("Accesos a alertas")
        unique_together = [["alert", "user"]]

    def __str__(self):
        status = "✓" if self.verified else "○"
        return f"{status} {self.user} - {self.alert}"
