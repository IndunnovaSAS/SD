"""
User and authentication models for SD LMS.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom user manager for email or document-based authentication."""

    def create_user(self, email=None, password=None, **extra_fields):
        """Create user with email (optional for operational staff)."""
        if email:
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

    class DocumentType(models.TextChoices):
        CC = "CC", _("Cédula de Ciudadanía")
        CE = "CE", _("Cédula de Extranjería")
        TI = "TI", _("Tarjeta de Identidad")
        PASSPORT = "PA", _("Pasaporte")

    class EmploymentType(models.TextChoices):
        DIRECT = "direct", _("Directo")
        CONTRACTOR = "contractor", _("Contratista")

    class Country(models.TextChoices):
        COLOMBIA = "CO", _("Colombia")
        PANAMA = "PA", _("Panamá")
        PERU = "PE", _("Perú")

    class JobProfile(models.TextChoices):
        # Personal operativo (usa cédula para login)
        LINIERO = "LINIERO", _("Liniero")
        TECNICO = "TECNICO", _("Técnico")
        OPERADOR = "OPERADOR", _("Operador")
        # Personal profesional (usa email para login)
        JEFE_CUADRILLA = "JEFE_CUADRILLA", _("Jefe de Cuadrilla")
        INGENIERO_RESIDENTE = "INGENIERO_RESIDENTE", _("Ingeniero Residente")
        COORDINADOR_HSEQ = "COORDINADOR_HSEQ", _("Coordinador HSEQ")
        # Coordinador con permisos de solo visualización (usa email para login)
        COORDINADOR_VISUALIZACION = "COORDINADOR_VIZ", _("Coordinador (Solo Visualización)")
        # Personal administrativo (usa email para login)
        ADMINISTRADOR = "ADMINISTRADOR", _("Administrador")

    # Remove username field, use email or document for login
    username = None
    email = models.EmailField(
        _("Correo electrónico"),
        unique=True,
        null=True,
        blank=True,
        help_text=_("Requerido para personal profesional y administrativo"),
    )

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
        choices=JobProfile.choices,
        default=JobProfile.LINIERO,
    )
    employment_type = models.CharField(
        _("Tipo de vinculación"),
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.DIRECT,
    )
    hire_date = models.DateField(_("Fecha de ingreso"))
    country = models.CharField(
        _("País"),
        max_length=2,
        choices=Country.choices,
        default=Country.COLOMBIA,
        help_text=_("País donde trabaja el usuario"),
    )
    status = models.CharField(
        _("Estado"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    # Metadata
    created_at = models.DateTimeField(_("Fecha de creación"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Fecha de actualización"), auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "document_number"
    REQUIRED_FIELDS = ["first_name", "last_name", "job_position", "hire_date"]

    class Meta:
        db_table = "users"
        verbose_name = _("Usuario")
        verbose_name_plural = _("Usuarios")
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.get_full_name()} ({self.document_number})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    @property
    def is_operational(self):
        """Check if user is operational staff (uses document number for login)."""
        return self.job_profile in [
            self.JobProfile.LINIERO,
            self.JobProfile.TECNICO,
            self.JobProfile.OPERADOR,
        ]

    @property
    def is_professional(self):
        """Check if user is professional staff (requires email for login)."""
        return self.job_profile in [
            self.JobProfile.JEFE_CUADRILLA,
            self.JobProfile.INGENIERO_RESIDENTE,
            self.JobProfile.COORDINADOR_HSEQ,
            self.JobProfile.COORDINADOR_VISUALIZACION,
        ]

    @property
    def is_viewer_only(self):
        """Check if user has view-only permissions (no editing capabilities)."""
        return self.job_profile == self.JobProfile.COORDINADOR_VISUALIZACION

    @property
    def is_admin(self):
        """Check if user is system administrator (requires email for login)."""
        return self.job_profile == self.JobProfile.ADMINISTRADOR

    @property
    def is_supervisor(self):
        """Check if user has supervisor role (can modify data)."""
        return self.job_profile in [
            self.JobProfile.JEFE_CUADRILLA,
            self.JobProfile.INGENIERO_RESIDENTE,
            self.JobProfile.COORDINADOR_HSEQ,
        ]

    @property
    def can_view_analytics(self):
        """Check if user can view analytics dashboard."""
        return self.is_supervisor or self.is_admin or self.is_viewer_only

    @property
    def can_edit_data(self):
        """Check if user can edit data (not view-only)."""
        return (self.is_supervisor or self.is_admin) and not self.is_viewer_only

    @property
    def requires_email(self):
        """Check if user requires email for authentication."""
        return self.is_professional or self.is_admin

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


class JobHistory(models.Model):
    """
    Historical record of job position changes for traceability.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="job_history",
        verbose_name=_("Usuario"),
    )
    previous_position = models.CharField(
        _("Cargo anterior"),
        max_length=100,
        blank=True,
    )
    new_position = models.CharField(
        _("Cargo nuevo"),
        max_length=100,
    )
    previous_profile = models.CharField(
        _("Perfil anterior"),
        max_length=50,
        blank=True,
    )
    new_profile = models.CharField(
        _("Perfil nuevo"),
        max_length=50,
    )
    previous_employment_type = models.CharField(
        _("Vinculación anterior"),
        max_length=20,
        blank=True,
    )
    new_employment_type = models.CharField(
        _("Vinculación nueva"),
        max_length=20,
    )
    change_date = models.DateField(_("Fecha de cambio"))
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="job_changes_made",
        verbose_name=_("Modificado por"),
    )
    reason = models.TextField(_("Motivo"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "job_history"
        verbose_name = _("Historial de cargo")
        verbose_name_plural = _("Historial de cargos")
        ordering = ["-change_date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "-change_date"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.previous_position} → {self.new_position}"


class SMSOTPCode(models.Model):
    """
    SMS OTP code for login verification.
    Ensures the person logging in has access to the registered phone number.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sms_otp_codes",
        verbose_name=_("Usuario"),
    )
    code = models.CharField(_("Código OTP"), max_length=6)
    created_at = models.DateTimeField(_("Fecha de creación"), auto_now_add=True)
    expires_at = models.DateTimeField(_("Fecha de expiración"))
    is_used = models.BooleanField(_("Usado"), default=False)
    used_at = models.DateTimeField(_("Fecha de uso"), null=True, blank=True)
    attempts = models.PositiveIntegerField(_("Intentos de verificación"), default=0)
    ip_address = models.GenericIPAddressField(_("Dirección IP"), null=True, blank=True)

    class Meta:
        db_table = "sms_otp_codes"
        verbose_name = _("Código OTP SMS")
        verbose_name_plural = _("Códigos OTP SMS")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["code", "user", "is_used"]),
        ]

    def __str__(self):
        status = "usado" if self.is_used else "pendiente"
        return f"OTP {self.code} para {self.user} ({status})"

    @property
    def is_expired(self):
        from django.utils import timezone

        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired and self.attempts < 5

    def mark_used(self):
        from django.utils import timezone

        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=["is_used", "used_at"])

    def increment_attempts(self):
        self.attempts += 1
        self.save(update_fields=["attempts"])
