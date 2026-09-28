import uuid
import unicodedata
import re
from datetime import timedelta
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from core.models import TimeStampedModel, User


def default_vigency_date():
    return (timezone.now() + timedelta(days=1)).date()


def normalize_name(name):
    """
    Normaliza nome removendo acentos, convertendo para maiúsculas
    e removendo caracteres especiais.
    """
    if not name:
        return ""
    # Remove acentos
    name = unicodedata.normalize('NFD', name)
    name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
    # Converte para maiúsculas e remove caracteres especiais (mantém apenas letras, números e espaços)
    name = re.sub(r'[^A-Za-z0-9\s]', '', name.upper())
    # Remove espaços extras
    name = ' '.join(name.split())
    return name


def normalize_name_compact(name):
    """Igual a normalize_name, sem espaços — '25 a 100' == '25a100'."""
    return re.sub(r'\s+', '', normalize_name(name))

class Agreement(TimeStampedModel):
    """
    Modelo para representar os convênios (INSS, FGTS, etc.).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('nome'), max_length=255)
    description = models.TextField(_('descrição'), blank=True, null=True)
    is_active = models.BooleanField(_('ativo'), default=True)
    alias = models.JSONField(_('Vínculos'), default=list, blank=True)
    class Meta:
        verbose_name = _('convênio')
        verbose_name_plural = _('convênios')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
class Bank(TimeStampedModel):
    """
    Modelo para representar os bancos parceiros.
    """
    ACCESS_LOGIN_CPF = 'cpf'
    ACCESS_LOGIN_EMAIL = 'email'

    ACCESS_LOGIN_CHOICES = [
        (ACCESS_LOGIN_CPF, _('Login por CPF')),
        (ACCESS_LOGIN_EMAIL, _('Login por e-mail/outro')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('nome'), max_length=255, unique=True)
    code = models.CharField(_('código'), max_length=10, blank=True, null=True)
    logo = models.ImageField(_('logo'), upload_to='bank_logos/', blank=True, null=True)
    website = models.URLField(_('website'), blank=True, null=True)
    is_active = models.BooleanField(_('ativo'), default=True)
    access_login_type = models.CharField(
        _('tipo de login no banco'),
        max_length=10,
        choices=ACCESS_LOGIN_CHOICES,
        default=ACCESS_LOGIN_EMAIL,
        help_text=_('CPF: um acesso por usuário no banco. E-mail: vários acessos por usuário.'),
    )
    agreements = models.ManyToManyField(Agreement, related_name='banks')
    
    class Meta:
        verbose_name = _('banco')
        verbose_name_plural = _('bancos')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Table(TimeStampedModel):
    """
    Modelo para representar as tabelas de propostas.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, related_name='tables')
    agreement = models.ForeignKey(Agreement, on_delete=models.CASCADE, related_name='tables')
    is_active = models.BooleanField(_('ativo'), default=True)
    min_value = models.DecimalField(_('valor mínimo'), max_digits=10, decimal_places=2, blank=True, null=True)
    max_value = models.DecimalField(_('valor máximo'), max_digits=10, decimal_places=2, blank=True, null=True)
    commission_rate = models.DecimalField(_('taxa de comissionamento'), max_digits=5, decimal_places=2, blank=True, null=True)
    name_in_bank = models.CharField(_('nome no banco'), max_length=255, blank=True, null=True)
    code_in_bank = models.CharField(_('código da tabela'), max_length=100, blank=True, null=True)
    vigency_date = models.DateField(_('data de vigência'), default=default_vigency_date)
    alias = models.JSONField(_('Vínculos'), default=list, blank=True)
    
    
    def find_commission_range(self, amount):
        """Faixa que cobre o valor. 0–0 com comissão vale para qualquer proposta."""
        from decimal import Decimal
        amount = Decimal(str(amount))
        specific = None
        wildcard = None
        for cr in self.commission_ranges.order_by('min_value'):
            is_wildcard = cr.min_value == 0 and cr.max_value == 0
            if is_wildcard:
                has_fixed = cr.fixed_value is not None
                has_rate = cr.commission_rate not in (None, 0, Decimal('0'))
                if has_fixed or has_rate:
                    wildcard = cr
                continue
            if cr.min_value <= amount <= cr.max_value:
                specific = cr
                break
        return specific or wildcard

    def covers_amount(self, amount):
        """True se a tabela se aplica ao valor da proposta.

        Faixa 0–0 (com taxa % ou valor fixo) vale para qualquer proposta.
        Se a tabela só tem 0–0, ignora min/max legado da tabela.
        """
        from decimal import Decimal
        if self.find_commission_range(amount) is not None:
            return True
        ranges = list(self.commission_ranges.all())
        if ranges:
            only_wildcard = all(cr.min_value == 0 and cr.max_value == 0 for cr in ranges)
            return only_wildcard
        if self.min_value is None and self.max_value is None:
            return True
        amount = Decimal(str(amount))
        min_v = self.min_value or Decimal('0')
        max_v = self.max_value or Decimal('0')
        return (min_v <= amount <= max_v) or (max_v == 0 and min_v == 0)

    def get_commission_for_amount(self, amount):
        """
        Retorna ('fixed', valor_em_reais) ou ('rate', percentual).
        """
        from decimal import Decimal
        cr = self.find_commission_range(amount)
        if cr:
            if cr.fixed_value is not None:
                return 'fixed', Decimal(str(cr.fixed_value))
            return 'rate', Decimal(str(cr.commission_rate or 0))
        return 'rate', self.commission_rate or Decimal('0')

    def get_commission_rate_for_amount(self, amount):
        """
        Retorna a taxa (%) da faixa. Faixa com valor fixo devolve 0
        (use get_commission_for_amount para o valor em reais).
        """
        kind, val = self.get_commission_for_amount(amount)
        if kind == 'fixed':
            from decimal import Decimal
            return Decimal('0')
        return val

    def get_config(self):
        return {
            "id": self.id,
            "bank": self.bank.id,
            "agreement": self.agreement.id,
            "is_active": self.is_active,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "commission_rate": self.commission_rate,
            "commission_ranges": [
                {
                    "min_value": cr.min_value,
                    "max_value": cr.max_value,
                    "commission_rate": cr.commission_rate,
                    "fixed_value": cr.fixed_value,
                }
                for cr in self.commission_ranges.order_by('min_value')
            ],
            "name_in_bank": self.name_in_bank,
            "code_in_bank": self.code_in_bank,
            "vigency_date": self.vigency_date,
            "alias": self.alias
        }
    class Meta:
        verbose_name = _('tabela')
        verbose_name_plural = _('tabelas')
        ordering = ['bank__name', 'vigency_date']
    
    def __str__(self):
        return f"{self.bank.name} - {self.agreement.name} ({self.vigency_date})"


class CommissionRange(TimeStampedModel):
    """
    Faixa de comissionamento de uma tabela.
    Percentual (commission_rate) ou valor fixo em reais (fixed_value).
    min/max 0–0 aplica a qualquer valor de proposta.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='commission_ranges')
    min_value = models.DecimalField(_('valor mínimo'), max_digits=10, decimal_places=2)
    max_value = models.DecimalField(_('valor máximo'), max_digits=10, decimal_places=2)
    commission_rate = models.DecimalField(
        _('taxa de comissionamento'),
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        default=0,
    )
    fixed_value = models.DecimalField(
        _('valor fixo de comissão'),
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        default=None,
    )

    class Meta:
        verbose_name = _('faixa de comissionamento')
        verbose_name_plural = _('faixas de comissionamento')
        ordering = ['min_value']

    def __str__(self):
        if self.fixed_value is not None:
            return f"{self.table.name_in_bank} | {self.min_value}–{self.max_value}: R$ {self.fixed_value}"
        return f"{self.table.name_in_bank} | {self.min_value}–{self.max_value}: {self.commission_rate}%"


class TableHistory(TimeStampedModel):
    """
    Modelo para armazenar o histórico de atualizações das tabelas.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(
        _('ação'),
        max_length=20,
        choices=[
            ('CREATE', 'Criação'),
            ('UPDATE', 'Atualização'),
            ('CSV_IMPORT', 'Importação CSV'),
            ('CSV_UPDATE', 'Atualização via CSV'),
        ]
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='table_history',
        verbose_name=_('usuário')
    )
    
    # Campos que foram alterados
    field_changes = models.JSONField(_('alterações'), default=dict, blank=True)
    
    # Valores anteriores (snapshot do estado anterior)
    previous_values = models.JSONField(_('valores anteriores'), default=dict, blank=True)
    
    # Valores novos (snapshot do estado atual)
    new_values = models.JSONField(_('novos valores'), default=dict, blank=True)
    
    notes = models.TextField(_('observações'), blank=True, null=True)
    
    class Meta:
        verbose_name = _('histórico de tabela')
        verbose_name_plural = _('históricos de tabelas')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.table} - {self.action} em {self.created_at.strftime('%d/%m/%Y %H:%M')}" 