"""
Pre-operational talks models for SD LMS.
"""

from django.contrib.postgres.fields import ArrayField
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
    key_points = ArrayField(
        models.TextField(),
        verbose_name=_("Puntos clave"),
        default=list,
    )
    safety_topics = ArrayField(
        models.CharField(max_length=200),
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
    target_activities = ArrayField(
        models.CharField(max_length=100),
        verbose_name=_("Actividades objetivo"),
        default=list,
        help_text=_("Tipos de actividades para las que aplica"),
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
    key_points = ArrayField(
        models.TextField(),
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
