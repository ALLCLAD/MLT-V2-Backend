"""
ASGI config for mlt project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from communication.middleware import JwtAuthMiddleware # Importation de notre nouveau middleware
import communication.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mlt.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JwtAuthMiddleware( 
        URLRouter(
            communication.routing.websocket_urlpatterns
        )
    ),
})
