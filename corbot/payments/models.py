"""
Modelos para controle de pagamentos e grupos de comissionamento.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

from core.models import User, Company
from bank.models import Bank, Table


# Removendo a importação circular
# from proposals.models import Proposal


class CommissionRules(models.Model):
    """
    Modelo para representar as regras de comissão.
    Usadas em CommissionGroupByCompany (teto da promotora para o corban) e
    em CommissionGroup tipo promotora (taxa única da promotora para o corban).
    """
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name=_("Banco"), null=True, default=None)
    table = models.ForeignKey(Table, on_delete=models.CASCADE, verbose_name=_("Tabela"), null=True, default=None)
    commission_range = models.ForeignKey(
        'bank.CommissionRange',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='commission_rules',
        verbose_name=_("Faixa de Comissionamento")
    )
    commission_rate = models.DecimalField(_("Taxa de Comissão"), max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)],default=0)
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)
    is_active = models.BooleanField(_("Ativo"), default=True)

    def get_config(self):
        return {
            "id": self.id,
            "bank": self.bank.id if self.bank else None,
            "table": self.table.id if self.table else None,
            "commission_range": self.commission_range.id if self.commission_range else None,
            "commission_rate": self.commission_rate
        }
    
    class Meta:
        verbose_name = _("Regra de Comissão")
        verbose_name_plural = _("Regras de Comissão")
    

class CommissionRulesByUser(models.Model):
    """
    Modelo para representar as regras de comissão por usuário.
    Usadas em CommissionGroup tipo corban (define split vendedor/líder).
    """
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, verbose_name=_("Banco"), null=True, default=None)
    table = models.ForeignKey(Table, on_delete=models.CASCADE, verbose_name=_("Tabela"), null=True, default=None)
    commission_range = models.ForeignKey(
        'bank.CommissionRange',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='commission_rules_by_user',
        verbose_name=_("Faixa de Comissionamento")
    )
    leader_commission_rate = models.DecimalField(_("Taxa de Comissão para Líder"), max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)],default=0)
    seller_commission_rate = models.DecimalField(_("Taxa de Comissão para Vendedor"), max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)],default=0)
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)
    is_active = models.BooleanField(_("Ativo"), default=True)

    def get_config(self):
        return {
            "id": self.id,
            "bank": self.bank.id if self.bank else None,
            "table": self.table.id if self.table else None,
            "commission_range": self.commission_range.id if self.commission_range else None,
            "leader_commission_rate": self.leader_commission_rate,
            "seller_commission_rate": self.seller_commission_rate
        }
class CommissionGroup(models.Model):
    """
    Modelo para representar um grupo de comissionamento.
    O grupo de comissionamento define as regras e porcentagens para comissões
    aplicadas aos vendedores e líderes.
    """
    name = models.CharField(_("Nome"), max_length=100)
    description = models.TextField(_("Descrição"), blank=True, null=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="comission_groups_single",
        verbose_name=_("Empresa"),
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(_("Ativo"), default=True)
    
    commission_rules = models.ManyToManyField(
        CommissionRulesByUser,
        verbose_name=_("Regras de Comissão (Corban)"),
        blank=True
    )

    promotora_rules = models.ManyToManyField(
        CommissionRules,
        related_name='promotora_groups',
        verbose_name=_("Regras de Comissão (Promotora)"),
        blank=True
    )

    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)

    sellers = models.ManyToManyField(
        User,
        related_name="comission_groups",
        verbose_name=_("Vendedores"),
        blank=True
    )
    
    leaders = models.ManyToManyField(
        User,
        related_name="leader_groups",
        verbose_name=_("Líderes"),
        blank=True
    )
    
    color = models.CharField(_("Cor"), max_length=7, default='#ffff')
    
    by_leader = models.BooleanField(_("Por Líder"), default=False)
    leader = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="leader_groups_single",
        verbose_name=_("Líder"),
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _("Grupo de Comissionamento")
        verbose_name_plural = _("Grupos de Comissionamento")
        ordering = ['-created_at']

    def __str__(self):
        return self.name
    
    def get_config(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "color": self.color,
            "by_leader": self.by_leader,
            "leader": self.leader.id if self.leader else None,
            "commission_rules": [rule.get_config() for rule in self.commission_rules.all()],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

class CommissionGroupByCompany(models.Model):
    """
    Modelo para representar um grupo de comissionamento por empresa.
    """
    name = models.CharField(_("Nome"), max_length=100)
    description = models.TextField(_("Descrição"), blank=True, null=True)
    
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)
    
    companies = models.ManyToManyField(
        Company,
        related_name="comission_groups_multi",  # Nome alterado para evitar conflito
        verbose_name=_("Empresas"),
        blank=True
    )
    is_active = models.BooleanField(_("Ativo"), default=True)
    color = models.CharField(_("Cor"), max_length=7, default='#ffff')
    
    comission_rules = models.ManyToManyField(
        CommissionRules,
        verbose_name=_("Regras de Comissão"),
        blank=True
    )
    
    def get_config(self):
        return {
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "color": self.color,
            "comission_rules": [rule.get_config() for rule in self.comission_rules.all()],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    class Meta:
        verbose_name = _("Grupo de Comissionamento por Empresa")
        verbose_name_plural = _("Grupos de Comissionamento por Empresa")
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class Payment(models.Model):
    """
    Modelo para representar um pagamento a um usuário.
    Cada pagamento está associado a um período e contém a soma das comissões
    do usuário naquele período.
    """
    PENDING = 'pending'
    APPROVED = 'approved'
    PAID = 'paid'
    REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (PENDING, _('Pendente')),
        (APPROVED, _('Aprovado')),
        (PAID, _('Pago')),
        (REJECTED, _('Rejeitado')),
    ]
    
    MANUAL = 'manual'
    WITHDRAW = 'withdraw'
    
    METHOD_CHOICES = [
        (MANUAL, _('Manual')),
        (WITHDRAW, _('Saque')),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="payments",
        verbose_name=_("Usuário")
    )
   
    total_amount = models.DecimalField(
        _("Valor Total"), 
        max_digits=10, 
        decimal_places=2
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING
    )
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        related_name="approved_payments",
        verbose_name=_("Aprovado por"),
        null=True, 
        blank=True
    )
    approved_at = models.DateTimeField(_("Aprovado em"), null=True, blank=True)
    paid_at = models.DateTimeField(_("Pago em"), null=True, blank=True)
    payment_method = models.CharField(_("Método de Pagamento"), max_length=50, choices=METHOD_CHOICES, default=None, null=True, blank=True)
    payment_details = models.JSONField(_("Detalhes do Pagamento"), blank=True, null=True)
    notes = models.TextField(_("Observações"), blank=True, null=True)
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)

    class Meta:
        verbose_name = _("Pagamento")
        verbose_name_plural = _("Pagamentos")
        ordering = ['-created_at']

    def __str__(self):
        return f"Pagamento {self.id}: {self.user}"


class CommissionConfig(models.Model):
    """
    Modelo para representar uma configuração de comissão.
    """
    commision_group_company_config = models.JSONField(_("Configuração do Grupo de Comissionamento por Empresa"), blank=True, null=True)
    commision_group_user_config = models.JSONField(_("Configuração do Grupo de Comissionamento por Usuário"), blank=True, null=True)
    table_config = models.JSONField(_("Configuração da Tabela"), blank=True, null=True)

    
    
class Commission(models.Model):
    """
    Modelo para representar uma comissão individual.
    Cada comissão está associada a uma proposta e a um usuário.
    """
    VENDEDOR = 'vendedor'
    LIDER = 'lider'
    EMPRESA = 'empresa'
    
    ROLE_CHOICES = [
        (VENDEDOR, _('Vendedor')),
        (LIDER, _('Líder')),
        (EMPRESA, _('Empresa')),
    ]
    
    # Status de liberação
    NOT_RELEASED = 'not_released'
    WITHDRAW_AVAILABLE = 'withdraw_available'
    PENDING_MANUAL_PAYMENT = 'pending_manual_payment'
    PAID = 'paid'
    
    RELEASE_STATUS_CHOICES = [
        (NOT_RELEASED, _('Não liberado')),
        (WITHDRAW_AVAILABLE, _('Saque liberado')),
        (PENDING_MANUAL_PAYMENT, _('Aguardando pagamento')),
        (PAID, _('Pago')),
    ]
    
    # Usando referência de string para evitar importação circular
    proposal = models.ForeignKey(
        'proposals.Proposal', 
        on_delete=models.CASCADE, 
        related_name="commissions",
        verbose_name=_("Proposta")
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="commissions",
        verbose_name=_("Usuário"),
        null=True,
        blank=True
    )
    company = models.ForeignKey(
        'core.Company', 
        on_delete=models.CASCADE, 
        related_name="commissions",
        verbose_name=_("Empresa"),
        null=True,
        blank=True
    )
    role = models.CharField(
        _("Função"),
        max_length=20,
        choices=ROLE_CHOICES
    )
    percentage = models.DecimalField(
        _("Porcentagem"), 
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    value = models.DecimalField(
        _("Valor"), 
        max_digits=10, 
        decimal_places=2
    )
    payment = models.ForeignKey(
        Payment, 
        on_delete=models.SET_NULL, 
        related_name="commissions",
        verbose_name=_("Pagamento"),
        null=True,
        blank=True
    )
    commission_config = models.ForeignKey(
        CommissionConfig, 
        on_delete=models.SET_NULL, 
        related_name="commissions",
        verbose_name=_("Configuração de Comissão"),
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)
    paid_at = models.DateTimeField(_("Pago em"), null=True, blank=True)
    paid_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="paid_commissions",
        verbose_name=_("Pago por"),
        null=True,
        blank=True
    )
    released = models.BooleanField(_("Liberado"), default=False)
    released_at = models.DateTimeField(_("Liberado em"), null=True, blank=True)
    released_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="released_commissions",
        verbose_name=_("Liberado por"),
        null=True,
        blank=True
    )
    release_status = models.CharField(
        _("Status de liberação"),
        max_length=30,
        choices=RELEASE_STATUS_CHOICES,
        default=NOT_RELEASED
    )
    
    class Meta:
        verbose_name = _("Comissão")
        verbose_name_plural = _("Comissões")
        ordering = ['-created_at']

    def __str__(self):
        return f"Comissão: {self.proposal} - {self.get_role_display()}"


class PaymentManual(models.Model):
    """
    Modelo para representar um pagamento manual.
    """
    payments = models.ManyToManyField(Payment, verbose_name=_("Pagamentos"))
    file = models.FileField(_("Arquivo"), upload_to='payments/manual/', blank=True, null=True)
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)
    paid_at = models.DateTimeField(_("Pago em"), null=True, blank=True)
    paid_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="paid_manual_payments",
        verbose_name=_("Pago por"),
        null=True,
        blank=True
    )
    class Meta:
        verbose_name = _("Pagamento Manual")
        verbose_name_plural = _("Pagamentos Manuais")
        ordering = ['-created_at']

class Withdraw(models.Model):
    """
    Modelo para representar um saque.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Usuário"))
    amount = models.DecimalField(_("Valor"), max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, verbose_name=_("Pagamento"))
    
    class Meta:
        verbose_name = _("Saque")
        verbose_name_plural = _("Saques")
        ordering = ['-created_at']

    def __str__(self):
        return f"Saque: {self.user} - {self.amount}"


class CorbanPayTransaction(models.Model):
    """
    Rastreia o ciclo de vida de um pré-pagamento no CorbanPay.

    Fluxo:
      pending → active (pré-pagamento criado + token gerado)
              → withdrawn (saque realizado pelo recebedor)
              → failed (erro em qualquer etapa)
    """
    PENDING = 'pending'
    ACTIVE = 'active'
    WITHDRAWN = 'withdrawn'
    FAILED = 'failed'

    STATUS_CHOICES = [
        (PENDING, _('Pendente')),
        (ACTIVE, _('Ativo – aguardando saque')),
        (WITHDRAWN, _('Sacado')),
        (FAILED, _('Falhou')),
    ]

    withdraw = models.OneToOneField(
        Withdraw,
        on_delete=models.CASCADE,
        related_name='corbanpay_transaction',
        verbose_name=_("Saque"),
    )
    receiver_id = models.CharField(_("ID do Recebedor (CorbanPay)"), max_length=100)
    pre_payment_id = models.CharField(
        _("ID do Pré-Pagamento (CorbanPay)"), max_length=100, blank=True, default=""
    )
    withdrawal_link = models.TextField(_("Link de Saque"), blank=True, default="")
    status = models.CharField(
        _("Status"), max_length=20, choices=STATUS_CHOICES, default=PENDING
    )
    error_message = models.TextField(_("Mensagem de erro"), blank=True, default="")
    created_at = models.DateTimeField(_("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Atualizado em"), auto_now=True)

    class Meta:
        verbose_name = _("Transação CorbanPay")
        verbose_name_plural = _("Transações CorbanPay")
        ordering = ['-created_at']

    def __str__(self):
        return f"CorbanPay #{self.id} – {self.withdraw.user} – {self.get_status_display()}"