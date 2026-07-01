from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Route pour le chat privé (1-à-1)
    re_path(r'^ws/chat/private/(?P<contact_id>\d+)/$', consumers.ChatConsumer.as_asgi()),

    # Route pour le chat de Groupe Classe (Enseignant + ses élèves)
    re_path(r'^ws/chat/classe/(?P<enseignant_id>\d+)/$', consumers.ChatConsumer.as_asgi()),

    # Route pour le chat de Groupe Famille (Parent + ses enfants)
    re_path(r'^ws/chat/famille/(?P<parent_id>\d+)/$', consumers.ChatConsumer.as_asgi()),

    # Route pour le système global de notifications temps réel
    re_path(r'^ws/notify/$', consumers.NotificationConsumer.as_asgi()),
]