"""
Celery tasks do app ai_agent.

Fase 1 (sem LLM): gera sugestão determinística baseada no limite da promotora.
Quando o PydanticAI for integrado, basta substituir _build_suggestion_data().
"""
import logging
from decimal import Decimal

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def compute_message_embedding(self, message_pk: int, api_key: str):
    """Computa e armazena embedding vetorial de uma mensagem (para contexto longo)."""
    try:
        from .llm import compute_and_store_embedding
        compute_and_store_embedding(message_pk, api_key)
    except Exception as exc:
        logger.warning("compute_message_embedding falhou para msg %s: %s", message_pk, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_suggestions_for_table(self, table_id: str, history_id: str):
    """
    Para cada CommissionGroup que usa a tabela atualizada:
      1. Calcula o limite máximo da promotora (CommissionGroupByCompany).
      2. Gera uma sugestão proporcional (50% líder / 50% vendedor do limite).
      3. Salva como TableUpdateSuggestion (status=pending).
      4. Envia push notification para os responsáveis.
    """
    try:
        from bank.models import Table, TableHistory
        from payments.models import CommissionGroup, CommissionGroupByCompany, CommissionRulesByUser
        from ai_agent.models import TableUpdateSuggestion
        from core.models import User

        table = Table.objects.select_related('bank', 'agreement').get(id=table_id)
        history = TableHistory.objects.get(pk=history_id)

        # Grupos que possuem regras para esta tabela
        groups = CommissionGroup.objects.filter(
            commission_rules__table=table
        ).distinct().select_related('company', 'leader')

        for group in groups:
            _process_group(group, table, history)

    except Exception as exc:
        logger.exception('Erro em generate_suggestions_for_table: %s', exc)
        raise self.retry(exc=exc)


def _process_group(group, table, history):
    from payments.models import CommissionGroupByCompany
    from ai_agent.models import TableUpdateSuggestion
    from core.models import User

    # Limite da promotora para esta tabela
    promotora_limit = _get_promotora_limit(group, table)

    # Configuração atual do grupo para esta tabela
    old_rules = list(
        group.commission_rules.filter(table=table).values(
            'id', 'bank_id', 'table_id',
            'leader_commission_rate', 'seller_commission_rate',
            'commission_range_id',
        )
    )

    if not old_rules and promotora_limit == Decimal('0'):
        return  # nada a sugerir

    suggested_config, reasoning = _build_suggestion_data(old_rules, promotora_limit, table)

    suggestion = TableUpdateSuggestion.objects.create(
        commission_group=group,
        table=table,
        table_history=history,
        old_config=_serialize_decimals(old_rules),
        suggested_config=_serialize_decimals(suggested_config),
        ai_reasoning=reasoning,
    )

    _notify_group_owner(group, table, suggestion)


def _get_promotora_limit(group, table) -> Decimal:
    """Retorna a taxa máxima que a promotora permite para este grupo/tabela."""
    from payments.models import CommissionGroupByCompany

    if not group.company_id:
        return Decimal('0')

    company_group = CommissionGroupByCompany.objects.filter(
        companies=group.company, is_active=True
    ).first()

    if not company_group:
        return Decimal('0')

    rule = company_group.comission_rules.filter(
        table=table, commission_range__isnull=True
    ).first()

    return Decimal(str(rule.commission_rate)) if rule else Decimal('0')


def _build_suggestion_data(old_rules, promotora_limit: Decimal, table):
    """
    Fase 1: lógica determinística — divide o limite 50/50 entre líder e vendedor.
    Fase 2: substituir por chamada PydanticAI.
    """
    if promotora_limit == Decimal('0'):
        return old_rules, 'Sem limite de promotora definido; configuração mantida.'

    half = (promotora_limit / 2).quantize(Decimal('0.01'))
    remainder = promotora_limit - half  # garante que soma == limite

    if old_rules:
        suggested = []
        for rule in old_rules:
            suggested.append({
                **rule,
                'leader_commission_rate': float(half),
                'seller_commission_rate': float(remainder),
            })
    else:
        suggested = [{
            'bank_id': str(table.bank_id),
            'table_id': str(table.pk),
            'commission_range_id': None,
            'leader_commission_rate': float(half),
            'seller_commission_rate': float(remainder),
        }]

    reasoning = (
        f'Tabela "{table.name_in_bank}" atualizada (banco: {table.bank.name}). '
        f'Limite da promotora: {promotora_limit}%. '
        f'Sugestão automática: Líder {half}% / Vendedor {remainder}% '
        f'(divisão igualitária do limite). Revise conforme sua estratégia comercial.'
    )
    return suggested, reasoning


def _serialize_decimals(data):
    """Converte Decimal para float para serialização JSON."""
    if isinstance(data, list):
        return [_serialize_decimals(item) for item in data]
    if isinstance(data, dict):
        return {k: _serialize_decimals(v) for k, v in data.items()}
    if isinstance(data, Decimal):
        return float(data)
    return data


def _notify_group_owner(group, table, suggestion):
    """Envia push notification para o responsável pelo grupo."""
    from core.models import User, PushSubscription
    from core.push_signals import send_push

    user_ids = set()

    if group.by_leader and group.leader_id:
        user_ids.add(group.leader_id)
    elif group.company_id:
        admins = User.objects.filter(
            company_id=group.company_id,
            role=User.EMPRESA_ADMIN,
        ).values_list('id', flat=True)
        user_ids.update(admins)

    if not user_ids:
        return

    subs = PushSubscription.objects.filter(user_id__in=user_ids)
    for sub in subs:
        send_push(
            sub,
            title='Tabela atualizada 📋',
            body=(
                f'A tabela "{table.name_in_bank}" foi atualizada. '
                f'Uma sugestão de configuração está disponível para o grupo "{group.name}".'
            ),
            url='/commission-groups',
        )
