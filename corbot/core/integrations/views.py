"""Views da API de integração v1 e cadastro público."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from core.api_key_auth import APIKeyAuthentication
from core.base_views import BaseApiView
from core.integration_permissions import HasAPIKeyScope, RequiresAPIKey
from core.integrations.idempotency import resolve_idempotency, store_idempotency
from core.integrations.services.commission_group import (
    create_commission_group,
    create_registration_link,
    revoke_registration_link,
)
from core.integrations.services.corban import create_corban
from core.integrations.services.registration import get_registration_info, register_seller_via_link
from core.integrations.services.seller import create_seller
from core.models import IntegrationIdempotencyRecord
from payments.models import CommissionGroup, CommissionGroupRegistrationLink


class PublicRegistrationThrottle(AnonRateThrottle):
    scope = 'public_registration'


class IntegrationAPIView(BaseApiView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [RequiresAPIKey, HasAPIKeyScope]


class CorbanIntegrationCreateView(IntegrationAPIView):
    required_api_key_scopes = ['companies:write']

    def post(self, request):
        api_key = request.api_key
        body = request.data or {}
        idem_key = request.headers.get('Idempotency-Key')

        cached = resolve_idempotency(
            api_key, idem_key, body.get('external_id'),
            IntegrationIdempotencyRecord.RESOURCE_CORBAN,
        )
        if cached:
            return cached

        try:
            result = create_corban(
                company_data=body.get('company') or body,
                admin_user_data=body.get('admin_user'),
                commission_group_by_company_id=body.get('commission_group_by_company_id'),
            )
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        if body.get('external_id'):
            result['external_id'] = body['external_id']

        store_idempotency(
            api_key, idem_key, body.get('external_id'),
            IntegrationIdempotencyRecord.RESOURCE_CORBAN,
            result['company_id'], status.HTTP_201_CREATED, result,
        )
        self.log_info(request, 'integration_create_corban', f'Corban criado: {result["company_id"]}')
        return Response(result, status=status.HTTP_201_CREATED)


class SellerIntegrationCreateView(IntegrationAPIView):
    required_api_key_scopes = ['users:write']

    def post(self, request):
        api_key = request.api_key
        body = request.data or {}
        idem_key = request.headers.get('Idempotency-Key')

        cached = resolve_idempotency(
            api_key, idem_key, body.get('external_id'),
            IntegrationIdempotencyRecord.RESOURCE_SELLER,
        )
        if cached:
            return cached

        company_id = body.get('company_id')
        if not company_id:
            return Response({'company_id': ['Obrigatório.']}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = create_seller(
                api_key=api_key,
                company_id=str(company_id),
                cpf=body.get('cpf', ''),
                email=body.get('email', ''),
                first_name=body.get('first_name', ''),
                last_name=body.get('last_name', ''),
                password=body.get('password'),
                leader_id=body.get('leader_id'),
                commission_group_id=body.get('commission_group_id'),
                matricula=body.get('matricula'),
                certificado=body.get('certificado'),
                extra_data=body.get('extra_data'),
            )
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        if body.get('external_id'):
            result['external_id'] = body['external_id']

        store_idempotency(
            api_key, idem_key, body.get('external_id'),
            IntegrationIdempotencyRecord.RESOURCE_SELLER,
            str(result['user_id']), status.HTTP_201_CREATED, result,
        )
        self.log_info(request, 'integration_create_seller', f'Vendedor criado: {result["user_id"]}')
        return Response(result, status=status.HTTP_201_CREATED)


class CommissionGroupIntegrationCreateView(IntegrationAPIView):
    required_api_key_scopes = ['commissions:write']

    def post(self, request):
        api_key = request.api_key
        body = request.data or {}
        idem_key = request.headers.get('Idempotency-Key')

        cached = resolve_idempotency(
            api_key, idem_key, body.get('external_id'),
            IntegrationIdempotencyRecord.RESOURCE_COMMISSION_GROUP,
        )
        if cached:
            return cached

        company_id = body.get('company_id')
        if not company_id:
            return Response({'company_id': ['Obrigatório.']}, status=status.HTTP_400_BAD_REQUEST)
        if not (body.get('name') or '').strip():
            return Response({'name': ['Obrigatório.']}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = create_commission_group(
                api_key=api_key,
                name=body.get('name', ''),
                company_id=str(company_id),
                description=body.get('description', ''),
                color=body.get('color', '#3b82f6'),
                commission_rules=body.get('commission_rules'),
                registration=body.get('registration'),
                request=request,
            )
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        if body.get('external_id'):
            result['external_id'] = body['external_id']

        store_idempotency(
            api_key, idem_key, body.get('external_id'),
            IntegrationIdempotencyRecord.RESOURCE_COMMISSION_GROUP,
            str(result['id']), status.HTTP_201_CREATED, result,
        )
        self.log_info(request, 'integration_create_commission_group', f'Grupo criado: {result["id"]}')
        return Response(result, status=status.HTTP_201_CREATED)


class CommissionGroupRegistrationLinkCreateView(IntegrationAPIView):
    required_api_key_scopes = ['commissions:write']

    def post(self, request, pk):
        api_key = request.api_key
        group = get_object_or_404(CommissionGroup, pk=pk)
        if not group.company_id:
            return Response(
                {'detail': ['Grupo sem Corban vinculado.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        body = request.data or {}
        try:
            from core.integrations.services.commission_group import _parse_expires_at
            link = create_registration_link(
                api_key=api_key,
                group=group,
                expires_at=_parse_expires_at(body.get('expires_at')),
                max_uses=body.get('max_uses'),
                allowed_role=body.get('allowed_role'),
                request=request,
            )
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        return Response(link, status=status.HTTP_201_CREATED)


class RegistrationLinkRevokeView(IntegrationAPIView):
    required_api_key_scopes = ['commissions:write']

    def post(self, request, link_id):
        try:
            revoke_registration_link(str(link_id), request.api_key)
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicRegistrationView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [PublicRegistrationThrottle]

    def get(self, request, token):
        link = CommissionGroupRegistrationLink.find_by_token(token)
        if not link or not link.is_usable():
            return Response(
                {'detail': ['Link inválido, expirado ou esgotado.']},
                status=status.HTTP_410_GONE,
            )
        return Response(get_registration_info(link))

    def post(self, request, token):
        link = CommissionGroupRegistrationLink.find_by_token(token)
        if not link or not link.is_usable():
            return Response(
                {'detail': ['Link inválido, expirado ou esgotado.']},
                status=status.HTTP_410_GONE,
            )

        body = request.data or {}
        try:
            result = register_seller_via_link(
                link,
                cpf=body.get('cpf', ''),
                email=body.get('email', ''),
                first_name=body.get('first_name', ''),
                last_name=body.get('last_name', ''),
                password=body.get('password', ''),
                extra_data=body.get('extra_data'),
            )
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_201_CREATED)
