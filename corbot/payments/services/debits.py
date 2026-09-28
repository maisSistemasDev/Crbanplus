"""
Abatimento de débitos em comissões.

O débito é abatido no momento da liberação/pagamento do lote, não na geração da
comissão. Até ser liberada, a comissão guarda o valor cheio em `value`; a
projeção abaixo mostra quanto seria abatido se o lote fosse liberado agora.

Dono do débito:
  - comissão de Empresa  -> o corban (`commission.company`)
  - comissão de vendedor/líder -> o usuário (`commission.user`)
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import Q

from payments.models import Commission, CommissionDebitDiscount, UserDebit

OWNER_USER = 'user'
OWNER_COMPANY = 'company'

ZERO = Decimal('0')

Owner = tuple[str, int]


def debit_owner(commission: Commission) -> Owner | None:
    """Quem responde pelo débito desta comissão."""
    if commission.role == Commission.EMPRESA:
        return (OWNER_COMPANY, commission.company_id) if commission.company_id else None
    if commission.user_id:
        return (OWNER_USER, commission.user_id)
    if commission.company_id:
        return (OWNER_COMPANY, commission.company_id)
    return None


def _payable_value(commission: Commission) -> Decimal:
    """Valor ainda pagável da comissão (já líquido de abatimentos anteriores)."""
    return Decimal(str(commission.value or 0))


def _pending_debits(owners: list[Owner], lock: bool = False):
    if not owners:
        return UserDebit.objects.none()

    user_ids = [owner_id for kind, owner_id in owners if kind == OWNER_USER]
    company_ids = [owner_id for kind, owner_id in owners if kind == OWNER_COMPANY]

    owner_filter: Q | None = None
    if user_ids:
        owner_filter = Q(user_id__in=user_ids)
    if company_ids:
        company_q = Q(company_id__in=company_ids)
        owner_filter = company_q if owner_filter is None else owner_filter | company_q
    if owner_filter is None:
        return UserDebit.objects.none()

    debits = UserDebit.objects.filter(owner_filter, is_active=True, remaining_amount__gt=0)
    if lock:
        debits = debits.select_for_update()
    return debits.order_by('created_at', 'id')


def _group_by_owner(commissions) -> dict[Owner, list[Commission]]:
    grouped: dict[Owner, list[Commission]] = defaultdict(list)
    for commission in commissions:
        owner = debit_owner(commission)
        if owner:
            grouped[owner].append(commission)
    for items in grouped.values():
        items.sort(key=lambda item: (item.created_at, item.id))
    return grouped


def project_debits(commissions) -> dict[int, dict[str, Decimal]]:
    """
    Simula o abatimento (sem gravar nada) para o conjunto de comissões recebido.

    Retorna {commission_id: {'debit': Decimal, 'net': Decimal, 'items': [...]}}
    apenas para as comissões que teriam algum abatimento. Cada item traz o
    débito de origem, para alimentar o modal de detalhes.
    """
    commissions = list(commissions)
    if not commissions:
        return {}

    grouped = _group_by_owner(commissions)
    if not grouped:
        return {}

    balances: dict[Owner, list[tuple[int, Decimal]]] = defaultdict(list)
    for debit in _pending_debits(list(grouped.keys())):
        owner: Owner = (
            (OWNER_COMPANY, debit.company_id) if debit.company_id else (OWNER_USER, debit.user_id)
        )
        balances[owner].append((debit.id, Decimal(str(debit.remaining_amount))))

    projection: dict[int, dict] = {}
    for owner, owner_commissions in grouped.items():
        pending = balances.get(owner)
        if not pending:
            continue

        index = 0
        for commission in owner_commissions:
            remaining = _payable_value(commission)
            if remaining <= ZERO:
                continue

            applied = ZERO
            items: list[dict] = []
            while index < len(pending) and remaining > ZERO:
                debit_id, available = pending[index]
                if available <= ZERO:
                    index += 1
                    continue
                discount = min(remaining, available)
                pending[index] = (debit_id, available - discount)
                applied += discount
                remaining -= discount
                items.append({'debit_id': debit_id, 'amount': discount})
                if pending[index][1] <= ZERO:
                    index += 1

            if applied > ZERO:
                projection[commission.id] = {
                    'debit': applied,
                    'net': _payable_value(commission) - applied,
                    'items': items,
                }

    return projection


@transaction.atomic
def apply_debits(commissions) -> dict[str, object]:
    """
    Abate de verdade os débitos pendentes nas comissões informadas.

    Consome `UserDebit.remaining_amount`, registra `CommissionDebitDiscount` e
    atualiza `gross_value`, `debit_discount` e `value` da comissão.
    """
    commissions = list(commissions)
    if not commissions:
        return {'applied_total': ZERO, 'affected': 0, 'zeroed_ids': []}

    grouped = _group_by_owner(commissions)
    if not grouped:
        return {'applied_total': ZERO, 'affected': 0, 'zeroed_ids': []}

    debits_by_owner: dict[Owner, list[UserDebit]] = defaultdict(list)
    for debit in _pending_debits(list(grouped.keys()), lock=True):
        owner: Owner = (
            (OWNER_COMPANY, debit.company_id) if debit.company_id else (OWNER_USER, debit.user_id)
        )
        debits_by_owner[owner].append(debit)

    applied_total = ZERO
    affected = 0
    zeroed_ids: list[int] = []

    for owner, owner_commissions in grouped.items():
        pending = debits_by_owner.get(owner)
        if not pending:
            continue

        index = 0
        for commission in owner_commissions:
            original = _payable_value(commission)
            remaining = original
            if remaining <= ZERO:
                continue

            applied = ZERO
            while index < len(pending) and remaining > ZERO:
                debit = pending[index]
                available = Decimal(str(debit.remaining_amount))
                if available <= ZERO:
                    index += 1
                    continue

                discount = min(remaining, available)
                debit.remaining_amount = available - discount
                if debit.remaining_amount <= ZERO:
                    debit.remaining_amount = ZERO
                    debit.is_active = False
                    index += 1
                debit.save(update_fields=['remaining_amount', 'is_active', 'updated_at'])

                CommissionDebitDiscount.objects.create(
                    commission=commission,
                    debit=debit,
                    amount=discount,
                )

                applied += discount
                remaining -= discount

            if applied <= ZERO:
                continue

            if commission.gross_value is None:
                commission.gross_value = original
            commission.debit_discount = Decimal(str(commission.debit_discount or 0)) + applied
            commission.value = remaining
            commission.save(update_fields=['gross_value', 'debit_discount', 'value', 'updated_at'])

            applied_total += applied
            affected += 1
            if remaining <= ZERO:
                zeroed_ids.append(commission.id)

    return {'applied_total': applied_total, 'affected': affected, 'zeroed_ids': zeroed_ids}


@transaction.atomic
def revert_debits(commissions) -> dict[str, object]:
    """
    Desfaz abatimentos já aplicados, devolvendo saldo ao débito de origem.

    Usado ao cancelar um pagamento: a comissão volta a valer o valor cheio e o
    débito volta a ficar pendente para o próximo lote.
    """
    commissions = list(commissions)
    if not commissions:
        return {'reverted_total': ZERO, 'affected': 0}

    discounts = (
        CommissionDebitDiscount.objects
        .select_for_update()
        .filter(commission__in=commissions)
        .select_related('debit')
    )

    restored_by_commission: dict[int, Decimal] = defaultdict(lambda: ZERO)
    touched_debits: dict[int, UserDebit] = {}
    discount_ids: list[int] = []

    for discount in discounts:
        amount = Decimal(str(discount.amount))
        debit = touched_debits.setdefault(discount.debit_id, discount.debit)
        debit.remaining_amount = Decimal(str(debit.remaining_amount)) + amount
        debit.is_active = True
        restored_by_commission[discount.commission_id] += amount
        discount_ids.append(discount.id)

    if not restored_by_commission:
        return {'reverted_total': ZERO, 'affected': 0}

    for debit in touched_debits.values():
        debit.save(update_fields=['remaining_amount', 'is_active', 'updated_at'])

    CommissionDebitDiscount.objects.filter(id__in=discount_ids).delete()

    reverted_total = ZERO
    for commission in commissions:
        restored = restored_by_commission.get(commission.id)
        if not restored:
            continue
        commission.value = _payable_value(commission) + restored
        commission.debit_discount = max(
            ZERO, Decimal(str(commission.debit_discount or 0)) - restored
        )
        commission.save(update_fields=['debit_discount', 'value', 'updated_at'])
        reverted_total += restored

    return {'reverted_total': reverted_total, 'affected': len(restored_by_commission)}
