from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from core.base_views import BaseApiView
from core.integrations.services.commission_group import (
    _parse_expires_at,
    create_registration_link,
)
from core.models import User
from core.permissions import IsAdminOrGerenteOrLider
from payments.models import CommissionGroup, CommissionGroupRegistrationLink


def _link_data(link: CommissionGroupRegistrationLink) -> dict:
    return {
        'id': str(link.id),
        'expires_at': link.expires_at.isoformat() if link.expires_at else None,
        'max_uses': link.max_uses,
        'uses_count': link.uses_count,
        'is_active': link.is_active,
        'is_usable': link.is_usable(),
        'created_at': link.created_at.isoformat(),
    }


class CommissionGroupRegistrationLinkView(BaseApiView):
    permission_classes = [IsAdminOrGerenteOrLider]

    def _get_group(self, request, pk: int) -> CommissionGroup:
        group = get_object_or_404(
            CommissionGroup.objects.select_related('company', 'leader'),
            pk=pk,
        )
        user = request.user

        if not group.company_id:
            self.permission_denied(request, message='Grupos da promotora não aceitam cadastro público.')
        if user.role != User.ADMIN and group.company_id != user.company_id:
            self.permission_denied(request)
        if user.role == User.LIDER and group.leader_id != user.id:
            self.permission_denied(request)
        return group

    def get(self, request, pk):
        group = self._get_group(request, pk)
        links = group.registration_links.all()
        return Response([_link_data(link) for link in links])

    def post(self, request, pk):
        group = self._get_group(request, pk)
        try:
            link_data = create_registration_link(
                group=group,
                created_by=request.user,
                expires_at=_parse_expires_at(request.data.get('expires_at')),
                max_uses=request.data.get('max_uses'),
                allowed_role=User.VENDEDOR,
                request=request,
            )
        except Exception as exc:
            from rest_framework.exceptions import ValidationError

            if isinstance(exc, ValidationError):
                return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
            raise

        self.log_info(
            request,
            'create_commission_group_registration_link',
            f'Link de cadastro criado para o grupo {group.id}',
            {'group_id': group.id, 'link_id': link_data['id']},
        )
        return Response(link_data, status=status.HTTP_201_CREATED)


class CommissionGroupRegistrationLinkDetailView(BaseApiView):
    permission_classes = [IsAdminOrGerenteOrLider]

    def delete(self, request, pk, link_id):
        link = get_object_or_404(
            CommissionGroupRegistrationLink.objects.select_related(
                'commission_group', 'commission_group__company',
            ),
            id=link_id,
            commission_group_id=pk,
        )
        group = link.commission_group
        user = request.user

        if user.role != User.ADMIN and group.company_id != user.company_id:
            self.permission_denied(request)
        if user.role == User.LIDER and group.leader_id != user.id:
            self.permission_denied(request)

        link.is_active = False
        link.save(update_fields=['is_active', 'updated_at'])
        self.log_info(
            request,
            'revoke_commission_group_registration_link',
            f'Link de cadastro revogado para o grupo {group.id}',
            {'group_id': group.id, 'link_id': str(link.id)},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
