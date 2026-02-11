from django.apps import AppConfig


class OccupationalProfilesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.occupational_profiles"
    verbose_name = "Perfiles Ocupacionales"

    def ready(self):
        import apps.occupational_profiles.signals  # noqa
