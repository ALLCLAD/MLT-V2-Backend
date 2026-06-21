from django.apps import AppConfig


class UauthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Uauth'

    def ready(self):
        # On importe les signaux ici pour qu'ils soient enregistrés par Django
        from . import signals
