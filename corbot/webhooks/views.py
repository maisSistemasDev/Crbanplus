import json

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.base_views import BaseApiView
from core.permissions import IsAdmin
from webhooks.models import WebhookDelivery, WebhookEndpoint, generate_webhook_secret
from webhooks.serializers import (
    WebhookDeliverySerializer,
    WebhookEndpointCreateSerializer,
    WebhookEndpointSerializer,
)
from webhooks.services.processor import preview_webhook_mapping, process_webhook_payload


def _client_ip(request) -> str | None:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class WebhookEndpointListCreateView(BaseApiView):
    permission_classes = [IsAdmin]

    def get(self, request):
        qs = WebhookEndpoint.objects.select_related('bank', 'layout').all()
        return Response(WebhookEndpointSerializer(qs, many=True, context={'request': request}).data)

    def post(self, request):
        serializer = WebhookEndpointCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        endpoint = serializer.save()
        return Response(
            WebhookEndpointCreateSerializer(endpoint, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class WebhookEndpointDetailView(BaseApiView):
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        return WebhookEndpoint.objects.select_related('bank', 'layout').get(pk=pk)

    def get(self, request, pk):
        endpoint = self.get_object(pk)
        return Response(WebhookEndpointSerializer(endpoint, context={'request': request}).data)

    def patch(self, request, pk):
        endpoint = self.get_object(pk)
        serializer = WebhookEndpointSerializer(
            endpoint,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(WebhookEndpointSerializer(endpoint, context={'request': request}).data)

    def delete(self, request, pk):
        endpoint = self.get_object(pk)
        endpoint.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WebhookEndpointRegenerateSecretView(BaseApiView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        endpoint = WebhookEndpoint.objects.get(pk=pk)
        endpoint.secret_token = generate_webhook_secret()
        endpoint.save(update_fields=['secret_token', 'updated_at'])
        return Response({
            'secret_token': endpoint.secret_token,
            'inbound_url': endpoint.inbound_url(request),
        })


class WebhookEndpointDeliveriesView(BaseApiView):
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        endpoint = WebhookEndpoint.objects.get(pk=pk)
        deliveries = endpoint.deliveries.select_related('proposal_batch').all()[:50]
        return Response(WebhookDeliverySerializer(deliveries, many=True).data)


class WebhookEndpointTestView(BaseApiView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        endpoint = WebhookEndpoint.objects.get(pk=pk)
        payload = request.data.get('payload')
        if payload is None:
            return Response({'detail': 'payload é obrigatório.'}, status=400)
        try:
            result = preview_webhook_mapping(endpoint, payload)
            return Response(result)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=400)


class WebhookInboundView(APIView):
    """Recebe POST JSON de sistemas externos (sem JWT)."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, endpoint_id):
        try:
            endpoint = WebhookEndpoint.objects.select_related('layout', 'bank').get(
                pk=endpoint_id,
                is_active=True,
            )
        except WebhookEndpoint.DoesNotExist:
            return Response({'detail': 'Webhook não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        secret = (
            request.headers.get('X-Webhook-Secret')
            or request.headers.get('X-Webhook-Token')
            or request.query_params.get('secret', '')
        ).strip()
        if not secret or secret != endpoint.secret_token:
            return Response({'detail': 'Token inválido.'}, status=status.HTTP_401_UNAUTHORIZED)

        if request.content_type and 'json' not in request.content_type.lower():
            if not isinstance(request.data, (dict, list)):
                return Response({'detail': 'Envie JSON no corpo da requisição.'}, status=400)

        payload = request.data
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                return Response({'detail': 'JSON inválido.'}, status=400)

        try:
            delivery = process_webhook_payload(
                endpoint,
                payload,
                source_ip=_client_ip(request),
                create_batch=True,
            )
        except Exception as exc:
            return Response(
                {'detail': str(exc), 'status': 'failed'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        response_data = {
            'delivery_id': str(delivery.id),
            'status': delivery.status,
            'items_count': delivery.items_count,
            'batch_created': delivery.batch_created,
        }
        if delivery.proposal_batch_id:
            response_data['batch_id'] = str(delivery.proposal_batch_id)
            response_data['batch_total_rows'] = delivery.proposal_batch.total_rows

        return Response(response_data, status=status.HTTP_202_ACCEPTED)

    def get(self, request, endpoint_id):
        """Health check para validar URL do webhook."""
        exists = WebhookEndpoint.objects.filter(pk=endpoint_id, is_active=True).exists()
        if not exists:
            return Response({'detail': 'Webhook não encontrado.'}, status=404)
        return Response({'ok': True, 'message': 'Envie POST com JSON e header X-Webhook-Secret.'})
