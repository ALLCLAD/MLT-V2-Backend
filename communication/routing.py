from django.urls import re_path
from . import consumers 

websocket_urlpatterns = [
    # Adresse pour le chat en direct
    re_path(r'ws/chat/(?P<contact_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    
    # Adresse pour les notifications en direct
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
