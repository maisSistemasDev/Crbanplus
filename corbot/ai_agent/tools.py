"""
Ferramentas (function calling) disponíveis para o agente IA.

Cada ferramenta é registrada em TOOL_DEFINITIONS (formato OpenAI/Anthropic)
e tem uma função Python correspondente em TOOL_HANDLERS.

Ferramentas implementadas:
  - list_banks           → lista bancos ativos
  - get_bank             → detalhes de um banco (tabelas + convênios)
  - list_agreements      → lista convênios
  - list_tables          → lista tabelas (filtro por banco/convênio)
  - get_table            → detalhes de uma tabela com faixas
  - update_table         → atualiza taxa/vigência/faixas de uma tabela
  - create_table         → cria nova tabela
  - update_agreement     → atualiza convênio
"""
import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)

# ─── Definições das ferramentas (schema JSON) ────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_banks",
            "description": "Lista todos os bancos parceiros ativos no sistema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "active_only": {
                        "type": "boolean",
                        "description": "Se true, retorna apenas bancos ativos. Padrão: true.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_bank",
            "description": "Retorna detalhes de um banco específico incluindo seus convênios e tabelas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bank_id": {
                        "type": "string",
                        "description": "UUID do banco.",
                    }
                },
                "required": ["bank_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_agreements",
            "description": "Lista os convênios disponíveis (INSS, FGTS, Siape, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "active_only": {
                        "type": "boolean",
                        "description": "Se true, retorna apenas convênios ativos. Padrão: true.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "Lista tabelas de comissionamento, opcionalmente filtradas por banco ou convênio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bank_id": {
                        "type": "string",
                        "description": "UUID do banco para filtrar tabelas.",
                    },
                    "agreement_id": {
                        "type": "string",
                        "description": "UUID do convênio para filtrar tabelas.",
                    },
                    "active_only": {
                        "type": "boolean",
                        "description": "Se true, retorna apenas tabelas ativas. Padrão: true.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_table",
            "description": "Retorna detalhes completos de uma tabela, incluindo faixas de comissionamento.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_id": {
                        "type": "string",
                        "description": "UUID da tabela.",
                    }
                },
                "required": ["table_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_table",
            "description": (
                "Atualiza dados de uma tabela existente. "
                "Pode atualizar taxa de comissão, data de vigência, se está ativa "
                "e as faixas de comissionamento. "
                "Passe apenas os campos que deseja alterar."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "table_id": {
                        "type": "string",
                        "description": "UUID da tabela a atualizar.",
                    },
                    "commission_rate": {
                        "type": "number",
                        "description": "Nova taxa de comissionamento (percentual, ex: 2.5).",
                    },
                    "vigency_date": {
                        "type": "string",
                        "description": "Nova data de vigência no formato YYYY-MM-DD.",
                    },
                    "is_active": {
                        "type": "boolean",
                        "description": "Ativar ou desativar a tabela.",
                    },
                    "min_value": {
                        "type": "number",
                        "description": "Valor mínimo de operação.",
                    },
                    "max_value": {
                        "type": "number",
                        "description": "Valor máximo de operação.",
                    },
                    "name_in_bank": {
                        "type": "string",
                        "description": "Nome da tabela no sistema do banco.",
                    },
                    "commission_ranges": {
                        "type": "array",
                        "description": (
                            "Faixas de comissionamento. "
                            "Se informado, SUBSTITUI todas as faixas existentes."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "min_value": {"type": "number"},
                                "max_value": {"type": "number"},
                                "commission_rate": {"type": "number"},
                            },
                            "required": ["min_value", "max_value", "commission_rate"],
                        },
                    },
                },
                "required": ["table_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_table",
            "description": "Cria uma nova tabela de comissionamento para um banco e convênio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bank_id": {"type": "string", "description": "UUID do banco."},
                    "agreement_id": {"type": "string", "description": "UUID do convênio."},
                    "name_in_bank": {"type": "string", "description": "Nome da tabela no banco."},
                    "commission_rate": {"type": "number", "description": "Taxa base de comissão (%)."},
                    "vigency_date": {"type": "string", "description": "Data de vigência YYYY-MM-DD."},
                    "min_value": {"type": "number"},
                    "max_value": {"type": "number"},
                    "commission_ranges": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "min_value": {"type": "number"},
                                "max_value": {"type": "number"},
                                "commission_rate": {"type": "number"},
                            },
                            "required": ["min_value", "max_value", "commission_rate"],
                        },
                    },
                },
                "required": ["bank_id", "agreement_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_agreement",
            "description": "Atualiza informações de um convênio (nome, descrição, status).",
            "parameters": {
                "type": "object",
                "properties": {
                    "agreement_id": {"type": "string", "description": "UUID do convênio."},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "is_active": {"type": "boolean"},
                },
                "required": ["agreement_id"],
            },
        },
    },
]

# ─── Handlers ────────────────────────────────────────────────────────────────


def _to_dec(val) -> Decimal:
    try:
        return Decimal(str(val))
    except (InvalidOperation, TypeError):
        return Decimal("0")


def _table_summary(table) -> dict:
    return {
        "id": str(table.id),
        "bank": table.bank.name,
        "agreement": table.agreement.name,
        "name_in_bank": table.name_in_bank,
        "commission_rate": str(table.commission_rate) if table.commission_rate else None,
        "vigency_date": str(table.vigency_date),
        "is_active": table.is_active,
        "min_value": str(table.min_value) if table.min_value else None,
        "max_value": str(table.max_value) if table.max_value else None,
        "commission_ranges": [
            {
                "min_value": str(r.min_value),
                "max_value": str(r.max_value),
                "commission_rate": str(r.commission_rate),
            }
            for r in table.commission_ranges.order_by("min_value")
        ],
    }


def tool_list_banks(active_only: bool = True) -> dict:
    from bank.models import Bank
    qs = Bank.objects.prefetch_related("agreements")
    if active_only:
        qs = qs.filter(is_active=True)
    banks = [
        {
            "id": str(b.id),
            "name": b.name,
            "code": b.code,
            "agreements": [a.name for a in b.agreements.all()],
        }
        for b in qs
    ]
    return {"banks": banks, "total": len(banks)}


def tool_get_bank(bank_id: str) -> dict:
    from bank.models import Bank
    try:
        bank = Bank.objects.prefetch_related("agreements", "tables__agreement", "tables__commission_ranges").get(pk=bank_id)
    except Bank.DoesNotExist:
        return {"error": f"Banco {bank_id} não encontrado."}
    return {
        "id": str(bank.id),
        "name": bank.name,
        "code": bank.code,
        "is_active": bank.is_active,
        "agreements": [{"id": str(a.id), "name": a.name} for a in bank.agreements.all()],
        "tables": [_table_summary(t) for t in bank.tables.all()],
    }


def tool_list_agreements(active_only: bool = True) -> dict:
    from bank.models import Agreement
    qs = Agreement.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    agreements = [
        {"id": str(a.id), "name": a.name, "description": a.description, "is_active": a.is_active}
        for a in qs
    ]
    return {"agreements": agreements, "total": len(agreements)}


def tool_list_tables(bank_id: str = None, agreement_id: str = None, active_only: bool = True) -> dict:
    from bank.models import Table
    qs = Table.objects.select_related("bank", "agreement").prefetch_related("commission_ranges")
    if active_only:
        qs = qs.filter(is_active=True)
    if bank_id:
        qs = qs.filter(bank_id=bank_id)
    if agreement_id:
        qs = qs.filter(agreement_id=agreement_id)
    tables = [_table_summary(t) for t in qs]
    return {"tables": tables, "total": len(tables)}


def tool_get_table(table_id: str) -> dict:
    from bank.models import Table
    try:
        table = Table.objects.select_related("bank", "agreement").prefetch_related("commission_ranges").get(pk=table_id)
    except Table.DoesNotExist:
        return {"error": f"Tabela {table_id} não encontrada."}
    return _table_summary(table)


def tool_update_table(
    table_id: str,
    commission_rate: float = None,
    vigency_date: str = None,
    is_active: bool = None,
    min_value: float = None,
    max_value: float = None,
    name_in_bank: str = None,
    commission_ranges: list = None,
) -> dict:
    from bank.models import Table, CommissionRange, TableHistory

    try:
        table = Table.objects.select_related("bank", "agreement").get(pk=table_id)
    except Table.DoesNotExist:
        return {"error": f"Tabela {table_id} não encontrada."}

    updated_fields = []

    if commission_rate is not None:
        table.commission_rate = _to_dec(commission_rate)
        updated_fields.append("commission_rate")
    if vigency_date is not None:
        from datetime import date
        try:
            table.vigency_date = date.fromisoformat(vigency_date)
            updated_fields.append("vigency_date")
        except ValueError:
            return {"error": f"Data inválida: {vigency_date}. Use YYYY-MM-DD."}
    if is_active is not None:
        table.is_active = is_active
        updated_fields.append("is_active")
    if min_value is not None:
        table.min_value = _to_dec(min_value)
        updated_fields.append("min_value")
    if max_value is not None:
        table.max_value = _to_dec(max_value)
        updated_fields.append("max_value")
    if name_in_bank is not None:
        table.name_in_bank = name_in_bank
        updated_fields.append("name_in_bank")

    if updated_fields:
        table.save(update_fields=updated_fields)

    if commission_ranges is not None:
        table.commission_ranges.all().delete()
        ranges_to_create = [
            CommissionRange(
                table=table,
                min_value=_to_dec(r["min_value"]),
                max_value=_to_dec(r["max_value"]),
                commission_rate=_to_dec(r["commission_rate"]),
            )
            for r in commission_ranges
        ]
        CommissionRange.objects.bulk_create(ranges_to_create)
        updated_fields.append("commission_ranges")

    # Registra no histórico
    try:
        TableHistory.objects.create(
            table=table,
            action="UPDATE",
            changed_by=None,
            snapshot=table.get_config(),
            notes=f"Atualizado pelo agente IA. Campos: {', '.join(updated_fields)}",
        )
    except Exception as exc:
        logger.warning("Não foi possível registrar TableHistory: %s", exc)

    return {
        "success": True,
        "updated_fields": updated_fields,
        "table": _table_summary(table),
    }


def tool_create_table(
    bank_id: str,
    agreement_id: str,
    name_in_bank: str = None,
    commission_rate: float = None,
    vigency_date: str = None,
    min_value: float = None,
    max_value: float = None,
    commission_ranges: list = None,
) -> dict:
    from bank.models import Table, CommissionRange, TableHistory, Bank, Agreement
    from datetime import date

    try:
        bank = Bank.objects.get(pk=bank_id)
    except Bank.DoesNotExist:
        return {"error": f"Banco {bank_id} não encontrado."}
    try:
        agreement = Agreement.objects.get(pk=agreement_id)
    except Agreement.DoesNotExist:
        return {"error": f"Convênio {agreement_id} não encontrado."}

    vdate = date.today()
    if vigency_date:
        try:
            vdate = date.fromisoformat(vigency_date)
        except ValueError:
            return {"error": f"Data inválida: {vigency_date}"}

    table = Table.objects.create(
        bank=bank,
        agreement=agreement,
        name_in_bank=name_in_bank or "",
        commission_rate=_to_dec(commission_rate) if commission_rate else None,
        vigency_date=vdate,
        min_value=_to_dec(min_value) if min_value else None,
        max_value=_to_dec(max_value) if max_value else None,
    )

    if commission_ranges:
        CommissionRange.objects.bulk_create([
            CommissionRange(
                table=table,
                min_value=_to_dec(r["min_value"]),
                max_value=_to_dec(r["max_value"]),
                commission_rate=_to_dec(r["commission_rate"]),
            )
            for r in commission_ranges
        ])

    try:
        TableHistory.objects.create(
            table=table,
            action="CREATE",
            snapshot=table.get_config(),
            notes="Criada pelo agente IA.",
        )
    except Exception as exc:
        logger.warning("Não foi possível registrar TableHistory: %s", exc)

    return {"success": True, "table": _table_summary(table)}


def tool_update_agreement(
    agreement_id: str,
    name: str = None,
    description: str = None,
    is_active: bool = None,
) -> dict:
    from bank.models import Agreement
    try:
        agreement = Agreement.objects.get(pk=agreement_id)
    except Agreement.DoesNotExist:
        return {"error": f"Convênio {agreement_id} não encontrado."}

    updated = []
    if name is not None:
        agreement.name = name
        updated.append("name")
    if description is not None:
        agreement.description = description
        updated.append("description")
    if is_active is not None:
        agreement.is_active = is_active
        updated.append("is_active")

    if updated:
        agreement.save(update_fields=updated)

    return {
        "success": True,
        "updated_fields": updated,
        "agreement": {"id": str(agreement.id), "name": agreement.name, "is_active": agreement.is_active},
    }


# ─── Despachador ─────────────────────────────────────────────────────────────

TOOL_HANDLERS: dict[str, Any] = {
    "list_banks": tool_list_banks,
    "get_bank": tool_get_bank,
    "list_agreements": tool_list_agreements,
    "list_tables": tool_list_tables,
    "get_table": tool_get_table,
    "update_table": tool_update_table,
    "create_table": tool_create_table,
    "update_agreement": tool_update_agreement,
}


def dispatch_tool(name: str, arguments: str | dict) -> str:
    """
    Executa a ferramenta `name` com os argumentos fornecidos.
    Retorna string JSON com o resultado.
    """
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return json.dumps({"error": f"Ferramenta '{name}' não existe."})

    if isinstance(arguments, str):
        try:
            kwargs = json.loads(arguments)
        except json.JSONDecodeError:
            return json.dumps({"error": "Argumentos inválidos (JSON malformado)."})
    else:
        kwargs = arguments

    try:
        result = handler(**kwargs)
        return json.dumps(result, default=str, ensure_ascii=False)
    except Exception as exc:
        logger.exception("Erro ao executar ferramenta '%s': %s", name, exc)
        return json.dumps({"error": str(exc)})
