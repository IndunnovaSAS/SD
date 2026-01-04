"""
Lessons learned models for SD LMS.
"""

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """
    Category for lessons learned.
    """

    name = models.CharField(_("Nombre"), max_length=100)
    description = models.TextField(_("Descripción"), blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Categoría padre"),
    )
    icon = models.CharField(_("Icono"), max_length=50, blank=True)
    order = models.PositiveIntegerField(_("Orden"), default=0)
    is_active = models.BooleanField(_("Activo"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lesson_learned_categories"
        verbose_name = _("Categoría")
        verbose_name_plural = _("Categorías")
        ordering = ["order", "name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class LessonLearned(models.Model):
    """
    Lesson learned from field experience.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", _("Borrador")
        PENDING_REVIEW = "pending_review", _("Pendiente de revisión")
        APPROVED = "approved", _("Aprobado")
        REJECTED = "rejected", _("Rechazado")
        ARCHIVED = "archived", _("Archivado")

    class Severity(models.TextChoices):
        LOW = "low", _("Bajo")
        MEDIUM = "medium", _("Medio")
        HIGH = "high", _("Alto")
        CRITICAL = "critical", _("Crítico")

    class Type(models.TextChoices):
        INCIDENT = "incident", _("Incidente")
        NEAR_MISS = "near_miss", _("Casi accidente")
        GOOD_PRACTICE = "good_practice", _("Buena práctica")
        IMPROVEMENT = "improvement", _("Mejora")
        OBSERVATION = "observation", _("Observación")

    title = models.CharField(_("Título"), max_length=300)
    description = models.TextField(_("Descripción"))
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="lessons_learned",
        verbose_name=_("Categoría"),
    )
    lesson_type = models.CharField(
        _("Tipo"),
        max_length=20,
        choices=Type.choices,
        default=Type.OBSERVATION,
    )
    severity = models.CharField(
        _("Severidad"),
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )
    status = models.CharField(
        _("Estado"),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    situation = models.TextField(
        _("Situación"),
        help_text=_("Descripción de la situación o contexto"),
    )
    root_cause = models.TextField(
        _("Causa raíz"),
        blank=True,
        help_text=_("Análisis de la causa raíz"),
    )
    lesson = models.TextField(
        _("Lección"),
        help_text=_("La lección aprendida"),
    )
    recommendations = models.TextField(
        _("Recomendaciones"),
        help_text=_("Acciones recomendadas"),
    )
    location = models.CharField(
        _("Ubicación"),
        max_length=200,
        blank=True,
        help_text=_("Proyecto, línea o sitio donde ocurrió"),
    )
    date_occurred = models.DateField(
        _("Fecha del evento"),
        null=True,
        blank=True,
    )
    tags = ArrayField(
        models.CharField(max_length=50),
        verbose_name=_("Etiquetas"),
        default=list,
        blank=True,
    )
    target_profiles = ArrayField(
        models.CharField(max_length=50),
        verbose_name=_("Perfiles objetivo"),
        default=list,
        blank=True,
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="lessons_learned_created",
        verbose_name=_("Creado por"),
    )
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lessons_learned_reviewed",
        verbose_name=_("Revisado por"),
    )
    reviewed_at = models.DateTimeField(
        _("Fecha de revisión"),
        null=True,
        blank=True,
    )
    review_notes = models.TextField(_("Notas de revisión"), blank=True)
    view_count = models.PositiveIntegerField(_("Vistas"), default=0)
    is_featured = models.BooleanField(_("Destacado"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lessons_learned"
        verbose_name = _("Lección aprendida")
        verbose_name_plural = _("Lecciones aprendidas")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class LessonAttachment(models.Model):
    """
    Attachment for a lesson learned.
    """

    class Type(models.TextChoices):
        IMAGE = "image", _("Imagen")
        VIDEO = "video", _("Video")
        DOCUMENT = "document", _("Documento")
        OTHER = "other", _("Otro")

    lesson_learned = models.ForeignKey(
        LessonLearned,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name=_("Lección aprendida"),
    )
    file = models.FileField(
        _("Archivo"),
        upload_to="lessons_learned/attachments/",
    )
    file_type = models.CharField(
        _("Tipo"),
        max_length=20,
        choices=Type.choices,
        default=Type.DOCUMENT,
    )
    original_name = models.CharField(_("Nombre original"), max_length=255)
    description = models.CharField(_("Descripción"), max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lesson_attachments"
        verbose_name = _("Adjunto")
        verbose_name_plural = _("Adjuntos")

    def __str__(self):
        return self.original_name


class LessonComment(models.Model):
    """
    Comment on a lesson learned.
    """

    lesson_learned = models.ForeignKey(
        LessonLearned,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("Lección aprendida"),
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="lesson_comments",
        verbose_name=_("Usuario"),
    )
    content = models.TextField(_("Contenido"))
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        verbose_name=_("Respuesta a"),
    )
    is_approved = models.BooleanField(_("Aprobado"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lesson_comments"
        verbose_name = _("Comentario")
        verbose_name_plural = _("Comentarios")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user} - {self.lesson_learned}"
