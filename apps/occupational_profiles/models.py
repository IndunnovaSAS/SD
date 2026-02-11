"""
Occupational profile models for SD LMS.

Implements PER-01 and PER-02: Module for managing occupational profiles
and linking them to learning paths.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class OccupationalProfile(models.Model):
    """
    Occupational profile defining job roles and their required training.

    Each profile can be linked to multiple learning paths that users
    with this profile must complete.
    """

    class Country(models.TextChoices):
        COLOMBIA = "CO", _("Colombia")
        PANAMA = "PA", _("Panamá")
        PERU = "PE", _("Perú")

    name = models.CharField(
        _("Nombre"),
        max_length=100,
        help_text=_("Ej: Liniero, Técnico Electricista"),
    )
    code = models.CharField(
        _("Código"),
        max_length=20,
        unique=True,
        help_text=_("Código único del perfil"),
    )
    description = models.TextField(
        _("Descripción"),
        blank=True,
    )
    country = models.CharField(
        _("País"),
        max_length=2,
        choices=Country.choices,
        default=Country.COLOMBIA,
        help_text=_("País donde aplica este perfil"),
    )
    learning_paths = models.ManyToManyField(
        "learning_paths.LearningPath",
        blank=True,
        related_name="occupational_profiles",
        verbose_name=_("Rutas de aprendizaje"),
        help_text=_("Rutas de aprendizaje obligatorias para este perfil"),
    )
    is_operational = models.BooleanField(
        _("Personal operativo"),
        default=True,
        help_text=_("Si es personal operativo (autenticación con cédula)"),
    )
    is_active = models.BooleanField(
        _("Activo"),
        default=True,
    )
    order = models.PositiveIntegerField(
        _("Orden"),
        default=0,
        help_text=_("Orden de visualización"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "occupational_profiles"
        verbose_name = _("Perfil ocupacional")
        verbose_name_plural = _("Perfiles ocupacionales")
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_mandatory_courses(self):
        """Get all mandatory courses from linked learning paths."""
        from apps.courses.models import Course

        course_ids = []
        for path in self.learning_paths.filter(status="active"):
            for path_course in path.path_courses.filter(is_required=True):
                course_ids.append(path_course.course_id)
        return Course.objects.filter(id__in=course_ids).distinct()


class UserOccupationalProfile(models.Model):
    """
    Assignment of occupational profile to a user.

    Tracks when a user is assigned a profile and who assigned it.
    """

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="occupational_profile_assignments",
        verbose_name=_("Usuario"),
    )
    profile = models.ForeignKey(
        OccupationalProfile,
        on_delete=models.CASCADE,
        related_name="user_assignments",
        verbose_name=_("Perfil"),
    )
    assigned_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="profile_assignments_made",
        verbose_name=_("Asignado por"),
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(
        _("Activo"),
        default=True,
        help_text=_("Si esta asignación está activa"),
    )
    notes = models.TextField(
        _("Notas"),
        blank=True,
    )

    class Meta:
        db_table = "user_occupational_profiles"
        verbose_name = _("Asignación de perfil")
        verbose_name_plural = _("Asignaciones de perfil")
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.user} - {self.profile}"

    def save(self, *args, **kwargs):
        # Deactivate previous active assignments for this user
        if self.is_active:
            UserOccupationalProfile.objects.filter(
                user=self.user,
                is_active=True,
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
