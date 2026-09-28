"""
Registro de sinistros em propostas.

Dois cenários:

1. Fraude confirmada: a proposta foi paga e o cliente comprovou fraude. Gera
   débito no corban da proposta, no valor da proposta.
2. Pago ao corban errado: o valor foi pago ao corban errado e ele não estornou.
   Marca as comissões dele como "sinistro", debita o que já tinha sido pago,
   aponta a proposta para o corban correto e cria uma comissão nova no nome
   dele, em "aguardando pagamento".
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils.timezone import now

from core.models import Company, User
from payments.models import Commission, ProposalClaim, UserDebit
from payments.services.debits import apply_debits

ZERO = Decimal('0')


class ClaimError(Exception):
    """Erro de regra de negócio ao registrar um sinistro."""


def _proposal_commissions(proposal):
    return Commission.objects.filter(proposal=proposal).select_related('user', 'company')


def _sum_values(commissions) -> Decimal:
    total = sum((Decimal(str(item.value or 0)) for item in commissions), ZERO)
    return total


def _company_payee(company: Company):
    """Usuário que recebe pelo corban; Payment exige usuário para gerar o lote."""
    return (
        company.users.filter(role=User.EMPRESA_ADMIN, is_active=True)
        .order_by('id')
        .first()
    )


@transaction.atomic
def register_fraud_claim(proposal, actor: User, description: str = '') -> ProposalClaim:
    """Fraude confirmada: debita o valor da proposta no corban que a originou."""
    if not proposal.company_id:
        raise ClaimError('A proposta não tem corban vinculado para receber o débito.')

    amount = Decimal(str(proposal.amount or 0))
    if amount <= ZERO:
        raise ClaimError('A proposta não tem valor para gerar o débito do sinistro.')

    reference = proposal.contract_number or str(proposal.id)
    debit = UserDebit.objects.create(
        company=proposal.company,
        amount=amount,
        remaining_amount=amount,
        reason=f'Sinistro - fraude confirmada (proposta {reference})',
        origin=UserDebit.SINISTRO,
        created_by=actor,
    )

    return ProposalClaim.objects.create(
        proposal=proposal,
        claim_type=ProposalClaim.FRAUD,
        description=description,
        amount=amount,
        debit=debit,
        charged_company=proposal.company,
        created_by=actor,
    )


@transaction.atomic
def register_wrong_corban_claim(
    proposal,
    actor: User,
    correct_company: Company,
    description: str = '',
) -> ProposalClaim:
    """
    Pago ao corban errado: marca as comissões do corban errado como sinistro e
    gera uma comissão nova no nome do corban correto.

    O débito só cobre o que realmente saiu (comissões já pagas). O que ainda
    estava na fila apenas vira sinistro, porque nada foi desembolsado ali e
    cobrar seria cobrar duas vezes.
    """
    wrong_company = proposal.company
    if not wrong_company:
        raise ClaimError('A proposta não tem corban vinculado.')
    if correct_company.id == wrong_company.id:
        raise ClaimError('O corban correto precisa ser diferente do corban que recebeu o valor.')

    commissions = list(
        _proposal_commissions(proposal)
        .filter(company=wrong_company)
        .exclude(release_status=Commission.SINISTRO)
    )
    if not commissions:
        raise ClaimError('A proposta não tem comissões geradas para este corban.')

    amount = _sum_values(commissions)
    if amount <= ZERO:
        raise ClaimError('A proposta não tem valor de comissão para transferir.')

    paid_amount = _sum_values(
        [item for item in commissions if item.release_status == Commission.PAID]
    )

    reference = proposal.contract_number or str(proposal.id)
    debit = None
    if paid_amount > ZERO:
        debit = UserDebit.objects.create(
            company=wrong_company,
            amount=paid_amount,
            remaining_amount=paid_amount,
            reason=f'Sinistro - pago ao corban errado (proposta {reference})',
            origin=UserDebit.SINISTRO,
            created_by=actor,
        )

    company_commission = next(
        (item for item in commissions if item.role == Commission.EMPRESA), None
    )

    Commission.objects.filter(id__in=[item.id for item in commissions]).update(
        release_status=Commission.SINISTRO,
    )

    # Comissão do corban correto: o recebedor é o corban, o usuário é só quem
    # assina o pagamento por ele.
    new_commission = Commission.objects.create(
        proposal=proposal,
        user=_company_payee(correct_company),
        company=correct_company,
        role=Commission.EMPRESA,
        percentage=(company_commission.percentage if company_commission else ZERO),
        value=amount,
        gross_value=amount,
        commission_config=(company_commission.commission_config if company_commission else None),
        release_status=Commission.PENDING_MANUAL_PAYMENT,
        released=True,
        released_at=now(),
        released_by=actor,
    )

    proposal.company = correct_company
    proposal.save(update_fields=['company'])

    # Já sai líquido dos débitos pendentes do corban correto, como numa liberação.
    apply_debits(
        Commission.objects.filter(id=new_commission.id).select_related('user', 'company')
    )

    return ProposalClaim.objects.create(
        proposal=proposal,
        claim_type=ProposalClaim.WRONG_CORBAN,
        description=description,
        amount=amount,
        debit=debit,
        charged_company=wrong_company,
        correct_company=correct_company,
        created_by=actor,
    )


def register_claim(
    proposal,
    claim_type: str,
    actor: User,
    description: str = '',
    correct_company_id=None,
) -> ProposalClaim:
    if claim_type == ProposalClaim.FRAUD:
        return register_fraud_claim(proposal, actor, description)

    if claim_type == ProposalClaim.WRONG_CORBAN:
        if not correct_company_id:
            raise ClaimError('Informe o corban correto para este tipo de sinistro.')
        try:
            correct_company = Company.objects.get(id=correct_company_id)
        except Company.DoesNotExist:
            raise ClaimError('Corban correto não encontrado.')
        return register_wrong_corban_claim(proposal, actor, correct_company, description)

    raise ClaimError('Tipo de sinistro inválido.')
