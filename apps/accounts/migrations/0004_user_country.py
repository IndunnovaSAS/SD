from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_rename_job_history_user_id_e74a4c_idx_job_history_user_id_3970d1_idx"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="country",
            field=models.CharField(
                choices=[("CO", "Colombia"), ("PA", "Panamá"), ("PE", "Perú")],
                default="CO",
                max_length=2,
                verbose_name="País",
            ),
        ),
    ]
