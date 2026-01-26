# Generated manually for removing risk_level and duration fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0004_add_missing_indexes"),
    ]

    operations = [
        # Remove risk_level field from Course
        migrations.RemoveField(
            model_name="course",
            name="risk_level",
        ),
        # Remove duration field from Course (now calculated from lessons)
        migrations.RemoveField(
            model_name="course",
            name="duration",
        ),
        # Update job_profile field to have choices
        migrations.AlterField(
            model_name="course",
            name="course_type",
            field=models.CharField(
                choices=[
                    ("mandatory", "Obligatorio"),
                    ("optional", "Opcional"),
                    ("refresher", "Refuerzo"),
                ],
                default="mandatory",
                max_length=20,
                verbose_name="Tipo",
            ),
        ),
    ]
