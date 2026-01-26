# Generated manually for user profile updates

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        # Add employment_type field
        migrations.AddField(
            model_name="user",
            name="employment_type",
            field=models.CharField(
                choices=[("direct", "Directo"), ("contractor", "Contratista")],
                default="direct",
                max_length=20,
                verbose_name="Tipo de vinculación",
            ),
        ),
        # Update job_profile to have choices
        migrations.AlterField(
            model_name="user",
            name="job_profile",
            field=models.CharField(
                choices=[
                    ("LINIERO", "Liniero"),
                    ("TECNICO", "Técnico"),
                    ("OPERADOR", "Operador"),
                    ("JEFE_CUADRILLA", "Jefe de Cuadrilla"),
                    ("INGENIERO_RESIDENTE", "Ingeniero Residente"),
                    ("COORDINADOR_HSEQ", "Coordinador HSEQ"),
                    ("ADMINISTRADOR", "Administrador"),
                ],
                default="LINIERO",
                max_length=50,
                verbose_name="Perfil ocupacional",
            ),
        ),
        # Make email nullable for operational staff
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(
                blank=True,
                help_text="Requerido para personal profesional y administrativo",
                max_length=254,
                null=True,
                unique=True,
                verbose_name="Correo electrónico",
            ),
        ),
        # Remove work_front field
        migrations.RemoveField(
            model_name="user",
            name="work_front",
        ),
        # Remove emergency_contact_name field
        migrations.RemoveField(
            model_name="user",
            name="emergency_contact_name",
        ),
        # Remove emergency_contact_phone field
        migrations.RemoveField(
            model_name="user",
            name="emergency_contact_phone",
        ),
        # Create JobHistory model
        migrations.CreateModel(
            name="JobHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "previous_position",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="Cargo anterior"
                    ),
                ),
                (
                    "new_position",
                    models.CharField(max_length=100, verbose_name="Cargo nuevo"),
                ),
                (
                    "previous_profile",
                    models.CharField(
                        blank=True, max_length=50, verbose_name="Perfil anterior"
                    ),
                ),
                (
                    "new_profile",
                    models.CharField(max_length=50, verbose_name="Perfil nuevo"),
                ),
                (
                    "previous_employment_type",
                    models.CharField(
                        blank=True, max_length=20, verbose_name="Vinculación anterior"
                    ),
                ),
                (
                    "new_employment_type",
                    models.CharField(
                        max_length=20, verbose_name="Vinculación nueva"
                    ),
                ),
                ("change_date", models.DateField(verbose_name="Fecha de cambio")),
                ("reason", models.TextField(blank=True, verbose_name="Motivo")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "changed_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="job_changes_made",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Modificado por",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="job_history",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Usuario",
                    ),
                ),
            ],
            options={
                "verbose_name": "Historial de cargo",
                "verbose_name_plural": "Historial de cargos",
                "db_table": "job_history",
                "ordering": ["-change_date", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="jobhistory",
            index=models.Index(
                fields=["user", "-change_date"], name="job_history_user_id_e74a4c_idx"
            ),
        ),
    ]
