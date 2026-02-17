"""
Data migration to seed initial job profile types from existing hardcoded choices.
"""

from django.db import migrations

PROFILES = [
    {"code": "LINIERO", "name": "Liniero", "description": "Personal operativo - Liniero", "order": 1},
    {"code": "TECNICO", "name": "Tecnico", "description": "Personal operativo - Tecnico", "order": 2},
    {"code": "OPERADOR", "name": "Operador", "description": "Personal operativo - Operador", "order": 3},
    {
        "code": "JEFE_CUADRILLA",
        "name": "Jefe de Cuadrilla",
        "description": "Personal profesional",
        "order": 4,
    },
    {
        "code": "INGENIERO_RESIDENTE",
        "name": "Ingeniero Residente",
        "description": "Personal profesional",
        "order": 5,
    },
    {
        "code": "COORDINADOR_HSEQ",
        "name": "Coordinador HSEQ",
        "description": "Personal profesional",
        "order": 6,
    },
    {
        "code": "ADMINISTRADOR",
        "name": "Administrador",
        "description": "Personal administrativo",
        "order": 7,
    },
]


def seed_profiles(apps, schema_editor):
    JobProfileType = apps.get_model("courses", "JobProfileType")
    for profile in PROFILES:
        JobProfileType.objects.get_or_create(code=profile["code"], defaults=profile)


def reverse_seed(apps, schema_editor):
    JobProfileType = apps.get_model("courses", "JobProfileType")
    JobProfileType.objects.filter(code__in=[p["code"] for p in PROFILES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0007_jobprofiletype"),
    ]

    operations = [
        migrations.RunPython(seed_profiles, reverse_seed),
    ]
