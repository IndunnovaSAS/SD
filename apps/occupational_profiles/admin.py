"""
Admin configuration for occupational_profiles app.
"""

from django.contrib import admin

from .models import OccupationalProfile, UserOccupationalProfile


@admin.register(OccupationalProfile)
class OccupationalProfileAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "country", "is_operational", "is_active", "order"]
    list_filter = ["country", "is_operational", "is_active"]
    search_fields = ["code", "name", "description"]
    ordering = ["order", "name"]
    filter_horizontal = ["learning_paths"]

    fieldsets = (
        (None, {"fields": ("code", "name", "description")}),
        ("Configuración", {"fields": ("country", "is_operational", "is_active", "order")}),
        (
            "Rutas de Aprendizaje",
            {
                "fields": ("learning_paths",),
                "description": "Seleccione las rutas de aprendizaje obligatorias para este perfil.",
            },
        ),
    )


@admin.register(UserOccupationalProfile)
class UserOccupationalProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "profile", "is_active", "assigned_by", "assigned_at"]
    list_filter = ["profile", "is_active", "assigned_at"]
    search_fields = ["user__first_name", "user__last_name", "user__document_number"]
    raw_id_fields = ["user", "assigned_by"]
    date_hierarchy = "assigned_at"
