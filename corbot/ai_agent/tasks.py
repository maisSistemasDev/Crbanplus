"""
Celery tasks do app ai_agent.

Fase 1 (sem LLM): gera sugestão determinística baseada no limite da promotora.
Quando o PydanticAI for integrado, basta substituir _build_suggestion_data().
"""
import logging
from decimal import Decimal

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def compute_message_embedding(self, message_pk: int, api_key: str):
    """Computa e armazena embedding vetorial de uma mensagem (para contexto longo)."""
    try:
        from .llm import compute_and_store_embedding
        compute_and_store_embedding(message_pk, api_key)
    except Exception as exc:
        logger.warning("compute_message_embedding falhou para msg %s: %s", message_pk, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def process_ai_message(self, conversation_id: int, message_pk: int, file_path: str | None = None):
    """
    Executa a chamada ao LLM em background e entrega o resultado via WebSocket.

    Fluxo:
      1. Reconstrói o histórico da conversa.
      2. Chama get_ai_reply() (pode levar vários segundos).
      3. Salva a mensagem do assistente.
      4. Faz group_send no canal `ai_user_<user_id>` para o consumer entregar ao frontend.
      5. Agenda embeddings como de costume.
    """
    from .models import Conversation, Message
    from .llm import get_ai_reply
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()

    try:
        conversation = Conversation.objects.select_related('user').get(pk=conversation_id)
        user_id = conversation.user_id

        history = list(
            Message.objects.filter(conversation=conversation)
            .order_by('created_at')
            .values('role', 'content', 'created_at')
        )

        from .context_files import resolve_file_for_llm, detach_conversation_file
        effective_path, file_context_text = resolve_file_for_llm(conversation_id, file_path)

        reply_text, tour_name, file_task_done = get_ai_reply(
            history=history,
            conversation_id=conversation_id,
            file_path=effective_path,
            file_context_text=file_context_text,
        )

        assistant_msg = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=reply_text,
        )

        task_complete = False
        if file_task_done:
            detach_conversation_file(conversation_id)
            task_complete = True

        # Envia resposta ao frontend via WebSocket
        logger.info('process_ai_message: enviando ai_reply para ai_user_%s reply_len=%s', user_id, len(reply_text or ''))
        async_to_sync(channel_layer.group_send)(
            f'ai_user_{user_id}',
            {
                'type': 'ai_reply',
                'data': {
                    'type': 'ai_reply',
                    'conversation_id': conversation_id,
                    'reply': reply_text,
                    'tour_name': tour_name,
                    'message_id': assistant_msg.pk,
                    'task_complete': task_complete,
                },
            },
        )

        # Agenda embeddings
        try:
            from core.models import SystemSettings
            settings = SystemSettings.get_solo()
            api_key = (settings.ai_api_key or '').strip()
            if api_key and settings.ai_provider == 'openai':
                compute_message_embedding.delay(message_pk, api_key)
                compute_message_embedding.delay(assistant_msg.pk, api_key)
        except Exception:
            pass

    except Exception as exc:
        logger.error('process_ai_message falhou (conv=%s): %s', conversation_id, exc)
        # Notifica o frontend do erro para não ficar carregando indefinidamente
        try:
            conversation = Conversation.objects.select_related('user').get(pk=conversation_id)
            async_to_sync(channel_layer.group_send)(
                f'ai_user_{conversation.user_id}',
                {
                    'type': 'ai_error',
                    'data': {
                        'type': 'ai_error',
                        'conversation_id': conversation_id,
                        'error': 'Não foi possível processar sua mensagem. Tente novamente.',
                    },
                },
            )
        except Exception:
            pass
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_suggestions_for_table(self, table_id: str, history_id: str):
    """
    Para cada CommissionGroup que usa a tabela atualizada:
      1. Calcula o limite máximo da promotora (CommissionGroupByCompany).
      2. Gera uma sugestão proporcional (50% líder / 50% vendedor do limite).
      3. Salva como TableUpdateSuggestion (status=pending).
      4. Envia push notification para os responsáveis.
    """
    try:
        from bank.models import Table, TableHistory
        from payments.models import CommissionGroup, CommissionGroupByCompany, CommissionRulesByUser
        from ai_agent.models import TableUpdateSuggestion
        from core.models import User

        table = Table.objects.select_related('bank', 'agreement').get(id=table_id)
        history = TableHistory.objects.get(pk=history_id)

        # Grupos que possuem regras para esta tabela
        groups = CommissionGroup.objects.filter(
            commission_rules__table=table
        ).distinct().select_related('company', 'leader')

        for group in groups:
            _process_group(group, table, history)

    except Exception as exc:
        logger.exception('Erro em generate_suggestions_for_table: %s', exc)
        raise self.retry(exc=exc)


def _process_group(group, table, history):
    from payments.models import CommissionGroupByCompany
    from ai_agent.models import TableUpdateSuggestion
    from core.models import User

    # Limite da promotora para esta tabela
    promotora_limit = _get_promotora_limit(group, table)

    # Configuração atual do grupo para esta tabela
    old_rules = list(
        group.commission_rules.filter(table=table).values(
            'id', 'bank_id', 'table_id',
            'leader_commission_rate', 'seller_commission_rate',
            'commission_range_id',
        )
    )

    if not old_rules and promotora_limit == Decimal('0'):
        return  # nada a sugerir

    suggested_config, reasoning = _build_suggestion_data(old_rules, promotora_limit, table)

    suggestion = TableUpdateSuggestion.objects.create(
        commission_group=group,
        table=table,
        table_history=history,
        old_config=_serialize_decimals(old_rules),
        suggested_config=_serialize_decimals(suggested_config),
        ai_reasoning=reasoning,
    )

    _notify_group_owner(group, table, suggestion)


def _get_promotora_limit(group, table) -> Decimal:
    """Retorna a taxa máxima que a promotora permite para este grupo/tabela."""
    from payments.models import CommissionGroupByCompany

    if not group.company_id:
        return Decimal('0')

    company_group = CommissionGroupByCompany.objects.filter(
        companies=group.company, is_active=True
    ).first()

    if not company_group:
        return Decimal('0')

    rule = company_group.comission_rules.filter(
        table=table, commission_range__isnull=True
    ).first()

    return Decimal(str(rule.commission_rate)) if rule else Decimal('0')


def _build_suggestion_data(old_rules, promotora_limit: Decimal, table):
    """
    Fase 1: lógica determinística — divide o limite 50/50 entre líder e vendedor.
    Fase 2: substituir por chamada PydanticAI.
    """
    if promotora_limit == Decimal('0'):
        return old_rules, 'Sem limite de promotora definido; configuração mantida.'

    half = (promotora_limit / 2).quantize(Decimal('0.01'))
    remainder = promotora_limit - half  # garante que soma == limite

    if old_rules:
        suggested = []
        for rule in old_rules:
            suggested.append({
                **rule,
                'leader_commission_rate': float(half),
                'seller_commission_rate': float(remainder),
            })
    else:
        suggested = [{
            'bank_id': str(table.bank_id),
            'table_id': str(table.pk),
            'commission_range_id': None,
            'leader_commission_rate': float(half),
            'seller_commission_rate': float(remainder),
        }]

    reasoning = (
        f'Tabela "{table.name_in_bank}" atualizada (banco: {table.bank.name}). '
        f'Limite da promotora: {promotora_limit}%. '
        f'Sugestão automática: Líder {half}% / Vendedor {remainder}% '
        f'(divisão igualitária do limite). Revise conforme sua estratégia comercial.'
    )
    return suggested, reasoning


def _serialize_decimals(data):
    """Converte Decimal para float para serialização JSON."""
    if isinstance(data, list):
        return [_serialize_decimals(item) for item in data]
    if isinstance(data, dict):
        return {k: _serialize_decimals(v) for k, v in data.items()}
    if isinstance(data, Decimal):
        return float(data)
    return data


def _notify_group_owner(group, table, suggestion):
    """Envia push notification para o responsável pelo grupo."""
    from core.models import User, PushSubscription
    from core.push_signals import send_push

    user_ids = set()

    if group.by_leader and group.leader_id:
        user_ids.add(group.leader_id)
    elif group.company_id:
        admins = User.objects.filter(
            company_id=group.company_id,
            role=User.EMPRESA_ADMIN,
        ).values_list('id', flat=True)
        user_ids.update(admins)

    if not user_ids:
        return

    subs = PushSubscription.objects.filter(user_id__in=user_ids)
    for sub in subs:
        send_push(
            sub,
            title='Tabela atualizada 📋',
            body=(
                f'A tabela "{table.name_in_bank}" foi atualizada. '
                f'Uma sugestão de configuração está disponível para o grupo "{group.name}".'
            ),
            url='/commission-groups',
        )


# ─── Indexação e processamento de arquivos grandes ───────────────────────────

def _ws_send(user_id: int, event_type: str, payload: dict):
    """Atalho para group_send síncrono via channel layer."""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'ai_user_{user_id}',
        {'type': event_type, 'data': payload},
    )


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def index_file_for_tables(self, message_pk: int, conversation_id: int, user_id: int):
    """
    Fase 1 do pipeline de arquivo grande:
      1. Cria o FileIndex (feito aqui, não na view, para não engolir erros de migration).
      2. Chama LLM UMA VEZ com header + amostra → descobre mapeamento de colunas.
      3. Cria os FileChunk records.
      4. Atualiza FileIndex com total_rows, total_chunks, column_mapping, status=processing.
      5. Envia WebSocket imediato informando o progresso.
      6. Dispara process_chunk_for_tables para cada chunk.
    """
    from .models import FileIndex, FileChunk, Message
    from .file_chunker import read_tabular_file, iter_chunks

    try:
        message = Message.objects.get(pk=message_pk)
    except Message.DoesNotExist:
        logger.error('index_file_for_tables: Message %s não encontrada', message_pk)
        return

    file_path = message.file.path if message.file else None
    if not file_path:
        logger.error('index_file_for_tables: message %s sem arquivo', message_pk)
        return

    # Cria o FileIndex aqui — erros de migration ficam no log da task, não engolidos na view
    try:
        fi = FileIndex.objects.create(
            message=message,
            conversation_id=conversation_id,
            file_name=message.file_name or 'arquivo',
            status=FileIndex.INDEXING,
        )
    except Exception as exc:
        logger.error('index_file_for_tables: falha ao criar FileIndex: %s', exc)
        _ws_send(user_id, 'ai_error', {
            'type': 'ai_error',
            'conversation_id': conversation_id,
            'error': 'Erro interno ao indexar o arquivo. Verifique se as migrations foram aplicadas.',
        })
        raise self.retry(exc=exc)

    try:
        header, rows, _ = read_tabular_file(file_path)
    except Exception as exc:
        logger.error('index_file_for_tables: erro ao ler arquivo: %s', exc)
        fi.status = FileIndex.ERROR
        fi.save(update_fields=['status'])
        _ws_send(user_id, 'ai_error', {
            'type': 'ai_error',
            'conversation_id': conversation_id,
            'error': f'Não foi possível ler o arquivo: {exc}',
        })
        return

    # ── Criar FileChunk records (o LLM interpreta cada chunk individualmente) ─
    chunks_data = list(iter_chunks(rows, header))

    bulk_chunks = []
    for chunk_idx, row_start, row_end, content in chunks_data:
        bulk_chunks.append(FileChunk(
            file_index=fi,
            chunk_index=chunk_idx,
            row_start=row_start,
            row_end=row_end,
            content=content,
            status=FileChunk.PENDING,
        ))
    FileChunk.objects.bulk_create(bulk_chunks)

    # ── Atualiza FileIndex ─────────────────────────────────────────────────
    fi.total_rows = len(rows)
    fi.total_chunks = len(chunks_data)
    fi.status = FileIndex.PROCESSING
    fi.save(update_fields=['total_rows', 'total_chunks', 'status'])

    # ── Notifica o usuário ─────────────────────────────────────────────────
    _ws_send(user_id, 'ai_reply', {
        'type': 'ai_reply',
        'conversation_id': conversation_id,
        'reply': (
            f'Arquivo detectado com **{len(rows)} linhas** em **{len(chunks_data)} lotes**. '
            f'Iniciando criação das tabelas em segundo plano… '
            f'Acompanhe o progresso aqui.'
        ),
        'message_id': None,
        'tour_name': None,
    })

    # ── Dispara uma task por chunk ─────────────────────────────────────────
    chunk_ids = list(
        FileChunk.objects.filter(file_index=fi).values_list('id', flat=True)
    )
    for chunk_id in chunk_ids:
        process_chunk_for_tables.delay(chunk_id, conversation_id, user_id)


@shared_task(bind=True, max_retries=3, default_retry_delay=15)
def process_chunk_for_tables(self, chunk_id: int, conversation_id: int, user_id: int):
    """
    Fase 2 do pipeline: processa um único chunk via LLM (create_tables_batch).

    1. Carrega o chunk.
    2. Chama process_chunk_with_llm — o LLM interpreta o formato da planilha
       e cria as tabelas usando create_tables_batch.
    3. Salva result_summary, marca DONE.
    4. Atualiza done_chunks no FileIndex atomicamente.
    5. Quando todos os chunks estiverem prontos, envia resumo final via WebSocket.
    """
    from .models import FileChunk, FileIndex
    from .file_chunker import parse_chunk_to_table_dicts
    from .tools import tool_create_tables_batch

    try:
        chunk = FileChunk.objects.select_related('file_index').get(pk=chunk_id)
    except FileChunk.DoesNotExist:
        logger.error('FileChunk %s não encontrado', chunk_id)
        return

    file_index = chunk.file_index

    chunk.status = FileChunk.PROCESSING
    chunk.save(update_fields=['status'])

    try:
        from core.models import SystemSettings
        settings = SystemSettings.get_solo()
        api_key = (settings.ai_api_key or '').strip()
        provider = settings.ai_provider or 'openai'
        model = getattr(settings, 'ai_model', None) or None

        if api_key:
            from .llm import process_chunk_with_llm
            result = process_chunk_with_llm(chunk.content, api_key, provider, model)
        else:
            # Fallback sem LLM: parsing Python com mapeamento salvo no FileIndex
            from .file_chunker import parse_chunk_to_table_dicts
            from .tools import tool_create_tables_batch
            mapping = file_index.column_mapping or {}
            tables = parse_chunk_to_table_dicts(chunk.content, mapping)
            result = (
                tool_create_tables_batch(tables=tables)
                if tables
                else {'created_count': 0, 'error_count': 0, 'skipped': True}
            )

        chunk.result_summary = result
        chunk.status = FileChunk.DONE
        chunk.save(update_fields=['result_summary', 'status'])

    except Exception as exc:
        logger.error('process_chunk_for_tables chunk=%s: %s', chunk_id, exc)
        chunk.status = FileChunk.ERROR
        chunk.error_detail = str(exc)
        chunk.save(update_fields=['status', 'error_detail'])
        raise self.retry(exc=exc)

    # ── Atualiza progresso e verifica conclusão ────────────────────────────
    all_done = file_index.increment_done()

    # Notifica progresso em tempo real
    file_index.refresh_from_db(fields=['done_chunks'])
    _ws_send(user_id, 'ai_progress', {
        'type': 'ai_progress',
        'conversation_id': conversation_id,
        'done': file_index.done_chunks,
        'total': file_index.total_chunks,
    })

    if all_done:
        file_index.status = FileIndex.DONE
        file_index.save(update_fields=['status'])
        _send_completion_summary(file_index, user_id, conversation_id)


def _send_completion_summary(file_index, user_id: int, conversation_id: int):
    """Agrega resultados de todos os chunks e envia resumo final via WebSocket."""
    from .models import FileChunk

    chunks = FileChunk.objects.filter(file_index=file_index)
    total_created = 0
    total_errors = 0
    error_details: list[str] = []

    for c in chunks:
        if c.result_summary:
            total_created += c.result_summary.get('created_count', 0)
            total_errors += c.result_summary.get('error_count', 0)
            for err in c.result_summary.get('errors', []):
                if isinstance(err, dict):
                    error_details.append(err.get('error', str(err)))
                else:
                    error_details.append(str(err))
        elif c.status == FileChunk.ERROR:
            total_errors += 1
            error_details.append(c.error_detail or 'Erro desconhecido')

    parts = [
        f'Processamento do arquivo **{file_index.file_name}** concluído.',
        f'**{total_created}** tabelas criadas em {file_index.total_chunks} lotes.',
    ]
    if total_errors:
        parts.append(f'**{total_errors}** erros encontrados.')
        if error_details[:3]:
            parts.append('Primeiros erros: ' + '; '.join(error_details[:3]))

    # ── Gera CSV de erros ─────────────────────────────────────────────────
    error_csv_url = None
    if total_errors:
        try:
            import csv, io, os
            from django.conf import settings
            from django.utils import timezone

            rows = []
            for c in chunks:
                for err in (c.result_summary or {}).get('errors', []):
                    d = err.get('data', {})
                    rows.append({
                        'banco': d.get('bank_id', ''),
                        'convenio': d.get('agreement_id', ''),
                        'nome_tabela': d.get('name_in_bank', ''),
                        'comissao': d.get('commission_rate', ''),
                        'vigencia': d.get('vigency_date', ''),
                        'erro': err.get('error', ''),
                    })

            if rows:
                ts = timezone.now().strftime('%Y%m%d_%H%M%S')
                rel_path = os.path.join('imports', f'erros_{ts}.csv')
                abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                with open(abs_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(rows)
                error_csv_url = f"{settings.MEDIA_URL}{rel_path}"
        except Exception as exc:
            logger.warning('Falha ao gerar CSV de erros: %s', exc)

    if error_csv_url:
        parts.append(f'[Baixar log de erros em CSV]({error_csv_url})')

    from .models import Message
    msg = Message.objects.create(
        conversation_id=file_index.conversation_id,
        role=Message.ASSISTANT,
        content='\n'.join(parts),
    )
    _ws_send(user_id, 'ai_reply', {
        'type': 'ai_reply',
        'conversation_id': conversation_id,
        'reply': '\n'.join(parts),
        'message_id': msg.pk,
        'tour_name': None,
        'task_complete': True,
    })
    from .context_files import detach_conversation_file
    detach_conversation_file(conversation_id)
