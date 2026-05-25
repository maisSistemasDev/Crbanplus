from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response

from core.base_views import BaseApiView
from core.permissions import IsAdminOrGerenteOrLider
from payments.models import CommissionGroup, CommissionRulesByUser
from bank.models import Table

from .models import TableUpdateSuggestion, Conversation, Message
from .serializers import TableUpdateSuggestionSerializer, ConversationSerializer, MessageSerializer


class TableSuggestionListView(BaseApiView):
    """
    Lista sugestões de atualização de tabela para o usuário autenticado.
    Filtra por status=pending por padrão.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        user = request.user
        qs = TableUpdateSuggestion.objects.select_related(
            'commission_group', 'table', 'table__bank'
        )

        # Filtra pelos grupos que o usuário gerencia
        if user.role == user.ADMIN:
            pass  # vê tudo
        elif user.role == user.GERENTE and user.company:
            qs = qs.filter(commission_group__company=user.company)
        elif user.role == user.EMPRESA_ADMIN and user.company:
            qs = qs.filter(commission_group__company=user.company)
        elif user.role == user.LIDER:
            qs = qs.filter(
                commission_group__by_leader=True,
                commission_group__leader=user,
            )
        else:
            return Response([], status=status.HTTP_200_OK)

        status_filter = request.query_params.get('status', 'pending')
        if status_filter:
            qs = qs.filter(status=status_filter)

        group_id = request.query_params.get('group')
        if group_id:
            qs = qs.filter(commission_group_id=group_id)

        serializer = TableUpdateSuggestionSerializer(qs, many=True)
        return Response(serializer.data)


class TableSuggestionAcceptView(BaseApiView):
    """
    Aceita uma sugestão: aplica as regras sugeridas ao CommissionGroup.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, format=None):
        suggestion = self._get_suggestion(pk, request.user)
        if isinstance(suggestion, Response):
            return suggestion

        if suggestion.status != TableUpdateSuggestion.PENDING:
            return Response(
                {'detail': 'Sugestão já foi processada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        self._apply_suggestion(suggestion)

        suggestion.status = TableUpdateSuggestion.ACCEPTED
        suggestion.applied_at = timezone.now()
        suggestion.applied_by = request.user
        suggestion.save(update_fields=['status', 'applied_at', 'applied_by'])

        self.log_info(
            request=request,
            action='accept_table_suggestion',
            message=f'Sugestão #{suggestion.pk} aceita para o grupo "{suggestion.commission_group.name}"',
            data={'suggestion_id': suggestion.pk},
        )

        serializer = TableUpdateSuggestionSerializer(suggestion)
        return Response(serializer.data)

    def _get_suggestion(self, pk, user):
        try:
            suggestion = TableUpdateSuggestion.objects.select_related(
                'commission_group', 'commission_group__company', 'commission_group__leader'
            ).get(pk=pk)
        except TableUpdateSuggestion.DoesNotExist:
            return Response({'detail': 'Não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        group = suggestion.commission_group
        if user.role == user.ADMIN:
            return suggestion
        if user.role in (user.GERENTE, user.EMPRESA_ADMIN) and user.company == group.company:
            return suggestion
        if user.role == user.LIDER and group.by_leader and group.leader == user:
            return suggestion

        return Response({'detail': 'Sem permissão.'}, status=status.HTTP_403_FORBIDDEN)

    def _apply_suggestion(self, suggestion):
        """Substitui as regras atuais para a tabela pelas regras sugeridas."""
        group = suggestion.commission_group
        table = suggestion.table

        # Remove regras antigas desta tabela no grupo
        old_rule_ids = list(
            group.commission_rules.filter(table=table).values_list('id', flat=True)
        )
        group.commission_rules.remove(*old_rule_ids)
        CommissionRulesByUser.objects.filter(id__in=old_rule_ids).delete()

        # Cria as novas regras
        new_rule_ids = []
        for rule_data in suggestion.suggested_config:
            rule = CommissionRulesByUser.objects.create(
                bank_id=rule_data.get('bank_id') or table.bank_id,
                table=table,
                commission_range_id=rule_data.get('commission_range_id'),
                leader_commission_rate=rule_data['leader_commission_rate'],
                seller_commission_rate=rule_data['seller_commission_rate'],
            )
            new_rule_ids.append(rule.id)

        group.commission_rules.add(*new_rule_ids)


class TableSuggestionRejectView(BaseApiView):
    """
    Rejeita uma sugestão sem aplicar alterações.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, format=None):
        try:
            suggestion = TableUpdateSuggestion.objects.get(pk=pk)
        except TableUpdateSuggestion.DoesNotExist:
            return Response({'detail': 'Não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if suggestion.status != TableUpdateSuggestion.PENDING:
            return Response(
                {'detail': 'Sugestão já foi processada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        suggestion.status = TableUpdateSuggestion.REJECTED
        suggestion.save(update_fields=['status'])

        self.log_info(
            request=request,
            action='reject_table_suggestion',
            message=f'Sugestão #{suggestion.pk} rejeitada',
            data={'suggestion_id': suggestion.pk},
        )

        return Response({'detail': 'Sugestão rejeitada.'})


class ConversationListCreateView(BaseApiView):
    """
    Lista conversas do usuário e cria novas.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        conversations = Conversation.objects.filter(user=request.user)
        serializer = ConversationSerializer(conversations, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        conversation = Conversation.objects.create(user=request.user)
        serializer = ConversationSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ConversationDetailView(BaseApiView):
    """
    Retorna o histórico de uma conversa específica.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, format=None):
        try:
            conversation = Conversation.objects.prefetch_related('messages').get(
                pk=pk, user=request.user
            )
        except Conversation.DoesNotExist:
            return Response({'detail': 'Não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ConversationSerializer(conversation)
        return Response(serializer.data)

    def delete(self, request, pk, format=None):
        try:
            conversation = Conversation.objects.get(pk=pk, user=request.user)
        except Conversation.DoesNotExist:
            return Response({'detail': 'Não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
