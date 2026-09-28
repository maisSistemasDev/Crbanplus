"""
ASGI config for corbot project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/stable/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'corbot.settings')

# Importa a aplicação ASGI padrão do Django.
# Isso precisa ser feito antes de importar qualquer coisa que dependa das configurações do Django.
django_asgi_app = get_asgi_application()

# Importa as configurações de roteamento WebSocket
from proposals.routing import websocket_urlpatterns as proposals_ws
from ai_agent.routing import websocket_urlpatterns as ai_ws

websocket_urlpatterns = proposals_ws + ai_ws

application = ProtocolTypeRouter(
    {
        # Aplicação ASGI do Django para requisições HTTP tradicionais
        "http": django_asgi_app,
        
        # Roteamento WebSocket
        "websocket": AllowedHostsOriginValidator( # Opcional, mas recomendado
            AuthMiddlewareStack(
                URLRouter(
                    websocket_urlpatterns
                )
            )
        ),
    }
) 