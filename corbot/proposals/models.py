import uuid
import os
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedModel, User, Company
from bank.models import Bank, Agreement, Table
import datetime
from django.utils import timezone
"""
Proposal File: Arquivo de proposta, caso a proposta venha de upload de arquivo.
Proposal: Salva as propostas, que vêm do arquivo de proposta.
Layout: Layout do arquivo de proposta, que define os campos do arquivo.
Layout Field: Campo do layout do arquivo de proposta.
"""

def proposal_file_path(instance, filename):
    """Define o caminho para salvar os arquivos de proposta."""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('proposals', str(instance.company.id), filename)


class ProposalFile(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to='proposals/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class LayoutField(TimeStampedModel):
    DATATYPE_TEXT = 'text'
    DATATYPE_NUMBER = 'number'
    DATATYPE_CURRENCY = 'currency'
    DATATYPE_DECIMAL = 'decimal'
    DATATYPE_DATETIME = 'datetime'
    DATATYPE_DATE = 'date'
    DATATYPE_CPF = 'cpf'
    DATATYPE_BOOLEAN = 'boolean'
    DATATYPE_EMAIL = 'email'
    DATATYPE_PHONE = 'phone'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(verbose_name=_("Nome"), max_length=255)
    data_type = models.CharField(verbose_name=_("Tipo de dado"), max_length=255)
    index = models.IntegerField(verbose_name=_("Índice"))
    header_name = models.CharField(verbose_name=_("Nome do cabeçalho"), max_length=255)
    
    def __str__(self):
        return f"{self.name} - {self.data_type} - {self.index} - {self.header_name}"
    

class Layout(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank = models.ForeignKey(verbose_name=_("Banco"), to=Bank, on_delete=models.CASCADE)
    name = models.CharField(verbose_name=_("Nome"), max_length=255, default="Layout")
    map_fields = models.ManyToManyField(verbose_name=_("Campos"), to=LayoutField, related_name='layouts')
    
    def __str__(self):
        return f"{self.bank.name} - {self.map_fields.count()} fields"

class ProposalBatch(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(verbose_name=_("Arquivo"), to=ProposalFile, on_delete=models.CASCADE)
    layout = models.ForeignKey(verbose_name=_("Layout"), to=Layout, on_delete=models.CASCADE)
    status = models.CharField(verbose_name=_("Status"), max_length=255, default="pending")
    processed_at = models.DateTimeField(verbose_name=_("Data de processamento"), null=True, blank=True)
    error_message = models.TextField(verbose_name=_("Mensagem de erro"), null=True, blank=True)
    processed_rows = models.IntegerField(verbose_name=_("Linhas processadas"), default=0)
    errored_rows = models.IntegerField(verbose_name=_("Linhas com erro"), default=0)
    total_rows = models.IntegerField(verbose_name=_("Total de linhas"), default=0)
    task_id = models.CharField(verbose_name=_("ID da tarefa Celery"), max_length=255, null=True, blank=True)
    etl_run = models.ForeignKey(
        'proposal_etl.ProposalEtlRun',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='batches',
        verbose_name=_('execução ETL'),
    )

    def __str__(self):
        return f"{self.file.file.name} - {self.layout.bank.name} - {self.layout.map_fields.count()} fields"

class Proposal(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(
        verbose_name=_("Vendedor"),
        to=User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proposals_as_seller',
    )
    digitador = models.CharField(
        verbose_name=_("Digitador"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Nome do digitador informado no arquivo de proposta."),
    )
    bank_access = models.ForeignKey(
        'bank_access.BankAccess',
        verbose_name=_("Acesso bancário"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proposals',
    )
    contract_number = models.CharField(verbose_name=_("Número do contrato"), max_length=255, unique=True)
    company = models.ForeignKey(verbose_name=_("Empresa"), to=Company, on_delete=models.CASCADE)
    bank = models.ForeignKey(verbose_name=_("Banco"), to=Bank, on_delete=models.CASCADE)
    agreement = models.ForeignKey(verbose_name=_("Convênio"), to=Agreement, on_delete=models.CASCADE)
    table = models.ForeignKey(verbose_name=_("Tabela"), to=Table, on_delete=models.CASCADE)
    status = models.CharField(verbose_name=_("Status"), max_length=255, default="pending")
    disbursement_date = models.DateField(verbose_name=_("Data de liberação"), default=datetime.date.today)
    amount = models.DecimalField(verbose_name=_("Valor"), max_digits=10, decimal_places=2)
    uploaded_at = models.DateTimeField(verbose_name=_("Data de upload"), default=timezone.now)
    client_document = models.CharField(verbose_name=_("CPF do cliente"), max_length=255, default="")
    client_name = models.CharField(verbose_name=_("Nome do cliente"), max_length=255, default="")
    original_data = models.JSONField(verbose_name=_("Dados originais"), default=dict)
    batch = models.ForeignKey(verbose_name=_("Lote"), to=ProposalBatch, on_delete=models.CASCADE, null=True, blank=True)
    release_date = models.DateField(verbose_name=_("Data de pagamento da operação"), default=None,null=True, blank=True)
    hash = models.CharField(verbose_name=_("Hash"), max_length=255, default=None, null=True, blank=True)
    def __str__(self):
        return f"{self.company.name} - {self.bank.name} - {self.agreement.name} - {self.table.name_in_bank}"

    
class ErroredProposal(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(verbose_name=_("Lote"), to=ProposalBatch, on_delete=models.CASCADE, null=True, blank=True)
    original_data = models.JSONField(verbose_name=_("Dados originais"), default=dict)
    error_message = models.TextField(verbose_name=_("Mensagem de erro"), null=True, blank=True)
    def __str__(self):
        return f"{self.original_data.get('company', '?')} - {self.original_data.get('bank', '?')} - {self.original_data.get('agreement', '?')} - {self.original_data.get('table', '?')}"

class BatchLogFile(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(verbose_name=_("Lote"), to=ProposalBatch, on_delete=models.CASCADE, null=True, blank=True)
    log_file = models.FileField(verbose_name=_("Arquivo de log"), upload_to='proposal_logs/')

    def __str__(self):
        return f"Log file for batch {self.batch.id} uploaded at {self.uploaded_at}"

class StatusPayment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(verbose_name=_("Nome"), max_length=255)
    alias = models.JSONField(verbose_name=_("Alias"), default=list)
    bank = models.ForeignKey(verbose_name=_("Banco"), to=Bank, on_delete=models.CASCADE)
    def __str__(self):
        return f"{self.name}"