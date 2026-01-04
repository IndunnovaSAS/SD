"""
User and authentication models for SD LMS.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("El email es obligatorio"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser debe tener is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser debe tener is_superuser=True."))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model for SD LMS.

    Uses email as the username field and includes additional fields
    for employee management in high-risk electrical work environments.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", _("Activo")
        INACTIVE = "inactive", _("Inactivo")
        SUSPENDED = "suspended", _("Suspendido")
        PROBATION = "probation", _("Período de Prueba")

    class DocumentType(models.TextChoices):
        CC = "CC", _("Cédula de Ciudadanía")
        CE = "CE", _("Cédula de Extranjería")
        TI = "TI", _("Tarjeta de Identidad")
        PASSPORT = "PA", _("Pasaporte")

    # Remove username field, use email instead
    username = None
    email = models.EmailField(_("Correo electrónico"), unique=True)

    # Personal information
    document_type = models.CharField(
        _("Tipo de documento"),
        max_length=10,
        choices=DocumentType.choices,
        default=DocumentType.CC,
    )
    document_number = models.CharField(
        _("Número de documento"),
        max_length=20,
        unique=True,
    )
    phone = models.CharField(_("Teléfono"), max_length=20, blank=True)
    photo = models.ImageField(
        _("Foto"),
        upload_to="users/photos/",
        blank=True,
        null=True,
    )

    # Employment information
    job_position = models.CharField(_("Cargo"), max_length=100)
    job_profile = models.CharField(
        _("Perfil ocupacional"),
        max_length=50,
        help_text=_("Ej: LINIERO, JEFE_CUADRILLA, INGENIERO_RESIDENTE"),
    )
    work_front = models.CharField(
        _("Frente de trabajo"),
        max_length=100,
        blank=True,
    )
    hire_date = models.DateField(_("Fecha de ingreso"))
    status = models.CharField(
        _("Estado"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    # Emergency contact
    emergency_contact_name = models.CharField(
        _("Contacto de emergencia"),
        max_length=100,
        blank=True,
    )
    emergency_contact_phone = models.CharField(
        _("Teléfono de emergencia"),
        max_length=20,
        blank=True,
    )

    # Metadata
    created_at = models.DateTimeField(_("Fecha de creación"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Fecha de actualización"), auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "document_number", "job_position", "hire_date"]

    class Meta:
        db_table = "users"
        verbose_name = _("Usuario")
        verbose_name_plural = _("Usuarios")
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    @property
    def is_supervisor(self):
        """Check if user has supervisor role."""
        return self.job_profile in ["JEFE_CUADRILLA", "INGENIERO_RESIDENTE", "COORDINADOR_HSEQ"]

    @property
    def can_access_field(self):
        """Check if user has completed required training for field work."""
        # This will be implemented with the certifications app
        return True


class Role(models.Model):
    """
    Custom roles for fine-grained permissions.
    """

    class RoleType(models.TextChoices):
        ADMIN = "admin", _("Administrador")
        SUPERVISOR = "supervisor", _("Supervisor")
        INSTRUCTOR = "instructor", _("Instructor")
        WORKER = "worker", _("Colaborador")
        AUDITOR = "auditor", _("Auditor ISA")

    name = models.CharField(_("Nombre"), max_length=50, unique=True)
    role_type = models.CharField(
        _("Tipo de rol"),
        max_length=20,
        choices=RoleType.choices,
        default=RoleType.WORKER,
    )
    description = models.TextField(_("Descripción"), blank=True)
    permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name=_("Permisos"),
        blank=True,
    )
    users = models.ManyToManyField(
        User,
        through="UserRole",
        through_fields=("role", "user"),
        related_name="custom_roles",
        verbose_name=_("Usuarios"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "roles"
        verbose_name = _("Rol")
        verbose_name_plural = _("Roles")
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserRole(models.Model):
    """
    Through model for User-Role relationship with additional metadata.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_roles",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="role_users",
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="roles_assigned",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "user_roles"
        verbose_name = _("Asignación de rol")
        verbose_name_plural = _("Asignaciones de roles")
        unique_together = ["user", "role"]

    def __str__(self):
        return f"{self.user} - {self.role}"


class Contract(models.Model):
    """
    Contracts with clients (e.g., ISA Intercolombia).
    """

    code = models.CharField(
        _("Código de contrato"),
        max_length=50,
        unique=True,
        help_text=_("Ej: ISA 4620004459"),
    )
    name = models.CharField(_("Nombre"), max_length=200)
    client = models.CharField(_("Cliente"), max_length=100)
    description = models.TextField(_("Descripción"), blank=True)
    start_date = models.DateField(_("Fecha de inicio"))
    end_date = models.DateField(_("Fecha de fin"), null=True, blank=True)
    is_active = models.BooleanField(_("Activo"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contracts"
        verbose_name = _("Contrato")
        verbose_name_plural = _("Contratos")
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class UserContract(models.Model):
    """
    Assignment of users to contracts.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="contracts",
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="users",
    )
    assigned_date = models.DateField(_("Fecha de asignación"))
    end_date = models.DateField(_("Fecha de fin"), null=True, blank=True)
    is_active = models.BooleanField(_("Activo"), default=True)
    notes = models.TextField(_("Notas"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_contracts"
        verbose_name = _("Asignación a contrato")
        verbose_name_plural = _("Asignaciones a contratos")
        unique_together = ["user", "contract"]

    def __str__(self):
        return f"{self.user} - {self.contract}"
