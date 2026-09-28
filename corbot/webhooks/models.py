import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel, User


def generate_webhook_secret() -> str:
    return f'whk_{secrets.token_urlsafe(32)}'


class WebhookEndpoint(TimeStampedModel):
    """Endpoint inbound: sistemas externos enviam JSON para criar lotes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('nome'), max_length=120)
    bank = models.ForeignKey(
        'bank.Bank',
        on_delete=models.CASCADE,
        related_name='webhook_endpoints',
        verbose_name=_('banco'),
    )
    layout = models.ForeignKey(
        'proposals.Layout',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='webhook_endpoints',
        verbose_name=_('layout'),
    )
    secret_token = models.CharField(_('token secreto'), max_length=80, editable=False)
    items_path = models.CharField(
        _('caminho dos itens no JSON'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('Ex.: $.data ou $.items. Vazio = objeto raiz ou lista na raiz.'),
    )
    mappings = models.JSONField(_('mapeamento de campos'), default=list, blank=True)
    is_active = models.BooleanField(_('ativo'), default=True)
    auto_process = models.BooleanField(
        _('processar lote automaticamente'),
        default=True,
        help_text=_('Dispara o pipeline ao criar um novo lote do dia (não ao acrescentar linhas).'),
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='webhook_endpoints',
        verbose_name=_('criado por'),
    )

    class Meta:
        verbose_name = _('webhook')
        verbose_name_plural = _('webhooks')
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.secret_token:
            self.secret_token = generate_webhook_secret()
        super().save(*args, **kwargs)

    def inbound_path(self) -> str:
        return f'/api/webhooks/inbound/{self.id}/'

    def inbound_url(self, request=None) -> str:
        path = self.inbound_path()
        if request:
            return request.build_absolute_uri(path)
        public = getattr(settings, 'PUBLIC_API_BASE_URL', '').rstrip('/')
        if public:
            return f'{public}{path}'
        return path


class WebhookDailyBatch(TimeStampedModel):
    """Rastreia o lote diário aberto por banco (webhook)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank = models.ForeignKey(
        'bank.Bank',
        on_delete=models.CASCADE,
        related_name='webhook_daily_batches',
        verbose_name=_('banco'),
    )
    batch_date = models.DateField(_('data do lote'))
    proposal_batch = models.ForeignKey(
        'proposals.ProposalBatch',
        on_delete=models.CASCADE,
        related_name='webhook_daily_batch',
        verbose_name=_('lote'),
    )
    layout = models.ForeignKey(
        'proposals.Layout',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='webhook_daily_batches',
        verbose_name=_('layout'),
    )

    class Meta:
        verbose_name = _('lote diário de webhook')
        verbose_name_plural = _('lotes diários de webhook')
        ordering = ['-batch_date', '-created_at']
        indexes = [
            models.Index(fields=['bank', 'batch_date']),
        ]

    def __str__(self):
        return f'{self.bank_id} — {self.batch_date}'


class WebhookDelivery(TimeStampedModel):
    STATUS_RECEIVED = 'received'
    STATUS_MAPPED = 'mapped'
    STATUS_BATCH_CREATED = 'batch_created'
    STATUS_APPENDED = 'appended'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_RECEIVED, _('Recebido')),
        (STATUS_MAPPED, _('Mapeado')),
        (STATUS_BATCH_CREATED, _('Lote criado')),
        (STATUS_APPENDED, _('Linhas adicionadas ao lote')),
        (STATUS_FAILED, _('Falhou')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    endpoint = models.ForeignKey(
        WebhookEndpoint,
        on_delete=models.CASCADE,
        related_name='deliveries',
        verbose_name=_('webhook'),
    )
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default=STATUS_RECEIVED)
    raw_payload = models.JSONField(_('payload bruto'))
    mapped_rows = models.JSONField(_('linhas mapeadas'), default=list, blank=True)
    items_count = models.PositiveIntegerField(_('itens'), default=0)
    proposal_batch = models.ForeignKey(
        'proposals.ProposalBatch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='webhook_deliveries',
        verbose_name=_('lote'),
    )
    error_message = models.TextField(_('erro'), blank=True)
    source_ip = models.GenericIPAddressField(_('IP de origem'), null=True, blank=True)
    batch_created = models.BooleanField(
        _('novo lote criado'),
        default=False,
        help_text=_('False quando as linhas foram acrescentadas a um lote aberto do dia.'),
    )

    class Meta:
        verbose_name = _('entrega de webhook')
        verbose_name_plural = _('entregas de webhook')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.endpoint.name} @ {self.created_at:%Y-%m-%d %H:%M}'
