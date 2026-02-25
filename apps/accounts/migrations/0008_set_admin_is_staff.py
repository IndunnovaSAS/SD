"""
Data migration: set is_staff=True for all users with ADMINISTRADOR job_profile.
"""

from django.db import migrations


def set_admin_is_staff(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(job_profile="ADMINISTRADOR", is_staff=False).update(is_staff=True)


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_remove_sms_otp_code"),
    ]

    operations = [
        migrations.RunPython(set_admin_is_staff, reverse_noop),
    ]
