"""
WebSocket consumer para o chat do agente IA.

Cada usuário se conecta a ws/ai/chat/?token=<jwt>
e entra no grupo `ai_user_<user_id>`.
O Celery faz group_send nesse grupo quando a resposta do LLM fica pronta.
"""
import json
import logging
from urllib.parse import parse_qs

from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class AiChatConsumer(WebsocketConsumer):
    def connect(self):
        user = self.scope.get('user', AnonymousUser())

        # Autenticação JWT via query string (mesmo padrão de proposals)
        if isinstance(user, AnonymousUser):
            raw_query = self.scope.get('query_string', b'').decode('utf-8')
            token_str = parse_qs(raw_query).get('token', [None])[0]

            if not token_str:
                logger.warning('ai_chat: conexão sem token')
                self.close()
                return

            try:
                from rest_framework_simplejwt.tokens import AccessToken
                from rest_framework_simplejwt.exceptions import TokenError
                from django.contrib.auth import get_user_model
                User = get_user_model()
                access = AccessToken(token_str)
                user = User.objects.get(id=access.payload['user_id'])
            except Exception as exc:
                logger.warning('ai_chat: token inválido — %s', exc)
                self.close()
                return

        self.user = user
        self.group_name = f'ai_user_{user.pk}'

        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()
        logger.info('ai_chat: conectado user=%s group=%s channel=%s', user.pk, self.group_name, self.channel_name)

    def disconnect(self, code):
        if hasattr(self, 'group_name'):
            async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    def receive(self, text_data=None, bytes_data=None):
        # Canal é só de saída (servidor → cliente); ignora mensagens do cliente
        pass

    # ── Handlers de eventos do channel layer ──────────────────────────────

    def ai_reply(self, event):
        """Chamado pelo Celery via group_send para entregar a resposta ao cliente."""
        logger.info('ai_chat: ai_reply entregue user=%s', getattr(self, 'user', None) and self.user.pk)
        self.send(text_data=json.dumps(event['data']))

    def ai_error(self, event):
        """Entrega mensagem de erro ao cliente."""
        self.send(text_data=json.dumps(event['data']))

    def ai_progress(self, event):
        """Entrega evento de progresso de tarefa em segundo plano ao cliente."""
        self.send(text_data=json.dumps(event['data']))
