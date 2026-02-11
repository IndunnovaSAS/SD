"""
Notification models for SD LMS.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.validators import validate_url


class NotificationManager(models.Manager):
    """Custom manager for Notification model."""

    def unread(self):
        return self.filter(status="unread")

    def for_user(self, user):
        return self.filter(user=user)


class NotificationTemplate(models.Model):
    """
    Template for notification messages.
    """

    class Channel(models.TextChoices):
        EMAIL = "email", _("Email")
        PUSH = "push", _("Push")
        SMS = "sms", _("SMS")
        IN_APP = "in_app", _("En la aplicación")

    name = models.CharField(_("Nombre"), max_length=100, unique=True)
    description = models.TextField(_("Descripción"), blank=True)
    subject = models.CharField(
        _("Asunto"),
        max_length=200,
        help_text=_("Asunto del email o título de la notificación"),
    )
    body = models.TextField(
        _("Cuerpo"),
        help_text=_("Contenido de la notificación. Usa {{variable}} para variables"),
    )
    html_body = models.TextField(
        _("Cuerpo HTML"),
        blank=True,
        help_text=_("Versión HTML del contenido para emails"),
    )
    channel = models.CharField(
        _("Canal"),
        max_length=20,
        choices=Channel.choices,
        default=Channel.IN_APP,
    )
    is_active = models.BooleanField(_("Activo"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_templates"
        verbose_name = _("Plantilla de notificación")
        verbose_name_plural = _("Plantillas de notificación")

    def __str__(self):
        return self.name


class Notification(models.Model):
    """
    Notification instance sent to a user.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pendiente")
        SENT = "sent", _("Enviado")
        DELIVERED = "delivered", _("Entregado")
        READ = "read", _("Leído")
        FAILED = "failed", _("Fallido")

    class Priority(models.TextChoices):
        LOW = "low", _("Baja")
        NORMAL = "normal", _("Normal")
        HIGH = "high", _("Alta")
        URGENT = "urgent", _("Urgente")

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Usuario"),
    )
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("Plantilla"),
    )
    channel = models.CharField(
        _("Canal"),
        max_length=20,
        choices=NotificationTemplate.Channel.choices,
        default=NotificationTemplate.Channel.IN_APP,
    )
    subject = models.CharField(_("Asunto"), max_length=200)
    body = models.TextField(_("Cuerpo"))
    status = models.CharField(
        _("Estado"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    priority = models.CharField(
        _("Prioridad"),
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    action_url = models.URLField(
        _("URL de acción"),
        blank=True,
        help_text=_("URL a la que dirigir al usuario"),
        validators=[validate_url],
    )
    action_text = models.CharField(
        _("Texto de acción"),
        max_length=100,
        blank=True,
    )
    metadata = models.JSONField(
        _("Metadatos"),
        default=dict,
        blank=True,
    )
    sent_at = models.DateTimeField(_("Fecha de envío"), null=True, blank=True)
    delivered_at = models.DateTimeField(_("Fecha de entrega"), null=True, blank=True)
    read_at = models.DateTimeField(_("Fecha de lectura"), null=True, blank=True)
    error_message = models.TextField(_("Mensaje de error"), blank=True)
    retry_count = models.PositiveIntegerField(_("Intentos"), default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = NotificationManager()

    class Meta:
        db_table = "notifications"
        verbose_name = _("Notificación")
        verbose_name_plural = _("Notificaciones")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["-created_at", "user"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.subject}"


class UserNotificationPreference(models.Model):
    """
    User preferences for notifications.
    """

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="notification_preferences",
        verbose_name=_("Usuario"),
    )
    email_enabled = models.BooleanField(_("Email habilitado"), default=True)
    push_enabled = models.BooleanField(_("Push habilitado"), default=True)
    sms_enabled = models.BooleanField(_("SMS habilitado"), default=False)
    in_app_enabled = models.BooleanField(_("En app habilitado"), default=True)

    # Specific notification types
    course_reminders = models.BooleanField(
        _("Recordatorios de cursos"),
        default=True,
    )
    assessment_results = models.BooleanField(
        _("Resultados de evaluaciones"),
        default=True,
    )
    certificate_issued = models.BooleanField(
        _("Certificados emitidos"),
        default=True,
    )
    new_assignments = models.BooleanField(
        _("Nuevas asignaciones"),
        default=True,
    )
    deadline_reminders = models.BooleanField(
        _("Recordatorios de fecha límite"),
        default=True,
    )
    lesson_learned_updates = models.BooleanField(
        _("Actualizaciones de lecciones aprendidas"),
        default=True,
    )

    quiet_hours_start = models.TimeField(
        _("Inicio de horas silenciosas"),
        null=True,
        blank=True,
    )
    quiet_hours_end = models.TimeField(
        _("Fin de horas silenciosas"),
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_notification_preferences"
        verbose_name = _("Preferencia de notificación")
        verbose_name_plural = _("Preferencias de notificación")

    def __str__(self):
        return f"Preferencias de {self.user}"


class PushSubscription(models.Model):
    """
    Push notification subscription for a user device.
    """

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        verbose_name=_("Usuario"),
    )
    endpoint = models.URLField(_("Endpoint"))
    p256dh_key = models.CharField(_("Clave P256DH"), max_length=255)
    auth_key = models.CharField(_("Clave de autenticación"), max_length=255)
    device_name = models.CharField(_("Nombre del dispositivo"), max_length=100, blank=True)
    device_type = models.CharField(_("Tipo de dispositivo"), max_length=50, blank=True)
    is_active = models.BooleanField(_("Activo"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(_("Último uso"), auto_now=True)

    class Meta:
        db_table = "push_subscriptions"
        verbose_name = _("Suscripción push")
        verbose_name_plural = _("Suscripciones push")

    def __str__(self):
        return f"{self.user} - {self.device_name or 'Unknown'}"
