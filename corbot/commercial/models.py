from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import Company, TimeStampedModel, User


class CommercialTeamMember(TimeStampedModel):
    """
    Vincula um Corban (Company) à carteira ("equipe") de um Gerente Comercial.
    Somente administradores com permissão podem adicionar/remover membros.
    """
    manager = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='commercial_team_companies',
        limit_choices_to={'role': User.GERENTE_COMERCIAL},
        verbose_name=_('gerente comercial'),
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='commercial_managers',
        verbose_name=_('corban'),
    )
    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('adicionado por'),
    )

    class Meta:
        verbose_name = _('membro de equipe comercial')
        verbose_name_plural = _('membros de equipe comercial')
        ordering = ['manager__first_name', 'company__name']
        constraints = [
            models.UniqueConstraint(
                fields=['manager', 'company'],
                name='unique_commercial_team_member',
            ),
        ]

    def __str__(self):
        return f'{self.manager.cpf} → {self.company.name}'
