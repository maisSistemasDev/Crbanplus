import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel, User
from bank.models import Bank


def default_flow_definition():
    return {
        'nodes': [
            {
                'id': 'trigger-1',
                'type': 'schedule_trigger',
                'position': {'x': 0, 'y': 120},
                'data': {
                    'schedule_mode': 'weekdays',
                    'schedule_time': '08:00',
                    'schedule_weekdays': [1, 2, 3, 4, 5],
                    'cron': '0 8 * * 1-5',
                    'timezone': 'America/Sao_Paulo',
                    'label': 'Agendamento',
                },
            },
            {
                'id': 'http-1',
                'type': 'http_request',
                'position': {'x': 280, 'y': 120},
                'data': {
                    'auth_type': 'none',
                    'auth_config': {},
                    'method': 'GET',
                    'url': '',
                    'headers': {},
                    'query_params': {},
                    'label': 'HTTP Request',
                },
            },
            {
                'id': 'extract-1',
                'type': 'extract_items',
                'position': {'x': 560, 'y': 120},
                'data': {'items_path': '$.data', 'label': 'Extrair lista'},
            },
            {
                'id': 'map-1',
                'type': 'map_fields',
                'position': {'x': 840, 'y': 120},
                'data': {'mappings': [], 'label': 'Mapear campos'},
            },
            {
                'id': 'batch-1',
                'type': 'create_batch',
                'position': {'x': 1120, 'y': 120},
                'data': {'layout_id': '', 'bank_id': '', 'label': 'Criar lote'},
            },
        ],
        'edges': [
            {'id': 'e1', 'source': 'trigger-1', 'target': 'http-1'},
            {'id': 'e2', 'source': 'http-1', 'target': 'extract-1'},
            {'id': 'e3', 'source': 'extract-1', 'target': 'map-1'},
            {'id': 'e4', 'source': 'map-1', 'target': 'batch-1'},
        ],
        'viewport': {'x': 0, 'y': 0, 'zoom': 1},
    }


class ProposalEtlFlow(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('nome'), max_length=255)
    bank = models.ForeignKey(
        Bank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='etl_flows',
        verbose_name=_('banco'),
    )
    is_active = models.BooleanField(_('ativo'), default=False)
    shared_auth_enabled = models.BooleanField(
        _('autenticação compartilhada'),
        default=False,
        help_text=_('Reutiliza a mesma sessão de auth em todos os nós HTTP a cada execução.'),
    )
    shared_auth_type = models.CharField(
        _('tipo de auth compartilhada'),
        max_length=64,
        default='none',
        blank=True,
    )
    shared_auth_config = models.JSONField(
        _('configuração de auth compartilhada'),
        default=dict,
        blank=True,
    )
    flow_definition = models.JSONField(
        _('definição do fluxo'),
        default=default_flow_definition,
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_etl_flows',
        verbose_name=_('criado por'),
    )

    class Meta:
        verbose_name = _('fluxo ETL')
        verbose_name_plural = _('fluxos ETL')
        ordering = ['-updated_at']

    def __str__(self):
        return self.name


class ProposalEtlRun(TimeStampedModel):
    STATUS_RUNNING = 'running'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_RUNNING, _('Executando')),
        (STATUS_SUCCESS, _('Sucesso')),
        (STATUS_FAILED, _('Falhou')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    flow = models.ForeignKey(
        ProposalEtlFlow,
        on_delete=models.CASCADE,
        related_name='runs',
        verbose_name=_('fluxo'),
    )
    proposal_batch = models.ForeignKey(
        'proposals.ProposalBatch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='etl_runs',
        verbose_name=_('lote criado'),
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RUNNING,
    )
    started_at = models.DateTimeField(_('início'), auto_now_add=True)
    finished_at = models.DateTimeField(_('fim'), null=True, blank=True)
    fetched_count = models.PositiveIntegerField(_('itens obtidos'), default=0)
    rows_written = models.PositiveIntegerField(_('linhas gravadas'), default=0)
    node_outputs = models.JSONField(_('outputs dos nós'), default=dict, blank=True)
    execution_log = models.JSONField(_('log de execução'), default=list, blank=True)
    trigger_source = models.CharField(
        _('origem do disparo'),
        max_length=20,
        default='manual',
        blank=True,
        help_text=_('manual ou schedule'),
    )
    error_message = models.TextField(_('erro'), blank=True, null=True)
    error_node_id = models.CharField(_('nó com erro'), max_length=64, blank=True, null=True)
    celery_task_id = models.CharField(
        _('ID da tarefa Celery'),
        max_length=255,
        blank=True,
        null=True,
    )
    connector_log = models.ForeignKey(
        'core.ConnectorLog',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='etl_runs',
    )

    class Meta:
        verbose_name = _('execução ETL')
        verbose_name_plural = _('execuções ETL')
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.flow.name} — {self.started_at:%d/%m/%Y %H:%M}'


class ProposalEtlBankProfile(TimeStampedModel):
    """Configuração ETL reutilizável por banco (paginação, auth, URLs, detalhes)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank = models.OneToOneField(
        Bank,
        on_delete=models.CASCADE,
        related_name='etl_profile',
        verbose_name=_('banco'),
    )
    settings = models.JSONField(
        _('configurações'),
        default=dict,
        blank=True,
        help_text=_('Defaults por tipo de nó: paginate_http, extract_items, detail_steps[]'),
    )
    notes = models.TextField(_('observações'), blank=True)

    class Meta:
        verbose_name = _('perfil ETL do banco')
        verbose_name_plural = _('perfis ETL dos bancos')

    def __str__(self):
        return f'ETL — {self.bank.name}'
