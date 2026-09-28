"""
Filtros, projeção de débito e consolidação da listagem de comissões.

Centraliza o que antes vivia dentro da view para que listagem, consolidado e
exportação usem exatamente o mesmo recorte.
"""
from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.timezone import make_aware, now

from core.models import User
from core.search_utils import split_filter_values
from payments.models import Commission
from payments.services.debits import project_debits

ZERO = Decimal('0')

DEBIT_WITH = 'with_debit'
DEBIT_WITHOUT = 'without_debit'
DEBIT_ZEROED = 'zeroed'
DEBIT_FILTERS = {DEBIT_WITH, DEBIT_WITHOUT, DEBIT_ZEROED}


def commission_date_bounds(request) -> tuple[datetime, datetime]:
    """Intervalo de datas com timezone (evita lista vazia por naive/aware)."""
    begin = now() - timedelta(days=90)
    end = now()

    for raw, is_begin in ((request.GET.get('begin_date'), True), (request.GET.get('end_date'), False)):
        if not raw:
            continue
        parsed = parse_datetime(raw)
        if not parsed:
            only_date = parse_date(raw)
            if only_date:
                boundary = datetime.min.time() if is_begin else datetime.max.time()
                parsed = make_aware(datetime.combine(only_date, boundary))
        if parsed:
            if is_begin:
                begin = parsed
            else:
                end = parsed

    return begin, end


def scope_commissions(actor: User, commissions):
    """Recorta a listagem conforme o papel do usuário. Retorna None se não pode ver."""
    if actor.role == User.VENDEDOR:
        return commissions.filter(
            user=actor,
            release_status__in=[Commission.WITHDRAW_AVAILABLE, Commission.PENDING_MANUAL_PAYMENT],
        )
    if actor.role == User.LIDER:
        return commissions.filter(Q(user=actor) | Q(user__leader=actor))
    if actor.role == User.GERENTE:
        if actor.company_id:
            return commissions.filter(user__company=actor.company)
        return commissions.filter(user=actor)
    if actor.role == User.EMPRESA_ADMIN:
        if actor.company_id:
            return commissions.filter(company=actor.company)
        return commissions
    if actor.role == User.GERENTE_COMERCIAL:
        from commercial.services import team_company_ids_for
        company_ids = team_company_ids_for(actor)
        return commissions.filter(
            Q(company_id__in=company_ids)
            | Q(user__company_id__in=company_ids)
            | Q(proposal__company_id__in=company_ids)
        ).distinct()
    if actor.role == User.ADMIN:
        return commissions
    return None


def apply_commission_filters(request, commissions):
    """Aplica os filtros de querystring (sem os de débito, que dependem da projeção)."""
    params = request.GET

    if params.get('client_document'):
        commissions = commissions.filter(proposal__client_document=params['client_document'])
    if params.get('client_name'):
        commissions = commissions.filter(proposal__client_name=params['client_name'])
    if params.get('user'):
        commissions = commissions.filter(user_id=params['user'])
    if params.get('company'):
        commissions = commissions.filter(company_id=params['company'])
    if params.get('role'):
        commissions = commissions.filter(role=params['role'])
    if params.get('payment_id'):
        commissions = commissions.filter(payment_id=params['payment_id'])
    if params.get('proposal_id'):
        commissions = commissions.filter(proposal_id=params['proposal_id'])

    release_status = params.get('release_status') or params.get('status')
    if release_status:
        commissions = commissions.filter(release_status=release_status)

    if params.get('payment_status'):
        commissions = commissions.filter(payment__status=params['payment_status'])

    matriculas = split_filter_values(params.get('matricula'))
    if matriculas:
        matricula_filter = Q()
        for value in matriculas:
            matricula_filter |= Q(proposal__seller__matricula__icontains=value)
        commissions = commissions.filter(matricula_filter)

    documents = split_filter_values(params.get('client_documents'))
    if documents:
        document_filter = Q()
        for value in documents:
            digits = ''.join(char for char in value if char.isdigit())
            document_filter |= Q(proposal__client_document__icontains=digits or value)
        commissions = commissions.filter(document_filter)

    contracts = split_filter_values(params.get('contract_numbers'))
    if contracts:
        contract_filter = Q()
        for value in contracts:
            contract_filter |= Q(proposal__contract_number__icontains=value)
        commissions = commissions.filter(contract_filter)

    search = (params.get('search') or '').strip()
    if search:
        commissions = commissions.filter(
            Q(proposal__client_name__icontains=search)
            | Q(proposal__client_document__icontains=search)
            | Q(proposal__contract_number__icontains=search)
            | Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__cpf__icontains=search)
            | Q(company__name__icontains=search)
        )

    return commissions


def commission_queryset(request):
    """Queryset completa (escopo + filtros) já ordenada. Retorna None se sem permissão."""
    begin_date, end_date = commission_date_bounds(request)
    commissions = (
        Commission.objects.filter(created_at__gte=begin_date, created_at__lte=end_date)
        .select_related('proposal', 'proposal__seller', 'proposal__bank', 'proposal__table',
                        'user', 'company', 'payment')
    )

    commissions = scope_commissions(request.user, commissions)
    if commissions is None:
        return None

    return apply_commission_filters(request, commissions).order_by('-created_at')


def commission_amounts(commission: Commission, projection: dict) -> tuple[Decimal, Decimal, Decimal]:
    """(total, débito, líquido) da comissão, usando o abatimento real ou o projetado."""
    applied = Decimal(str(commission.debit_discount or 0))
    value = Decimal(str(commission.value or 0))

    if applied > ZERO:
        total = Decimal(str(commission.gross_value or 0)) or (value + applied)
        return total, applied, value

    entry = projection.get(commission.id)
    debit = Decimal(str(entry['debit'])) if entry else ZERO
    return value, debit, max(ZERO, value - debit)


def build_debit_projection(commissions) -> dict:
    """Projeção de abatimento apenas para as comissões que ainda não foram abatidas."""
    pending = [
        commission for commission in commissions
        if Decimal(str(commission.debit_discount or 0)) <= ZERO
    ]
    return project_debits(pending) if pending else {}


def filter_by_debit(commissions: list, projection: dict, debit_filter: str | None) -> list:
    """Aplica os filtros "Com débito", "Sem débito" e "Zerados" em memória."""
    if debit_filter not in DEBIT_FILTERS:
        return commissions

    result = []
    for commission in commissions:
        _, debit, net = commission_amounts(commission, projection)
        if debit_filter == DEBIT_WITH and debit > ZERO:
            result.append(commission)
        elif debit_filter == DEBIT_WITHOUT and debit <= ZERO:
            result.append(commission)
        elif debit_filter == DEBIT_ZEROED and debit > ZERO and net <= ZERO:
            result.append(commission)
    return result


def recipient_key(commission: Commission):
    """Agrupa pelo recebedor do pagamento: corban nas comissões de empresa, usuário nas demais."""
    if commission.role == Commission.EMPRESA and commission.company_id:
        return ('company', str(commission.company_id))
    if commission.user_id:
        return ('user', str(commission.user_id))
    if commission.company_id:
        return ('company', str(commission.company_id))
    return ('none', '0')


def recipient_info(commission: Commission) -> dict:
    kind, identifier = recipient_key(commission)
    if kind == 'company':
        company = commission.company
        return {
            'type': 'company',
            'id': identifier,
            'name': company.name if company else '-',
            'document': company.document if company else None,
        }
    user = commission.user
    return {
        'type': 'user',
        'id': identifier,
        'name': (user.get_full_name() or user.username) if user else '-',
        'document': user.cpf if user else None,
    }


def commission_row(commission: Commission, projection: dict) -> dict:
    """Linha compacta usada no modal de detalhes e no relatório detalhado."""
    total, debit, net = commission_amounts(commission, projection)
    proposal = commission.proposal
    return {
        'id': commission.id,
        'proposal_id': str(proposal.id) if proposal else None,
        'contract_number': proposal.contract_number if proposal else None,
        'client_name': proposal.client_name if proposal else None,
        'client_document': proposal.client_document if proposal else None,
        'proposal_amount': str(proposal.amount or ZERO) if proposal else '0',
        'bank_name': proposal.bank.name if proposal and proposal.bank_id else None,
        'table_name': (proposal.table.name_in_bank or proposal.table.name)
                      if proposal and proposal.table_id else None,
        'matricula': proposal.seller.matricula if proposal and proposal.seller_id else None,
        'role': commission.role,
        'role_display': commission.get_role_display(),
        'percentage': str(commission.percentage or ZERO),
        'total_value': str(total),
        'debit_value': str(debit),
        'net_value': str(net),
        'is_zeroed': debit > ZERO and net <= ZERO,
        'release_status': commission.release_status,
        'created_at': commission.created_at.isoformat() if commission.created_at else None,
    }


def consolidation_key(commission: Commission):
    """Chave do consolidado: recebedor + status. Status diferentes nunca se somam."""
    kind, identifier = recipient_key(commission)
    return (kind, identifier, commission.release_status or Commission.NOT_RELEASED)


def consolidate_commissions(commissions: list, projection: dict) -> list[dict]:
    """Soma as comissões por recebedor e status, mantendo os ids que compõem cada linha."""
    groups: OrderedDict = OrderedDict()

    for commission in commissions:
        key = consolidation_key(commission)
        total, debit, net = commission_amounts(commission, projection)

        group = groups.get(key)
        if group is None:
            group = {
                'key': f'{key[0]}:{key[1]}:{key[2]}',
                'recipient': recipient_info(commission),
                'release_status': key[2],
                'release_status_display': commission.get_release_status_display(),
                'total_value': ZERO,
                'debit_value': ZERO,
                'net_value': ZERO,
                'commissions_count': 0,
                'commission_ids': [],
                'items': [],
                'roles': set(),
                'companies': set(),
            }
            groups[key] = group

        group['total_value'] += total
        group['debit_value'] += debit
        group['net_value'] += net
        group['commissions_count'] += 1
        group['commission_ids'].append(commission.id)
        group['items'].append(commission_row(commission, projection))
        group['roles'].add(commission.get_role_display())
        if commission.company_id:
            group['companies'].add(commission.company.name)

    rows = []
    for group in groups.values():
        rows.append({
            'key': group['key'],
            'recipient': group['recipient'],
            'release_status': group['release_status'],
            'release_status_display': group['release_status_display'],
            'total_value': str(group['total_value']),
            'debit_value': str(group['debit_value']),
            'net_value': str(group['net_value']),
            'is_zeroed': group['debit_value'] > ZERO and group['net_value'] <= ZERO,
            'commissions_count': group['commissions_count'],
            'commission_ids': group['commission_ids'],
            'items': group['items'],
            'roles': sorted(group['roles']),
            'companies': sorted(group['companies']),
        })

    rows.sort(key=lambda row: (row['recipient']['name'].lower(), row['release_status']))
    return rows


def totals_from(commissions: list, projection: dict) -> dict:
    total = debit = net = ZERO
    zeroed = 0
    for commission in commissions:
        item_total, item_debit, item_net = commission_amounts(commission, projection)
        total += item_total
        debit += item_debit
        net += item_net
        if item_debit > ZERO and item_net <= ZERO:
            zeroed += 1
    return {
        'total_value': str(total),
        'debit_value': str(debit),
        'net_value': str(net),
        'commissions_count': len(commissions),
        'zeroed_count': zeroed,
    }
