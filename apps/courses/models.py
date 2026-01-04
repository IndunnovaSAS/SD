"""
Course and content models for SD LMS.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Course(models.Model):
    """
    Course model representing a training course.
    """

    class Type(models.TextChoices):
        MANDATORY = "mandatory", _("Obligatorio")
        OPTIONAL = "optional", _("Opcional")
        REFRESHER = "refresher", _("Refuerzo")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Borrador")
        PUBLISHED = "published", _("Publicado")
        ARCHIVED = "archived", _("Archivado")

    class RiskLevel(models.TextChoices):
        LOW = "low", _("Bajo")
        MEDIUM = "medium", _("Medio")
        HIGH = "high", _("Alto")
        CRITICAL = "critical", _("Crítico")

    code = models.CharField(_("Código"), max_length=50, unique=True)
    title = models.CharField(_("Título"), max_length=200)
    description = models.TextField(_("Descripción"))
    objectives = models.TextField(_("Objetivos"), blank=True)
    duration = models.PositiveIntegerField(
        _("Duración (minutos)"),
        help_text=_("Duración estimada en minutos"),
    )
    course_type = models.CharField(
        _("Tipo"),
        max_length=20,
        choices=Type.choices,
        default=Type.MANDATORY,
    )
    risk_level = models.CharField(
        _("Nivel de riesgo"),
        max_length=20,
        choices=RiskLevel.choices,
        default=RiskLevel.MEDIUM,
    )
    thumbnail = models.ImageField(
        _("Imagen miniatura"),
        upload_to="courses/thumbnails/",
        blank=True,
        null=True,
    )
    status = models.CharField(
        _("Estado"),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    version = models.PositiveIntegerField(_("Versión"), default=1)
    target_profiles = models.JSONField(
        verbose_name=_("Perfiles objetivo"),
        help_text=_("Lista de perfiles ocupacionales para este curso"),
        default=list,
    )
    prerequisites = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="required_for",
        verbose_name=_("Prerrequisitos"),
    )
    validity_months = models.PositiveIntegerField(
        _("Validez (meses)"),
        null=True,
        blank=True,
        help_text=_("Meses de validez de la certificación (null = sin vencimiento)"),
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="courses_created",
        verbose_name=_("Creado por"),
    )
    published_at = models.DateTimeField(_("Fecha de publicación"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "courses"
        verbose_name = _("Curso")
        verbose_name_plural = _("Cursos")
        ordering = ["title"]

    def __str__(self):
        return f"{self.code} - {self.title}"

    @property
    def total_duration(self):
        """Calculate total duration including all lessons."""
        return sum(lesson.duration for module in self.modules.all() for lesson in module.lessons.all())


class Module(models.Model):
    """
    Course module containing lessons.
    """

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="modules",
        verbose_name=_("Curso"),
    )
    title = models.CharField(_("Título"), max_length=200)
    description = models.TextField(_("Descripción"), blank=True)
    order = models.PositiveIntegerField(_("Orden"), default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "modules"
        verbose_name = _("Módulo")
        verbose_name_plural = _("Módulos")
        ordering = ["order"]
        unique_together = ["course", "order"]

    def __str__(self):
        return f"{self.course.code} - {self.title}"


class Lesson(models.Model):
    """
    Individual lesson within a module.
    """

    class Type(models.TextChoices):
        VIDEO = "video", _("Video")
        PDF = "pdf", _("PDF")
        SCORM = "scorm", _("SCORM")
        INTERACTIVE = "interactive", _("Interactivo")
        AUDIO = "audio", _("Audio")
        QUIZ = "quiz", _("Quiz")
        TEXT = "text", _("Texto")

    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="lessons",
        verbose_name=_("Módulo"),
    )
    title = models.CharField(_("Título"), max_length=200)
    description = models.TextField(_("Descripción"), blank=True)
    lesson_type = models.CharField(
        _("Tipo"),
        max_length=20,
        choices=Type.choices,
    )
    content = models.TextField(_("Contenido"), blank=True, help_text=_("Contenido HTML o texto"))
    content_file = models.FileField(
        _("Archivo de contenido"),
        upload_to="courses/content/",
        blank=True,
        null=True,
    )
    video_url = models.URLField(_("URL del video"), blank=True)
    duration = models.PositiveIntegerField(_("Duración (minutos)"), default=0)
    order = models.PositiveIntegerField(_("Orden"), default=0)
    is_mandatory = models.BooleanField(_("Obligatorio"), default=True)
    is_offline_available = models.BooleanField(_("Disponible offline"), default=True)
    metadata = models.JSONField(_("Metadatos"), default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lessons"
        verbose_name = _("Lección")
        verbose_name_plural = _("Lecciones")
        ordering = ["order"]

    def __str__(self):
        return f"{self.module.title} - {self.title}"


class MediaAsset(models.Model):
    """
    Media files used in courses.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pendiente")
        PROCESSING = "processing", _("Procesando")
        READY = "ready", _("Listo")
        ERROR = "error", _("Error")

    class Type(models.TextChoices):
        VIDEO = "video", _("Video")
        AUDIO = "audio", _("Audio")
        IMAGE = "image", _("Imagen")
        DOCUMENT = "document", _("Documento")
        SCORM = "scorm", _("Paquete SCORM")

    filename = models.CharField(_("Nombre de archivo"), max_length=255)
    original_name = models.CharField(_("Nombre original"), max_length=255)
    file = models.FileField(_("Archivo"), upload_to="media_assets/")
    file_type = models.CharField(_("Tipo"), max_length=20, choices=Type.choices)
    mime_type = models.CharField(_("MIME type"), max_length=100)
    size = models.PositiveBigIntegerField(_("Tamaño (bytes)"))
    thumbnail = models.ImageField(
        _("Miniatura"),
        upload_to="media_assets/thumbnails/",
        blank=True,
        null=True,
    )
    compressed_file = models.FileField(
        _("Archivo comprimido (offline)"),
        upload_to="media_assets/offline/",
        blank=True,
        null=True,
    )
    status = models.CharField(
        _("Estado"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    processing_error = models.TextField(_("Error de procesamiento"), blank=True)
    duration = models.PositiveIntegerField(_("Duración (segundos)"), null=True, blank=True)
    metadata = models.JSONField(_("Metadatos"), default=dict, blank=True)
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_assets",
        verbose_name=_("Subido por"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "media_assets"
        verbose_name = _("Recurso multimedia")
        verbose_name_plural = _("Recursos multimedia")
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_name


class Enrollment(models.Model):
    """
    User enrollment in a course.
    """

    class Status(models.TextChoices):
        ENROLLED = "enrolled", _("Inscrito")
        IN_PROGRESS = "in_progress", _("En progreso")
        COMPLETED = "completed", _("Completado")
        EXPIRED = "expired", _("Vencido")
        DROPPED = "dropped", _("Abandonado")

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name=_("Usuario"),
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name=_("Curso"),
    )
    status = models.CharField(
        _("Estado"),
        max_length=20,
        choices=Status.choices,
        default=Status.ENROLLED,
    )
    progress = models.DecimalField(
        _("Progreso (%)"),
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    started_at = models.DateTimeField(_("Fecha de inicio"), null=True, blank=True)
    completed_at = models.DateTimeField(_("Fecha de completado"), null=True, blank=True)
    due_date = models.DateField(_("Fecha límite"), null=True, blank=True)
    assigned_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="enrollments_assigned",
        verbose_name=_("Asignado por"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "enrollments"
        verbose_name = _("Inscripción")
        verbose_name_plural = _("Inscripciones")
        unique_together = ["user", "course"]

    def __str__(self):
        return f"{self.user} - {self.course}"


class LessonProgress(models.Model):
    """
    Track user progress on individual lessons.
    """

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
        verbose_name=_("Inscripción"),
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="user_progress",
        verbose_name=_("Lección"),
    )
    is_completed = models.BooleanField(_("Completado"), default=False)
    progress_percent = models.DecimalField(
        _("Progreso (%)"),
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    time_spent = models.PositiveIntegerField(
        _("Tiempo empleado (segundos)"),
        default=0,
    )
    last_position = models.JSONField(
        _("Última posición"),
        default=dict,
        blank=True,
        help_text=_("Posición del video/contenido para continuar"),
    )
    completed_at = models.DateTimeField(_("Fecha de completado"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lesson_progress"
        verbose_name = _("Progreso de lección")
        verbose_name_plural = _("Progreso de lecciones")
        unique_together = ["enrollment", "lesson"]

    def __str__(self):
        return f"{self.enrollment.user} - {self.lesson}"
