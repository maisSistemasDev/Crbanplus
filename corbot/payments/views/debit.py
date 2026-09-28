from decimal import Decimal

from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.response import Response

from core.base_views import BaseApiView
from core.models import Company, User
from core.permissions import IsPromotoraUser
from core.search_utils import paginate_queryset
from payments.models import UserDebit
from payments.serializers import UserDebitSerializer


class UserDebitListCreateView(BaseApiView):
    """Lista e cria debitos para usuarios de corban ou para o proprio corban."""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated()]
        return [IsPromotoraUser()]

    def get(self, request):
        debits = UserDebit.objects.select_related(
            'user', 'created_by', 'user__company', 'company'
        ).all()

        search = request.query_params.get('search', '').strip()
        user_id = request.query_params.get('user', '').strip()
        company_id = request.query_params.get('company', '').strip()
        active = request.query_params.get('active', '').strip().lower()

        if search:
            debits = debits.filter(
                Q(user__cpf__icontains=search)
                | Q(user__email__icontains=search)
                | Q(user__matricula__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(company__name__icontains=search)
                | Q(company__document__icontains=search)
            )

        if user_id:
            debits = debits.filter(user_id=user_id)

        if company_id:
            debits = debits.filter(company_id=company_id)

        if active in {'true', 'false'}:
            debits = debits.filter(is_active=(active == 'true'))

        user = request.user
        if user.role in (User.EMPRESA_ADMIN, User.GERENTE):
            debits = debits.filter(Q(user__company=user.company) | Q(company=user.company))
        elif user.role == User.LIDER:
            debits = debits.filter(Q(user=user) | Q(user__leader=user))
        elif user.role == User.VENDEDOR:
            debits = debits.filter(user=user)
        elif user.role not in (User.ADMIN, User.COLABORADOR):
            return Response({'detail': 'Você não tem permissão para acessar esta página.'}, status=status.HTTP_403_FORBIDDEN)

        return paginate_queryset(request, debits, UserDebitSerializer)

    def post(self, request):
        payload = request.data.copy()
        user_id = payload.get('user')
        company_id = payload.get('company')

        if bool(user_id) == bool(company_id):
            return Response(
                {'detail': 'Informe o usuário ou o corban dono do débito (apenas um dos dois).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_id:
            try:
                target_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({'detail': 'Usuário não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

            if target_user.role in (User.ADMIN, User.COLABORADOR) or target_user.company_id is None:
                return Response(
                    {'detail': 'O débito deve ser lançado para um usuário de corban.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif not Company.objects.filter(id=company_id).exists():
            return Response({'detail': 'Corban não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserDebitSerializer(data=payload)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        debit = serializer.save(created_by=request.user)
        self.audit_create(request=request, instance=debit, data_after=UserDebitSerializer(debit).data)
        self.log_info(
            request=request,
            action='create_user_debit',
            message=f'Débito lançado para {debit.owner_label}',
            data={
                'debit_id': debit.id,
                'user_id': debit.user_id,
                'company_id': str(debit.company_id) if debit.company_id else None,
                'amount': str(Decimal(debit.amount)),
            },
        )
        return Response(UserDebitSerializer(debit).data, status=status.HTTP_201_CREATED)


class UserDebitDetailView(BaseApiView):
    """Consulta e altera status de um débito."""

    def get_permissions(self):
        if self.request.method in ('PATCH', 'DELETE'):
            return [IsPromotoraUser()]
        return [permissions.IsAuthenticated()]

    def _get_debit(self, pk):
        return UserDebit.objects.select_related('user', 'created_by', 'company').get(pk=pk)

    def _can_access_debit(self, requester: User, debit: UserDebit) -> bool:
        if requester.role in (User.ADMIN, User.COLABORADOR):
            return True
        if requester.role in (User.EMPRESA_ADMIN, User.GERENTE):
            if requester.company_id is None:
                return False
            owner_company_id = debit.company_id or (debit.user.company_id if debit.user_id else None)
            return owner_company_id == requester.company_id
        if not debit.user_id:
            return False
        if requester.role == User.LIDER:
            return debit.user_id == requester.id or debit.user.leader_id == requester.id
        if requester.role == User.VENDEDOR:
            return debit.user_id == requester.id
        return False

    def get(self, request, pk):
        try:
            debit = self._get_debit(pk)
        except UserDebit.DoesNotExist:
            return Response({'detail': 'Débito não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not self._can_access_debit(request.user, debit):
            return Response({'detail': 'Você não tem permissão para acessar este débito.'}, status=status.HTTP_403_FORBIDDEN)

        data = UserDebitSerializer(debit).data

        # Propostas que originaram o débito (sinistros).
        data['origin_claims'] = [
            {
                'claim_id': claim.id,
                'claim_type': claim.claim_type,
                'claim_type_display': claim.get_claim_type_display(),
                'amount': str(claim.amount),
                'description': claim.description,
                'proposal_id': str(claim.proposal_id),
                'contract_number': claim.proposal.contract_number,
                'client_name': claim.proposal.client_name,
                'client_document': claim.proposal.client_document,
                'created_at': claim.created_at.isoformat(),
            }
            for claim in debit.claims.select_related('proposal').all()
        ]

        # Comissões em que o débito já foi abatido.
        data['applications'] = [
            {
                'commission_id': application.commission_id,
                'amount': str(application.amount),
                'proposal_id': str(application.commission.proposal_id),
                'contract_number': application.commission.proposal.contract_number,
                'client_name': application.commission.proposal.client_name,
                'role_display': application.commission.get_role_display(),
                'created_at': application.created_at.isoformat(),
            }
            for application in debit.applications.select_related(
                'commission', 'commission__proposal'
            ).all()
        ]

        return Response(data)

    def patch(self, request, pk):
        try:
            debit = self._get_debit(pk)
        except UserDebit.DoesNotExist:
            return Response({'detail': 'Débito não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        old_data = UserDebitSerializer(debit).data
        serializer = UserDebitSerializer(debit, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated = serializer.save()
        self.audit_update(
            request=request,
            instance=updated,
            data_before=old_data,
            data_after=UserDebitSerializer(updated).data,
        )
        return Response(UserDebitSerializer(updated).data)

    def delete(self, request, pk):
        try:
            debit = self._get_debit(pk)
        except UserDebit.DoesNotExist:
            return Response({'detail': 'Débito não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        old_data = UserDebitSerializer(debit).data
        self.audit_delete(request=request, instance=debit, data_before=old_data)
        debit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
