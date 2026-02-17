from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0008_seed_job_profile_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="country",
            field=models.CharField(
                choices=[("CO", "Colombia"), ("PA", "Panamá"), ("PE", "Perú")],
                default="CO",
                help_text="País donde aplica este curso",
                max_length=2,
                verbose_name="País",
            ),
        ),
    ]
