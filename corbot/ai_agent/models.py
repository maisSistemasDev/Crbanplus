from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import User


class Conversation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ai_conversations',
        verbose_name=_('usuário'),
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
