"""
Filtros da listagem de propostas.

Listagem e exportação usam exatamente o mesmo recorte: o Excel sai com o que
está na tela, não com a página atual.
"""
from __future__ import annotations

import re
from datetime import datetime

from django.db.models import (
    Case, CharField, Func, IntegerField, OuterRef, Q, Subquery, Value, When,
)
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.timezone import is_aware, make_aware

from core.search_utils import split_filter_values
from payments.models import Commission


class StripNonDigits(Func):
    function = 'REGEXP_REPLACE'
    template = "%(function)s(%(expressions)s, '[^0-9]', '', 'g')"
    output_field = CharField()

# Mesma ordem de prioridade do ProposalSerializer: a proposta assume o status
# mais avançado entre as comissões dela.
PAYMENT_STATUS_PRIORITY = {
    Commission.SINISTRO: 0,
    Commission.NOT_RELEASED: 1,
    Commission.WITHDRAW_AVAILABLE: 2,
    Commission.PENDING_MANUAL_PAYMENT: 3,
    Commission.PAID: 4,
}

DATE_FIELDS = {
    'created_at': 'created_at',
    'disbursement_date': 'disbursement_date',
}


def _parse_boundary(raw: str | None, end_of_day: bool):
    """Aceita data ou datetime; datas viram início/fim do dia com timezone."""
    if not raw:
        return None

    parsed = parse_datetime(raw)
    if not parsed:
        only_date = parse_date(raw)
        if not only_date:
            return None
        boundary = datetime.max.time() if end_of_day else datetime.min.time()
        parsed = datetime.combine(only_date, boundary)

    return parsed if is_aware(parsed) else make_aware(parsed)


def filter_matriculas(queryset, raw: str | None):
    """Filtra por uma ou várias matrículas do vendedor (código do parceiro)."""
    values = split_filter_values(raw)
    if not values:
        return queryset
    query = Q()
    for value in values:
        query |= Q(seller__matricula__iexact=value) | Q(seller__matricula__icontains=value)
    return queryset.filter(query)


def filter_client_documents(queryset, raw: str | None):
    values = split_filter_values(raw)
    if not values:
        return queryset
    digits = [re.sub(r'\D', '', value) for value in values]
    digits = [value for value in digits if value]
    query = Q()
    for value in values:
        query |= Q(client_document__icontains=value)
    if digits:
        queryset = queryset.annotate(_doc_digits=StripNonDigits('client_document'))
        query |= Q(_doc_digits__in=digits)
    return queryset.filter(query)


def filter_contract_numbers(queryset, raw: str | None):
    values = split_filter_values(raw)
    if not values:
        return queryset
    if len(values) == 1:
        return queryset.filter(contract_number__icontains=values[0])
    query = Q()
    for value in values:
        query |= Q(contract_number__iexact=value) | Q(contract_number__icontains=value)
    return queryset.filter(query)


def annotate_payment_status(queryset):
    """Anota a prioridade do status de pagamento da proposta (maior entre as comissões)."""
    priority = Case(
        *[
            When(release_status=value, then=Value(weight))
            for value, weight in PAYMENT_STATUS_PRIORITY.items()
        ],
        default=Value(PAYMENT_STATUS_PRIORITY[Commission.NOT_RELEASED]),
        output_field=IntegerField(),
    )
    best = (
        Commission.objects.filter(proposal=OuterRef('pk'))
        .annotate(_priority=priority)
        .order_by('-_priority')
        .values('_priority')[:1]
    )
    return queryset.annotate(
        _payment_priority=Subquery(best, output_field=IntegerField())
    )


def filter_payment_status(queryset, raw: str | None):
    """Filtra pelo status de pagamento exibido na listagem."""
    if not raw or raw not in PAYMENT_STATUS_PRIORITY:
        return queryset

    queryset = annotate_payment_status(queryset)
    weight = PAYMENT_STATUS_PRIORITY[raw]

    # Proposta sem comissão nenhuma aparece como "não liberado".
    if raw == Commission.NOT_RELEASED:
        return queryset.filter(
            Q(_payment_priority=weight) | Q(_payment_priority__isnull=True)
        )
    return queryset.filter(_payment_priority=weight)


def filter_dates(queryset, begin_raw: str | None, end_raw: str | None, field_raw: str | None):
    """Período por data de cadastro ou de liberação; os limites são independentes."""
    field = DATE_FIELDS.get(field_raw or '', 'created_at')
    begin = _parse_boundary(begin_raw, end_of_day=False)
    end = _parse_boundary(end_raw, end_of_day=True)

    if field == 'disbursement_date':
        # disbursement_date é DateField: compara por data, sem horário.
        if begin:
            queryset = queryset.filter(disbursement_date__gte=begin.date())
        if end:
            queryset = queryset.filter(disbursement_date__lte=end.date())
        return queryset

    if begin:
        queryset = queryset.filter(created_at__gte=begin)
    if end:
        queryset = queryset.filter(created_at__lte=end)
    return queryset


def apply_proposal_filters(request, queryset):
    """Aplica todos os filtros de querystring da tela de propostas."""
    params = request.GET

    if params.get('bank'):
        queryset = queryset.filter(bank_id=params['bank'])
    if params.get('company'):
        queryset = queryset.filter(company_id=params['company'])
    if params.get('seller'):
        queryset = queryset.filter(seller_id=params['seller'])
    if params.get('agreement'):
        queryset = queryset.filter(agreement_id=params['agreement'])
    if params.get('table'):
        queryset = queryset.filter(table_id=params['table'])

    queryset = filter_client_documents(queryset, params.get('client_cpf'))
    queryset = filter_contract_numbers(queryset, params.get('contract_number'))
    queryset = filter_matriculas(queryset, params.get('matricula'))
    queryset = filter_payment_status(queryset, params.get('payment_status'))
    queryset = filter_dates(
        queryset,
        params.get('begin_date'),
        params.get('end_date'),
        params.get('date_field'),
    )

    search = (params.get('search') or '').strip()
    if search:
        queryset = queryset.filter(
            Q(contract_number__icontains=search)
            | Q(client_document__icontains=search)
            | Q(client_name__icontains=search)
            | Q(seller__first_name__icontains=search)
            | Q(seller__last_name__icontains=search)
            | Q(seller__matricula__icontains=search)
            | Q(company__name__icontains=search)
        )

    return queryset
