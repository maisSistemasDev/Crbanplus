from django.urls import re_path
from .consumers import AiChatConsumer

websocket_urlpatterns = [
    re_path(r'^ws/ai/chat/$', AiChatConsumer.as_asgi()),
]
