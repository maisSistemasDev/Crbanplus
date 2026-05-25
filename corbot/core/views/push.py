from rest_framework import permissions, status
from rest_framework.response import Response

from core.base_views import BaseApiView
from core.models import PushSubscription


class PushSubscriptionView(BaseApiView):
    """
    Registra ou remove a subscription de Web Push para o usuário autenticado.
    POST  — cria/atualiza subscription (upsert por endpoint)
    DELETE — remove subscription pelo endpoint
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        endpoint = request.data.get('endpoint', '').strip()
        p256dh = request.data.get('p256dh', '').strip()
        auth = request.data.get('auth', '').strip()

        if not endpoint or not p256dh or not auth:
            return Response(
                {'error': 'endpoint, p256dh e auth são obrigatórios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={'user': request.user, 'p256dh': p256dh, 'auth': auth},
        )
        return Response({'status': 'subscribed'}, status=status.HTTP_200_OK)

    def delete(self, request):
        endpoint = request.data.get('endpoint', '').strip()
        if not endpoint:
            return Response(
                {'error': 'endpoint é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
        return Response({'status': 'unsubscribed'}, status=status.HTTP_200_OK)
