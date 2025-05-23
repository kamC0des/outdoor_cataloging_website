from django.apps import AppConfig


class GearshareConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gearshare'
    def ready(self):
        import gearshare.signals