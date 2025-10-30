 # echosphere/asgi.py
"""
ASGI config for echosphere project.
 It exposes the ASGI callable as a module-level variable named ``application``.
 For more information on this file, see
 https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
# Import your routing
from chat.routing import websocket_urlpatterns
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'echosphere.settings')
# Django ASGI application
django_asgi_app = get_asgi_application()
# Combined ASGI application with WebSocket support
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
            )
    ),
 })