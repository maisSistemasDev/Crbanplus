"""Anexo de arquivo ao contexto da conversa (até conclusão da tarefa)."""
import logging

logger = logging.getLogger(__name__)


def attach_conversation_file(conversation_id: int, message_pk: int) -> None:
    from .models import Conversation, Message

    try:
        message = Message.objects.get(pk=message_pk, conversation_id=conversation_id)
    except Message.DoesNotExist:
        return
    if not message.file:
        return
    Conversation.objects.filter(pk=conversation_id).update(context_file_message_id=message.pk)


def detach_conversation_file(conversation_id: int) -> None:
    from .models import Conversation

    Conversation.objects.filter(pk=conversation_id).update(context_file_message_id=None)


def get_attached_file_path(conversation_id: int) -> str | None:
    from .models import Conversation

    try:
        conversation = Conversation.objects.select_related('context_file_message').get(pk=conversation_id)
    except Conversation.DoesNotExist:
        return None
    msg = conversation.context_file_message
    if not msg or not msg.file:
        return None
    try:
        path = msg.file.path
    except ValueError:
        return None
    return path if path else None


def build_file_index_context(conversation_id: int, max_chars: int = 12000) -> str | None:
    """Resumo textual de arquivo grande indexado (chunks) para follow-ups."""
    from .models import Conversation, FileIndex

    try:
        conversation = Conversation.objects.select_related('context_file_message').get(pk=conversation_id)
    except Conversation.DoesNotExist:
        return None
    msg = conversation.context_file_message
    if not msg:
        return None
    try:
        fi = msg.file_index
    except Exception:
        return None

    parts = [
        f"[Arquivo anexado: {fi.file_name} — {fi.total_rows} linhas, "
        f"status: {fi.status}, {fi.done_chunks}/{fi.total_chunks} lotes processados]",
    ]
    used = len(parts[0])
    for chunk in fi.chunks.order_by('chunk_index')[:8]:
        snippet = chunk.content[:2000]
        if used + len(snippet) > max_chars:
            break
        parts.append(snippet)
        used += len(snippet)
    return '\n\n'.join(parts) if len(parts) > 1 else parts[0]


def resolve_file_for_llm(conversation_id: int, file_path: str | None) -> tuple[str | None, str | None]:
    """
    Retorna (file_path para multimodal, contexto textual alternativo).
    Arquivos grandes indexados usam trechos dos chunks em vez de reler o arquivo inteiro.
    """
    effective = file_path or get_attached_file_path(conversation_id)
    if not effective:
        return None, None

    try:
        from .file_chunker import is_large_file
        if is_large_file(effective):
            ctx = build_file_index_context(conversation_id)
            if ctx:
                return None, ctx
    except Exception as exc:
        logger.warning('resolve_file_for_llm: %s', exc)

    return effective, None
