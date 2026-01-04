"""
Admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Contract, Role, User, UserContract, UserRole


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""

    list_display = (
        "email",
        "first_name",
        "last_name",
        "document_number",
        "job_position",
        "status",
        "is_active",
    )
    list_filter = ("status", "is_active", "is_staff", "job_profile", "hire_date")
    search_fields = ("email", "first_name", "last_name", "document_number")
    ordering = ("last_name", "first_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Información Personal"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "document_type",
                    "document_number",
                    "phone",
                    "photo",
                )
            },
        ),
        (
            _("Información Laboral"),
            {
                "fields": (
                    "job_position",
                    "job_profile",
                    "work_front",
                    "hire_date",
                    "status",
                )
            },
        ),
        (
            _("Contacto de Emergencia"),
            {"fields": ("emergency_contact_name", "emergency_contact_phone")},
        ),
        (
            _("Permisos"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Fechas Importantes"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "document_type",
                    "document_number",
                    "job_position",
                    "job_profile",
                    "hire_date",
                ),
            },
        ),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin configuration for Role model."""

    list_display = ("name", "role_type", "user_count", "created_at")
    list_filter = ("role_type",)
    search_fields = ("name", "description")
    filter_horizontal = ("permissions",)

    def user_count(self, obj):
        return obj.users.count()

    user_count.short_description = _("Usuarios")


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    """Admin configuration for Contract model."""

    list_display = ("code", "name", "client", "start_date", "end_date", "is_active")
    list_filter = ("is_active", "client", "start_date")
    search_fields = ("code", "name", "client")
    date_hierarchy = "start_date"


class UserContractInline(admin.TabularInline):
    """Inline for UserContract in User admin."""

    model = UserContract
    extra = 0
    autocomplete_fields = ["contract"]


class UserRoleInline(admin.TabularInline):
    """Inline for UserRole in User admin."""

    model = UserRole
    extra = 0
    autocomplete_fields = ["role"]
