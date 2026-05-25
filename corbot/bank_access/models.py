import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedModel, User, Company
from bank.models import Bank


class BankAccess(TimeStampedModel):
    """
    Modelo para representar acessos aos sistemas dos bancos parceiros.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, related_name='bank_accesses')
    username = models.CharField(_('usuário'), max_length=255)
    password = models.CharField(_('senha'), max_length=255)
    is_active = models.BooleanField(_('ativo'), default=True)
    alias = models.JSONField(_('Vínculos'), default=list, blank=True)
    # Usuário associado (vendedor que utiliza este acesso)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                            related_name='bank_accesses', verbose_name=_('vendedor'))
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                  related_name='created_bank_accesses', verbose_name=_('criado por'))
    
    class Meta:
        verbose_name = _('acesso bancário')
        verbose_name_plural = _('acessos bancários')
        ordering = ['bank__name', 'username']
        unique_together = ('bank', 'username')
    
    def __str__(self):
        return f"{self.bank.name} - {self.username}"


class AccessLog(TimeStampedModel):
    """
    Modelo para registrar logs de acesso aos sistemas bancários.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_access = models.ForeignKey(BankAccess, on_delete=models.CASCADE, related_name='access_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='bank_access_logs')
    
    # Informações do acesso
    access_time = models.DateTimeField(_('horário de acesso'), auto_now_add=True)
    ip_address = models.GenericIPAddressField(_('endereço IP'), null=True, blank=True)
    user_agent = models.TextField(_('user agent'), null=True, blank=True)
    
    # Status e resultado
    status = models.CharField(_('status'), max_length=50)
    details = models.TextField(_('detalhes'), blank=True, null=True)
    
    # Dados adicionais
    data = models.JSONField(_('dados'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('log de acesso')
        verbose_name_plural = _('logs de acesso')
        ordering = ['-access_time']
    
    def __str__(self):
        return f"{self.bank_access} - {self.access_time.strftime('%d/%m/%Y %H:%M:%S')}" 