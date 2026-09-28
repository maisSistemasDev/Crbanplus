import logging

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from core.base_views import BaseApiView
from core.permissions import IsAdminOrGerenteOrLider
from payments.models import CommissionGroup, CommissionRulesByUser
from bank.models import Table

from .models import TableUpdateSuggestion, Conversation, Message
from .serializers import TableUpdateSuggestionSerializer, ConversationSerializer, MessageSerializer
from .llm import get_ai_reply, compute_and_store_embedding

logger = logging.getLogger(__name__)


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


class ConversationMessageView(BaseApiView):
    """
    Recebe mensagem do usuário (texto + arquivo opcional) e retorna resposta do agente.

    Aceita multipart/form-data (com arquivo) ou application/json (só texto).
    Campos: content (str), file (File, opcional)

    Response: { "reply": "<texto>", "tour_name": "<nome|null>", "conversation_id": <id> }
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk, format=None):
        try:
            conversation = Conversation.objects.get(pk=pk, user=request.user)
        except Conversation.DoesNotExist:
            return Response({'detail': 'Conversa não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        content = (request.data.get('content') or '').strip()
        uploaded_file = request.FILES.get('file')

        if not content and not uploaded_file:
            return Response(
                {'detail': 'Mensagem ou arquivo obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Conteúdo padrão quando só arquivo é enviado
        if not content and uploaded_file:
            content = f'[Arquivo enviado: {uploaded_file.name}]'

        # Salva mensagem do usuário
        user_msg = Message.objects.create(
            conversation=conversation,
            role='user',
            content=content,
        )
        if uploaded_file:
            user_msg.file = uploaded_file
            user_msg.file_name = uploaded_file.name
            user_msg.save(update_fields=['file', 'file_name'])
            from .context_files import attach_conversation_file
            attach_conversation_file(conversation.pk, user_msg.pk)

        file_path = user_msg.file.path if user_msg.file else None

        # Arquivo grande (tabular com >= 50 linhas) → fluxo assíncrono por chunks.
        # Apenas is_large_file() fica em try/except; o dispatch nunca deve falhar silenciosamente.
        if file_path:
            _large = False
            try:
                from .file_chunker import is_large_file
                _large = is_large_file(file_path)
            except Exception as exc:
                logger.warning('is_large_file check falhou: %s', exc)

            if _large:
                from .tasks import index_file_for_tables
                index_file_for_tables.delay(
                    message_pk=user_msg.pk,
                    conversation_id=conversation.pk,
                    user_id=request.user.pk,
                )
                return Response(
                    {'status': 'processing_large', 'conversation_id': pk},
                    status=status.HTTP_202_ACCEPTED,
                )

        # Despacha para Celery — retorna imediatamente ao cliente
        from .tasks import process_ai_message
        process_ai_message.delay(
            conversation_id=conversation.pk,
            message_pk=user_msg.pk,
            file_path=file_path,
        )

        return Response(
            {'status': 'processing', 'conversation_id': pk},
            status=status.HTTP_202_ACCEPTED,
        )


def _schedule_embeddings(user_msg_pk: int, assistant_msg_pk: int, api_key: str) -> None:
    """Tenta agendar cálculo de embeddings via Celery. Falha silenciosamente."""
    try:
        from .tasks import compute_message_embedding
        compute_message_embedding.delay(user_msg_pk, api_key)
        compute_message_embedding.delay(assistant_msg_pk, api_key)
    except Exception:
        pass


class AiSuggestMappingView(BaseApiView):
    """
    POST /api/ai/suggest-mapping/

    Body: { "columns": [FileColumn], "fields": [ModelField] }
    Response: { "mappings": { field_name: [{ index, name, data_type }] } }

    Usa heurística de normalização de nomes para sugerir mapeamentos automáticos.
    Funciona sem chave de API configurada.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        columns = request.data.get('columns', [])
        fields = request.data.get('fields', [])

        if not columns or not fields:
            return Response({'error': 'columns e fields são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)

        mappings = _suggest_mappings(columns, fields)
        return Response({'mappings': mappings})


def _normalize(text: str) -> str:
    """Normaliza texto: minúsculas, sem acentos, sem caracteres especiais."""
    import unicodedata
    text = text.lower().strip()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = text.replace(' ', '_').replace('-', '_').replace('.', '_')
    import re
    text = re.sub(r'[^a-z0-9_]', '', text)
    text = re.sub(r'_+', '_', text).strip('_')
    return text


# Sinônimos comuns em planilhas de proposta
_SYNONYMS: dict[str, list[str]] = {
    'cpf': ['cpf', 'documento', 'doc', 'cpf_cliente', 'nr_cpf', 'num_cpf'],
    'nome': ['nome', 'name', 'nome_cliente', 'cliente', 'razao', 'razao_social', 'titular'],
    'valor': ['valor', 'value', 'montante', 'valor_proposta', 'vl_proposta', 'vl', 'amount'],
    'prazo': ['prazo', 'parcelas', 'qtd_parcelas', 'num_parcelas', 'nr_parcelas', 'meses'],
    'data': ['data', 'date', 'dt', 'data_proposta', 'data_digitacao', 'dt_proposta'],
    'banco': ['banco', 'bank', 'cod_banco', 'nr_banco', 'nome_banco'],
    'convenio': ['convenio', 'convenio', 'agreement', 'produto', 'product', 'beneficio'],
    'matricula': ['matricula', 'mat', 'nr_matricula', 'num_matricula', 'registro'],
    'tabela': ['tabela', 'table', 'cod_tabela', 'nr_tabela', 'tab'],
    'taxa': ['taxa', 'rate', 'juros', 'tx', 'taxa_juros', 'tx_juros'],
    'status': ['status', 'situacao', 'estado', 'st'],
    'telefone': ['telefone', 'tel', 'fone', 'celular', 'phone', 'nr_tel'],
    'email': ['email', 'e_mail', 'mail'],
    'cep': ['cep', 'cod_postal', 'postal'],
    'agente': ['agente', 'agent', 'vendedor', 'seller', 'operador'],
    'parcela': ['parcela', 'vl_parcela', 'valor_parcela', 'prestacao'],
    'contrato': ['contrato', 'nr_contrato', 'num_contrato', 'proposta', 'nr_proposta'],
    'bank_access': [
        'acesso', 'acessos', 'acesso_bancario', 'login', 'usuario', 'username',
        'usuario_acesso', 'acesso_login', 'user_login', 'login_banco',
    ],
    'digitador': ['digitador', 'digitacao', 'operador'],
    'seller': ['vendedor', 'seller', 'corretor', 'agente'],
}


def _score_match(col_norm: str, field_norm: str, field_verbose_norm: str, synonyms: list[str]) -> int:
    # Correspondência exata
    if col_norm == field_norm or col_norm == field_verbose_norm:
        return 100
    # Sinônimos
    if col_norm in synonyms:
        return 90
    if any(s and (s == col_norm or s in col_norm.split('_')) for s in synonyms):
        return 85
    # col contém field ou vice-versa
    if field_norm in col_norm or col_norm in field_norm:
        return 75
    if field_verbose_norm in col_norm or col_norm in field_verbose_norm:
        return 70
    # Sobreposição de palavras
    col_words = set(col_norm.split('_'))
    field_words = set(field_norm.split('_'))
    verbose_words = set(field_verbose_norm.split('_'))
    overlap = len(col_words & field_words)
    verbose_overlap = len(col_words & verbose_words)
    if overlap >= 2 or verbose_overlap >= 2:
        return 60
    if overlap == 1 or verbose_overlap == 1:
        return 40
    return 0


def _suggest_mappings(columns: list, fields: list) -> dict:
    used_col_indices: set = set()
    result: dict = {}

    for field in fields:
        field_name = field.get('name', '')
        field_verbose = field.get('verbose_name', '')
        field_type = field.get('type', '')
        field_norm = _normalize(field_name)
        field_verbose_norm = _normalize(field_verbose)

        # Coleta sinônimos para este campo
        synonyms: list[str] = []
        for key, vals in _SYNONYMS.items():
            if field_norm.startswith(key) or key in field_norm or field_verbose_norm.startswith(key):
                synonyms.extend(vals)

        best_score = 0
        best_col = None

        for col in columns:
            col_idx = col.get('column_index')
            if col_idx in used_col_indices:
                continue
            col_norm = _normalize(col.get('column_name', ''))
            col_type = col.get('detected_type', '')

            score = _score_match(col_norm, field_norm, field_verbose_norm, synonyms)

            # Bônus por tipo compatível
            if score > 0 and _types_compatible(col_type, field_type):
                score += 5

            if score > best_score:
                best_score = score
                best_col = col

        if best_score >= 40 and best_col is not None:
            used_col_indices.add(best_col['column_index'])
            result[field_name] = [{
                'index': best_col['column_index'],
                'name': best_col['column_name'],
                'data_type': best_col.get('detected_type', 'text'),
            }]

    return result


def _types_compatible(col_type: str, field_type: str) -> bool:
    numeric = {'number', 'currency', 'decimal', 'DecimalField', 'IntegerField', 'FloatField'}
    date_types = {'date', 'datetime', 'DateField', 'DateTimeField'}
    text_types = {'text', 'cpf', 'phone', 'email', 'CharField', 'TextField'}
    for group in (numeric, date_types, text_types):
        if col_type in group and field_type in group:
            return True
    return False

