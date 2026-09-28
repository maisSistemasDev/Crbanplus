import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import F

from core.models import User


class Conversation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ai_conversations',
        verbose_name=_('usuário'),
    )
    # Mensagem com arquivo mantida no contexto do LLM até a tarefa concluir.
    context_file_message = models.ForeignKey(
        'Message',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='context_for_conversations',
        verbose_name=_('arquivo em contexto'),
    )
    created_at = models.DateTimeField(_('criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('atualizado em'), auto_now=True)

    class Meta:
        verbose_name = _('Conversa')
        verbose_name_plural = _('Conversas')
        ordering = ['-updated_at']

    def __str__(self):
        return f'Conversa #{self.pk} — {self.user}'


class Message(models.Model):
    USER = 'user'
    ASSISTANT = 'assistant'
    ROLE_CHOICES = [(USER, 'Usuário'), (ASSISTANT, 'Assistente')]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('conversa'),
    )
    role = models.CharField(_('papel'), max_length=10, choices=ROLE_CHOICES)
    content = models.TextField(_('conteúdo'))
    tool_calls = models.JSONField(_('chamadas de ferramentas'), null=True, blank=True)
    # Arquivo/imagem enviado pelo usuário nesta mensagem
    file = models.FileField(
        _('arquivo'), upload_to='ai_agent/uploads/%Y/%m/', null=True, blank=True
    )
    file_name = models.CharField(_('nome do arquivo'), max_length=255, blank=True)
    # Embedding vetorial para recuperação semântica (janela de contexto longa)
    embedding = models.JSONField(_('embedding'), null=True, blank=True)
    created_at = models.DateTimeField(_('criado em'), auto_now_add=True)

    class Meta:
        verbose_name = _('Mensagem')
        verbose_name_plural = _('Mensagens')
        ordering = ['created_at']

    def __str__(self):
        return f'[{self.role}] {self.content[:60]}'


class TableUpdateSuggestion(models.Model):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    STATUS_CHOICES = [
        (PENDING, _('Pendente')),
        (ACCEPTED, _('Aceita')),
        (REJECTED, _('Rejeitada')),
    ]

    commission_group = models.ForeignKey(
        'payments.CommissionGroup',
        on_delete=models.CASCADE,
        related_name='table_suggestions',
        verbose_name=_('grupo de comissionamento'),
    )
    table = models.ForeignKey(
        'bank.Table',
        on_delete=models.CASCADE,
        related_name='suggestions',
        verbose_name=_('tabela'),
    )
    table_history = models.ForeignKey(
        'bank.TableHistory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suggestions',
        verbose_name=_('histórico de atualização'),
    )
    old_config = models.JSONField(_('configuração anterior'))
    suggested_config = models.JSONField(_('configuração sugerida'))
    ai_reasoning = models.TextField(_('raciocínio da IA'), blank=True)
    status = models.CharField(
        _('status'), max_length=10, choices=STATUS_CHOICES, default=PENDING
    )
    created_at = models.DateTimeField(_('criado em'), auto_now_add=True)
    applied_at = models.DateTimeField(_('aplicado em'), null=True, blank=True)
    applied_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applied_suggestions',
        verbose_name=_('aplicado por'),
    )

    class Meta:
        verbose_name = _('Sugestão de Atualização de Tabela')
        verbose_name_plural = _('Sugestões de Atualização de Tabela')
        ordering = ['-created_at']

    def __str__(self):
        return f'Sugestão #{self.pk} — {self.commission_group} / {self.table}'


# ── Indexação de arquivos grandes ────────────────────────────────────────────

class FileIndex(models.Model):
    """Metadados de um arquivo grande indexado em chunks."""
    INDEXING   = 'indexing'
    PROCESSING = 'processing'
    DONE       = 'done'
    ERROR      = 'error'
    STATUS_CHOICES = [
        (INDEXING,   _('Indexando')),
        (PROCESSING, _('Processando')),
        (DONE,       _('Concluído')),
        (ERROR,      _('Erro')),
    ]

    message = models.OneToOneField(
        Message,
        on_delete=models.CASCADE,
        related_name='file_index',
        verbose_name=_('mensagem'),
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='file_indexes',
        verbose_name=_('conversa'),
    )
    file_name  = models.CharField(_('nome do arquivo'), max_length=255)
    total_rows = models.IntegerField(_('total de linhas'), default=0)
    total_chunks = models.IntegerField(_('total de chunks'), default=0)
    done_chunks  = models.IntegerField(_('chunks concluídos'), default=0)
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default=INDEXING)
    # Mapeamento coluna→campo descoberto pelo LLM na primeira análise.
    # Ex: {"bank_id": 0, "agreement_id": 1, "commission_rate": 3, ...}
    column_mapping = models.JSONField(_('mapeamento de colunas'), null=True, blank=True)
    created_at = models.DateTimeField(_('criado em'), auto_now_add=True)

    class Meta:
        verbose_name = _('Índice de Arquivo')
        verbose_name_plural = _('Índices de Arquivo')
        ordering = ['-created_at']

    def __str__(self):
        return f'FileIndex #{self.pk} — {self.file_name} ({self.total_rows} linhas)'

    @property
    def progress_pct(self) -> int:
        if not self.total_chunks:
            return 0
        return int(self.done_chunks / self.total_chunks * 100)

    def increment_done(self) -> bool:
        """Incrementa done_chunks atomicamente. Retorna True se todos concluídos."""
        FileIndex.objects.filter(pk=self.pk).update(done_chunks=F('done_chunks') + 1)
        self.refresh_from_db(fields=['done_chunks', 'total_chunks'])
        return self.done_chunks >= self.total_chunks


class AIAgentRestorePoint(models.Model):
    """Ponto de restauração criado automaticamente pela IA antes de alterações destrutivas."""

    OPERATION_DELETE = 'delete'
    OPERATION_UPDATE = 'update'
    OPERATION_NORMALIZE = 'normalize'
    OPERATION_BULK = 'bulk'
    OPERATION_OTHER = 'other'
    OPERATION_CHOICES = [
        (OPERATION_DELETE, _('Exclusão')),
        (OPERATION_UPDATE, _('Atualização')),
        (OPERATION_NORMALIZE, _('Normalização')),
        (OPERATION_BULK, _('Alteração em lote')),
        (OPERATION_OTHER, _('Outro')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='restore_points',
        verbose_name=_('conversa'),
    )
    operation_type = models.CharField(_('tipo de operação'), max_length=20, choices=OPERATION_CHOICES)
    model_label = models.CharField(_('modelo afetado'), max_length=100, blank=True)
    description = models.CharField(_('descrição'), max_length=255)
    snapshot_data = models.JSONField(_('snapshot para restauração'))
    restored_at = models.DateTimeField(_('restaurado em'), null=True, blank=True)
    created_at = models.DateTimeField(_('criado em'), auto_now_add=True)

    class Meta:
        verbose_name = _('Ponto de Restauração da IA')
        verbose_name_plural = _('Pontos de Restauração da IA')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.operation_type} — {self.model_label} — {self.description[:40]}'


class FileChunk(models.Model):
    """Uma página (chunk) de um arquivo indexado, pronta para processamento."""
    PENDING    = 'pending'
    PROCESSING = 'processing'
    DONE       = 'done'
    ERROR      = 'error'
    STATUS_CHOICES = [
        (PENDING,    _('Pendente')),
        (PROCESSING, _('Processando')),
        (DONE,       _('Concluído')),
        (ERROR,      _('Erro')),
    ]

    file_index  = models.ForeignKey(FileIndex, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.IntegerField(_('índice do chunk'))
    row_start   = models.IntegerField(_('linha inicial'))
    row_end     = models.IntegerField(_('linha final'))
    # Conteúdo em formato CSV (header + linhas do chunk)
    content     = models.TextField(_('conteúdo'))
    # Embedding vetorial do conteúdo (pgvector — 1536 dims para text-embedding-3-small)
    embedding   = models.JSONField(_('embedding'), null=True, blank=True)
    status      = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default=PENDING)
    # Resumo do que foi criado/erros neste chunk
    result_summary = models.JSONField(_('resultado'), null=True, blank=True)
    error_detail   = models.TextField(_('detalhe do erro'), blank=True)
    created_at  = models.DateTimeField(_('criado em'), auto_now_add=True)

    class Meta:
        verbose_name = _('Chunk de Arquivo')
        verbose_name_plural = _('Chunks de Arquivo')
        ordering = ['file_index', 'chunk_index']
        unique_together = [('file_index', 'chunk_index')]

    def __str__(self):
        return f'Chunk {self.chunk_index} de {self.file_index.file_name} (linhas {self.row_start}–{self.row_end})'
