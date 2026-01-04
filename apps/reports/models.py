"""
Reports and analytics models for SD LMS.
"""

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _


class ReportTemplate(models.Model):
    """
    Template for generating reports.
    """

    class Type(models.TextChoices):
        TRAINING = "training", _("Capacitación")
        COMPLIANCE = "compliance", _("Cumplimiento")
        ASSESSMENT = "assessment", _("Evaluaciones")
        CERTIFICATION = "certification", _("Certificaciones")
        PROGRESS = "progress", _("Progreso")
        CUSTOM = "custom", _("Personalizado")

    class Format(models.TextChoices):
        PDF = "pdf", _("PDF")
        EXCEL = "excel", _("Excel")
        CSV = "csv", _("CSV")
        HTML = "html", _("HTML")

    name = models.CharField(_("Nombre"), max_length=200)
    description = models.TextField(_("Descripción"), blank=True)
    report_type = models.CharField(
        _("Tipo"),
        max_length=20,
        choices=Type.choices,
    )
    default_format = models.CharField(
        _("Formato por defecto"),
        max_length=20,
        choices=Format.choices,
        default=Format.PDF,
    )
    template_file = models.FileField(
        _("Archivo de plantilla"),
        upload_to="reports/templates/",
        blank=True,
        null=True,
    )
    query_definition = models.JSONField(
        _("Definición de consulta"),
        default=dict,
        help_text=_("Definición de filtros y datos del reporte"),
    )
    columns = models.JSONField(
        _("Columnas"),
        default=list,
        help_text=_("Definición de columnas del reporte"),
    )
    filters = models.JSONField(
        _("Filtros disponibles"),
        default=list,
        help_text=_("Filtros que el usuario puede aplicar"),
    )
    is_active = models.BooleanField(_("Activo"), default=True)
    is_scheduled = models.BooleanField(_("Programable"), default=False)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="report_templates_created",
        verbose_name=_("Creado por"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "report_templates"
        verbose_name = _("Plantilla de reporte")
        verbose_name_plural = _("Plantillas de reporte")

    def __str__(self):
        return self.name


class GeneratedReport(models.Model):
    """
    Generated report instance.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pendiente")
        GENERATING = "generating", _("Generando")
        COMPLETED = "completed", _("Completado")
        FAILED = "failed", _("Fallido")

    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name="generated_reports",
        verbose_name=_("Plantilla"),
    )
    name = models.CharField(_("Nombre"), max_length=200)
    format = models.CharField(
        _("Formato"),
        max_length=20,
        choices=ReportTemplate.Format.choices,
    )
    status = models.CharField(
        _("Estado"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    filters_applied = models.JSONField(
        _("Filtros aplicados"),
        default=dict,
    )
    file = models.FileField(
        _("Archivo"),
        upload_to="reports/generated/",
        blank=True,
        null=True,
    )
    file_size = models.PositiveBigIntegerField(
        _("Tamaño del archivo"),
        null=True,
        blank=True,
    )
    row_count = models.PositiveIntegerField(
        _("Número de filas"),
        null=True,
        blank=True,
    )
    generation_started_at = models.DateTimeField(
        _("Inicio de generación"),
        null=True,
        blank=True,
    )
    generation_completed_at = models.DateTimeField(
        _("Fin de generación"),
        null=True,
        blank=True,
    )
    error_message = models.TextField(_("Mensaje de error"), blank=True)
    generated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="reports_generated",
        verbose_name=_("Generado por"),
    )
    expires_at = models.DateTimeField(
        _("Fecha de expiración"),
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "generated_reports"
        verbose_name = _("Reporte generado")
        verbose_name_plural = _("Reportes generados")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.created_at}"


class ScheduledReport(models.Model):
    """
    Scheduled report configuration.
    """

    class Frequency(models.TextChoices):
        DAILY = "daily", _("Diario")
        WEEKLY = "weekly", _("Semanal")
        BIWEEKLY = "biweekly", _("Quincenal")
        MONTHLY = "monthly", _("Mensual")
        QUARTERLY = "quarterly", _("Trimestral")

    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name="schedules",
        verbose_name=_("Plantilla"),
    )
    name = models.CharField(_("Nombre"), max_length=200)
    frequency = models.CharField(
        _("Frecuencia"),
        max_length=20,
        choices=Frequency.choices,
    )
    format = models.CharField(
        _("Formato"),
        max_length=20,
        choices=ReportTemplate.Format.choices,
    )
    filters = models.JSONField(
        _("Filtros"),
        default=dict,
    )
    recipients = ArrayField(
        models.EmailField(),
        verbose_name=_("Destinatarios"),
        default=list,
    )
    day_of_week = models.PositiveSmallIntegerField(
        _("Día de la semana"),
        null=True,
        blank=True,
        help_text=_("0=Lunes, 6=Domingo"),
    )
    day_of_month = models.PositiveSmallIntegerField(
        _("Día del mes"),
        null=True,
        blank=True,
    )
    time_of_day = models.TimeField(
        _("Hora del día"),
        help_text=_("Hora a la que se genera el reporte"),
    )
    is_active = models.BooleanField(_("Activo"), default=True)
    last_run_at = models.DateTimeField(
        _("Última ejecución"),
        null=True,
        blank=True,
    )
    next_run_at = models.DateTimeField(
        _("Próxima ejecución"),
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="scheduled_reports_created",
        verbose_name=_("Creado por"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scheduled_reports"
        verbose_name = _("Reporte programado")
        verbose_name_plural = _("Reportes programados")

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"


class Dashboard(models.Model):
    """
    Custom dashboard configuration.
    """

    name = models.CharField(_("Nombre"), max_length=200)
    description = models.TextField(_("Descripción"), blank=True)
    is_default = models.BooleanField(_("Por defecto"), default=False)
    layout = models.JSONField(
        _("Layout"),
        default=dict,
        help_text=_("Configuración del layout del dashboard"),
    )
    widgets = models.JSONField(
        _("Widgets"),
        default=list,
        help_text=_("Lista de widgets del dashboard"),
    )
    is_active = models.BooleanField(_("Activo"), default=True)
    is_public = models.BooleanField(_("Público"), default=False)
    allowed_roles = ArrayField(
        models.CharField(max_length=50),
        verbose_name=_("Roles permitidos"),
        default=list,
        blank=True,
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="dashboards_created",
        verbose_name=_("Creado por"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dashboards"
        verbose_name = _("Dashboard")
        verbose_name_plural = _("Dashboards")

    def __str__(self):
        return self.name


class UserDashboard(models.Model):
    """
    User's selected dashboard.
    """

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="dashboard_preference",
        verbose_name=_("Usuario"),
    )
    dashboard = models.ForeignKey(
        Dashboard,
        on_delete=models.SET_NULL,
        null=True,
        related_name="user_selections",
        verbose_name=_("Dashboard"),
    )
    custom_widgets = models.JSONField(
        _("Widgets personalizados"),
        default=list,
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_dashboards"
        verbose_name = _("Dashboard de usuario")
        verbose_name_plural = _("Dashboards de usuario")

    def __str__(self):
        return f"{self.user} - {self.dashboard}"
