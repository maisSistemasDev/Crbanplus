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

from bank.models import normalize_name

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
                    "code_in_bank": {
                        "type": "string",
                        "description": "Código da tabela no banco para filtro exato ou parcial.",
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
                        "description": "UUID, código da tabela no banco ou nome da tabela a atualizar.",
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
                    "code_in_bank": {
                        "type": "string",
                        "description": "Código da tabela no banco. Pode ser vazio.",
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
                    "code_in_bank": {"type": "string", "description": "Código da tabela no banco."},
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
    {
        "type": "function",
        "function": {
            "name": "delete_agreement",
            "description": "Remove um convênio permanentemente. Também remove as tabelas vinculadas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agreement_id": {"type": "string", "description": "UUID ou nome do convênio."},
                },
                "required": ["agreement_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_agreement",
            "description": (
                "Cria um novo convênio (ex: INSS, FGTS, SIAPE). "
                "Use quando o convênio não existir no sistema e precisar ser cadastrado."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nome do convênio."},
                    "description": {"type": "string", "description": "Descrição opcional."},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "normalize_agreements",
            "description": (
                "Unifica convênios duplicados pelo nome normalizado. "
                "Mantém o primeiro convênio de cada grupo e move as tabelas e vínculos bancários dos demais para ele. "
                "Use quando o usuário informar que existem convênios duplicados no sistema."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "dry_run": {
                        "type": "boolean",
                        "description": "Se true, apenas simula e retorna o plano sem alterar dados.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_table",
            "description": "Remove uma tabela permanentemente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_id": {"type": "string", "description": "UUID, código ou nome da tabela."},
                },
                "required": ["table_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_layouts",
            "description": "Lista os layouts de importação de propostas cadastrados.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Máximo de resultados."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_layout",
            "description": "Remove um layout de importação permanentemente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "layout_id": {"type": "string", "description": "UUID do layout."},
                },
                "required": ["layout_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_restore_points",
            "description": "Lista os pontos de restauração criados pela IA que ainda não foram usados.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Máximo de resultados. Padrão: 20."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "restore_restore_point",
            "description": (
                "Desfaz uma operação destrutiva da IA a partir de um ponto de restauração. "
                "Use quando o usuário pedir para desfazer uma exclusão, atualização ou normalização feita pela IA."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "restore_point_id": {"type": "string", "description": "UUID do ponto de restauração retornado pela operação original."},
                },
                "required": ["restore_point_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_tables_batch",
            "description": (
                "Cria múltiplas tabelas de comissionamento de uma só vez a partir de um arquivo ou lista. "
                "Use esta ferramenta (em vez de create_table repetido) sempre que o usuário enviar "
                "um arquivo ou listar várias tabelas para importar."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tables": {
                        "type": "array",
                        "description": "Lista de tabelas a criar.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "bank_id":         {"type": "string", "description": "UUID ou nome do banco."},
                                "agreement_id":    {"type": "string", "description": "UUID ou nome do convênio."},
                                "name_in_bank":    {"type": "string"},
                                "code_in_bank":    {"type": "string"},
                                "commission_rate": {"type": "number"},
                                "vigency_date":    {"type": "string", "description": "YYYY-MM-DD"},
                                "min_value":       {"type": "number"},
                                "max_value":       {"type": "number"},
                                "commission_ranges": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "min_value":       {"type": "number"},
                                            "max_value":       {"type": "number"},
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
                "required": ["tables"],
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


def _is_uuid(value: str) -> bool:
    import uuid as _uuid
    try:
        _uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError):
        return False


def _resolve_bank(value: str):
    """Aceita UUID, nome exato ou nome parcial do banco.

    Estratégia de fallback (em ordem):
      1. UUID exato
      2. name__iexact
      3. Primeira parte de nome composto 'BANCO - ...' → name__iexact
      4. name__icontains na primeira parte
    """
    from bank.models import Bank
    if _is_uuid(value):
        return Bank.objects.get(pk=value)

    # Match exato
    try:
        return Bank.objects.get(name__iexact=value)
    except Bank.MultipleObjectsReturned:
        raise
    except Bank.DoesNotExist:
        pass

    # Candidatos: valor completo + primeira parte se for nome composto
    candidates: list[str] = []
    if ' - ' in value:
        candidates.append(value.split(' - ', 1)[0].strip())
    candidates.append(value)  # tenta icontains com o valor original como fallback

    for candidate in candidates:
        if not candidate or candidate == value and candidates[0] != value:
            continue
        try:
            return Bank.objects.get(name__iexact=candidate)
        except (Bank.DoesNotExist, Bank.MultipleObjectsReturned):
            pass
        qs = Bank.objects.filter(name__icontains=candidate)
        if qs.count() == 1:
            return qs.first()
        if qs.count() > 1:
            raise Bank.MultipleObjectsReturned(
                f"Múltiplos bancos encontrados para '{candidate}'. Use o UUID."
            )

    raise Bank.DoesNotExist(f"Banco '{value}' não encontrado.")


def _resolve_agreement(value: str):
    """Aceita UUID, nome exato ou nome parcial do convênio."""
    from bank.models import Agreement
    if _is_uuid(value):
        return Agreement.objects.get(pk=value)

    # Match exato
    try:
        return Agreement.objects.get(name__iexact=value)
    except Agreement.MultipleObjectsReturned:
        raise
    except Agreement.DoesNotExist:
        pass

    # Fallback icontains
    qs = Agreement.objects.filter(name__icontains=value)
    if qs.count() == 1:
        return qs.first()
    if qs.count() > 1:
        raise Agreement.MultipleObjectsReturned(
            f"Múltiplos convênios encontrados para '{value}'. Use o UUID."
        )

    raise Agreement.DoesNotExist(f"Convênio '{value}' não encontrado.")


def _resolve_table(value: str):
    """Aceita UUID, código da tabela ou nome da tabela no banco."""
    from bank.models import Table
    qs = Table.objects.select_related("bank", "agreement")
    if _is_uuid(value):
        return qs.get(pk=value)

    try:
        return qs.get(code_in_bank__iexact=value)
    except Table.MultipleObjectsReturned:
        raise
    except Table.DoesNotExist:
        pass

    try:
        return qs.get(name_in_bank__iexact=value)
    except Table.MultipleObjectsReturned:
        raise
    except Table.DoesNotExist:
        pass

    partial = qs.filter(name_in_bank__icontains=value)
    if partial.count() == 1:
        return partial.first()
    if partial.count() > 1:
        raise Table.MultipleObjectsReturned(
            f"Múltiplas tabelas encontradas para '{value}'. Use o UUID ou o código exato."
        )

    partial_code = qs.filter(code_in_bank__icontains=value)
    if partial_code.count() == 1:
        return partial_code.first()
    if partial_code.count() > 1:
        raise Table.MultipleObjectsReturned(
            f"Múltiplas tabelas encontradas para '{value}'. Use o UUID ou o código exato."
        )

    raise Table.DoesNotExist(f"Tabela '{value}' não encontrada.")


def _table_summary(table) -> dict:
    return {
        "id": str(table.id),
        "bank": table.bank.name,
        "agreement": table.agreement.name,
        "name_in_bank": table.name_in_bank,
        "code_in_bank": table.code_in_bank,
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
        bank = _resolve_bank(bank_id)
        bank = Bank.objects.prefetch_related("agreements", "tables__agreement", "tables__commission_ranges").get(pk=bank.pk)
    except Bank.DoesNotExist:
        return {"error": f"Banco '{bank_id}' não encontrado."}
    except Bank.MultipleObjectsReturned:
        return {"error": f"Múltiplos bancos encontrados para '{bank_id}'. Use o UUID."}
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


def tool_list_tables(bank_id: str = None, agreement_id: str = None, code_in_bank: str = None, active_only: bool = True) -> dict:
    from bank.models import Table, Bank, Agreement
    qs = Table.objects.select_related("bank", "agreement").prefetch_related("commission_ranges")
    if active_only:
        qs = qs.filter(is_active=True)
    if bank_id:
        try:
            bank = _resolve_bank(bank_id)
            qs = qs.filter(bank=bank)
        except (Bank.DoesNotExist, Bank.MultipleObjectsReturned):
            qs = qs.filter(bank__name__icontains=bank_id)
    if agreement_id:
        try:
            agr = _resolve_agreement(agreement_id)
            qs = qs.filter(agreement=agr)
        except (Agreement.DoesNotExist, Agreement.MultipleObjectsReturned):
            qs = qs.filter(agreement__name__icontains=agreement_id)
    if code_in_bank:
        qs = qs.filter(code_in_bank__icontains=code_in_bank)
    tables = [_table_summary(t) for t in qs]
    return {"tables": tables, "total": len(tables)}


def tool_get_table(table_id: str) -> dict:
    from bank.models import Table
    try:
        table = _resolve_table(table_id)
        table = Table.objects.select_related("bank", "agreement").prefetch_related("commission_ranges").get(pk=table.pk)
    except Table.DoesNotExist:
        return {"error": f"Tabela '{table_id}' não encontrada."}
    except Table.MultipleObjectsReturned:
        return {"error": f"Múltiplas tabelas encontradas para '{table_id}'. Use o UUID."}
    return _table_summary(table)


def tool_update_table(
    table_id: str,
    commission_rate: float = None,
    vigency_date: str = None,
    is_active: bool = None,
    min_value: float = None,
    max_value: float = None,
    name_in_bank: str = None,
    code_in_bank: str = None,
    commission_ranges: list = None,
) -> dict:
    from bank.models import Table, CommissionRange, TableHistory
    from .restore_points import create_restore_point

    try:
        table = _resolve_table(table_id)
    except Table.DoesNotExist:
        return {"error": f"Tabela '{table_id}' não encontrada."}

    rp = create_restore_point(
        operation_type="update",
        model_label="bank.Table",
        description=f"Antes de atualizar tabela '{table.name_in_bank or table_id}'",
        instances=[table],
    )

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
    if code_in_bank is not None:
        table.code_in_bank = code_in_bank or None
        updated_fields.append("code_in_bank")

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
            user=None,
            new_values=_table_summary(table),
            notes=f"Atualizado pelo agente IA. Campos: {', '.join(updated_fields)}",
        )
    except Exception as exc:
        logger.warning("Não foi possível registrar TableHistory: %s", exc)

    return {
        "success": True,
        "updated_fields": updated_fields,
        "table": _table_summary(table),
        "restore_point_id": str(rp.id),
    }


def tool_create_table(
    bank_id: str,
    agreement_id: str,
    name_in_bank: str = None,
    code_in_bank: str = None,
    commission_rate: float = None,
    vigency_date: str = None,
    min_value: float = None,
    max_value: float = None,
    commission_ranges: list = None,
) -> dict:
    from bank.models import Table, CommissionRange, TableHistory, Bank, Agreement
    from datetime import date

    try:
        bank = _resolve_bank(bank_id)
    except Bank.DoesNotExist:
        return {"error": f"Banco '{bank_id}' não encontrado."}
    except Bank.MultipleObjectsReturned:
        return {"error": f"Múltiplos bancos encontrados para '{bank_id}'. Use o UUID."}
    try:
        agreement = _resolve_agreement(agreement_id)
    except Agreement.DoesNotExist:
        # Auto-cria o convênio caso não exista
        agreement = Agreement.objects.create(name=agreement_id)
        logger.info("Convênio '%s' criado automaticamente.", agreement_id)
    except Agreement.MultipleObjectsReturned:
        return {"error": f"Múltiplos convênios encontrados para '{agreement_id}'. Use o UUID."}

    vdate = date.today()
    if vigency_date:
        try:
            v = str(vigency_date).strip()
            # Excel armazena datas como número de dias desde 30/12/1899
            if v.replace('.', '', 1).isdigit():
                from datetime import timedelta
                vdate = date(1899, 12, 30) + timedelta(days=int(float(v)))
            else:
                vdate = date.fromisoformat(v)
        except (ValueError, OverflowError):
            return {"error": f"Data inválida: {vigency_date}"}

    table = Table.objects.create(
        bank=bank,
        agreement=agreement,
        name_in_bank=name_in_bank or "",
        code_in_bank=code_in_bank or None,
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
            user=None,
            new_values=_table_summary(table),
            notes="Criada pelo agente IA.",
        )
    except Exception as exc:
        logger.warning("Não foi possível registrar TableHistory: %s", exc)

    return {"success": True, "table": _table_summary(table)}


def tool_create_agreement(name: str, description: str = "") -> dict:
    """Cria um novo convênio. Se já existir (case-insensitive), retorna o existente."""
    from bank.models import Agreement
    try:
        existing = _resolve_agreement(name)
        return {
            "success": True,
            "created": False,
            "agreement": {"id": str(existing.id), "name": existing.name, "is_active": existing.is_active},
        }
    except Agreement.DoesNotExist:
        pass
    except Agreement.MultipleObjectsReturned:
        return {"error": f"Múltiplos convênios encontrados para '{name}'. Use o UUID."}

    agreement = Agreement.objects.create(name=name, description=description or "")
    return {
        "success": True,
        "created": True,
        "agreement": {"id": str(agreement.id), "name": agreement.name, "is_active": agreement.is_active},
    }


def tool_update_agreement(
    agreement_id: str,
    name: str = None,
    description: str = None,
    is_active: bool = None,
) -> dict:
    from bank.models import Agreement
    from .restore_points import create_restore_point
    try:
        agreement = _resolve_agreement(agreement_id)
    except Agreement.DoesNotExist:
        return {"error": f"Convênio '{agreement_id}' não encontrado."}
    except Agreement.MultipleObjectsReturned:
        return {"error": f"Múltiplos convênios encontrados para '{agreement_id}'. Use o UUID."}

    rp = create_restore_point(
        operation_type="update",
        model_label="bank.Agreement",
        description=f"Antes de atualizar convênio '{agreement.name}'",
        instances=[agreement],
    )

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
        "restore_point_id": str(rp.id),
    }


def tool_create_tables_batch(tables: list) -> dict:
    """
    Cria múltiplas tabelas em uma única chamada.
    Cada item de `tables` tem os mesmos campos de `tool_create_table`.
    Retorna resumo de quantas foram criadas e quais falharam.
    """
    created = []
    errors = []

    for i, t in enumerate(tables):
        try:
            result = tool_create_table(
                bank_id=t.get("bank_id", ""),
                agreement_id=t.get("agreement_id", ""),
                name_in_bank=t.get("name_in_bank"),
                code_in_bank=t.get("code_in_bank"),
                commission_rate=t.get("commission_rate"),
                vigency_date=t.get("vigency_date"),
                min_value=t.get("min_value"),
                max_value=t.get("max_value"),
                commission_ranges=t.get("commission_ranges"),
            )
            if result.get("success"):
                created.append(result["table"].get("name_in_bank") or f"tabela_{i+1}")
            else:
                errors.append({"index": i, "error": result.get("error", "erro desconhecido"), "data": t})
        except Exception as exc:
            errors.append({"index": i, "error": str(exc), "data": t})

    return {
        "success": True,
        "total_requested": len(tables),
        "created_count": len(created),
        "error_count": len(errors),
        "created": created,
        "errors": errors,
    }


def tool_delete_agreement(agreement_id: str) -> dict:
    """Remove um convênio e suas tabelas vinculadas."""
    from bank.models import Agreement, Table
    from .restore_points import create_restore_point
    try:
        agreement = _resolve_agreement(agreement_id)
        name = agreement.name
        deleted_id = str(agreement.id)

        # Cria restore point incluindo o convênio e todas as tabelas vinculadas
        related_tables = list(agreement.tables.select_related('bank'))
        rp = create_restore_point(
            operation_type="delete",
            model_label="bank.Agreement",
            description=f"Antes de remover convênio '{name}'",
            instances=[agreement],
        )
        if related_tables:
            create_restore_point(
                operation_type="delete",
                model_label="bank.Table",
                description=f"Tabelas vinculadas ao convênio '{name}'",
                instances=related_tables,
            )

        agreement.delete()
        return {
            "success": True,
            "deleted": deleted_id,
            "name": name,
            "message": f"Convênio '{name}' removido com sucesso.",
            "restore_point_id": str(rp.id),
            "note": "Use o restore_point_id para desfazer a exclusão.",
        }
    except Agreement.DoesNotExist:
        return {"error": f"Convênio '{agreement_id}' não encontrado."}
    except Agreement.MultipleObjectsReturned:
        return {"error": f"Múltiplos convênios encontrados para '{agreement_id}'. Use o UUID."}
    except Exception as exc:
        return {"error": str(exc)}


def tool_delete_table(table_id: str) -> dict:
    """Remove uma tabela permanentemente."""
    from bank.models import Table
    from .restore_points import create_restore_point
    try:
        table = _resolve_table(table_id)
        name = table.name_in_bank
        deleted_id = str(table.id)
        rp = create_restore_point(
            operation_type="delete",
            model_label="bank.Table",
            description=f"Antes de remover tabela '{name}'",
            instances=[table],
        )
        table.delete()
        return {
            "success": True,
            "deleted": deleted_id,
            "name": name,
            "message": f"Tabela '{name}' removida com sucesso.",
            "restore_point_id": str(rp.id),
            "note": "Use o restore_point_id para desfazer a exclusão.",
        }
    except Table.DoesNotExist:
        return {"error": f"Tabela '{table_id}' não encontrada."}
    except Table.MultipleObjectsReturned:
        return {"error": f"Múltiplas tabelas encontradas para '{table_id}'. Use o UUID."}
    except Exception as exc:
        return {"error": str(exc)}


def tool_normalize_agreements(dry_run: bool = False) -> dict:
    """
    Agrupa convênios pelo nome normalizado e funde os duplicados.
    Mantém o primeiro de cada grupo e move tabelas/bancos dos demais para ele.
    """
    from bank.models import Agreement, Bank
    from collections import defaultdict
    from .restore_points import create_restore_point

    agreements = list(Agreement.objects.prefetch_related('banks', 'tables'))
    groups: dict[str, list[Agreement]] = defaultdict(list)
    for agr in agreements:
        norm = normalize_name(agr.name)
        if norm:
            groups[norm].append(agr)

    merged = []
    skipped = []
    snapshot_groups = []
    for norm, group in groups.items():
        if len(group) <= 1:
            continue
        keeper = group[0]
        duplicates = group[1:]
        plan = {
            "canonical": {"id": str(keeper.id), "name": keeper.name},
            "duplicates": [{"id": str(a.id), "name": a.name} for a in duplicates],
        }
        snapshot_groups.append({
            "canonical": {"id": str(keeper.id), "name": keeper.name},
            "duplicates": [
                {
                    "id": str(a.id),
                    "name": a.name,
                    "banks": [str(b.id) for b in a.banks.all()],
                    "tables": [str(t.id) for t in a.tables.all()],
                }
                for a in duplicates
            ],
        })
        if dry_run:
            merged.append(plan)
            continue

        bank_ids_to_add = set()
        tables_to_move = []
        for dup in duplicates:
            for b in dup.banks.all():
                bank_ids_to_add.add(b.pk)
            for t in dup.tables.all():
                tables_to_move.append(t)

        for b in Bank.objects.filter(pk__in=bank_ids_to_add):
            if not keeper.banks.filter(pk=b.pk).exists():
                keeper.banks.add(b)

        for t in tables_to_move:
            t.agreement = keeper
            t.save(update_fields=['agreement'])

        for dup in duplicates:
            dup.delete()

        merged.append(plan)

    rp = None
    if not dry_run and snapshot_groups:
        rp = create_restore_point(
            operation_type="normalize",
            model_label="bank.Agreement",
            description=f"Antes de normalizar {len(snapshot_groups)} grupos de convênios",
            snapshot_data={"merged_groups": snapshot_groups},
        )

    result = {
        "success": True,
        "dry_run": dry_run,
        "merged_groups": len(merged),
        "merged": merged,
    }
    if rp:
        result["restore_point_id"] = str(rp.id)
    return result


def tool_list_layouts(limit: int = 100) -> dict:
    """Lista layouts de importação de propostas."""
    from proposals.models import Layout
    qs = Layout.objects.select_related('bank').prefetch_related('map_fields')[: max(1, min(int(limit or 100), 200))]
    layouts = []
    for l in qs:
        layouts.append({
            "id": str(l.id),
            "name": l.name,
            "bank": l.bank.name if l.bank else None,
            "fields_count": l.map_fields.count(),
            "created_at": str(l.created_at),
        })
    return {"layouts": layouts, "total": len(layouts)}


def tool_delete_layout(layout_id: str) -> dict:
    """Remove um layout de importação permanentemente."""
    from proposals.models import Layout
    from .restore_points import create_restore_point
    try:
        layout = Layout.objects.get(pk=layout_id)
        name = layout.name
        deleted_id = str(layout.id)
        rp = create_restore_point(
            operation_type="delete",
            model_label="proposals.Layout",
            description=f"Antes de remover layout '{name}'",
            instances=[layout],
        )
        layout.delete()
        return {
            "success": True,
            "deleted": deleted_id,
            "name": name,
            "message": f"Layout '{name}' removido com sucesso.",
            "restore_point_id": str(rp.id),
            "note": "Use o restore_point_id para desfazer a exclusão.",
        }
    except Layout.DoesNotExist:
        return {"error": f"Layout '{layout_id}' não encontrado."}
    except Exception as exc:
        return {"error": str(exc)}


# ─── Despachador ─────────────────────────────────────────────────────────────

TOOL_HANDLERS: dict[str, Any] = {
    "list_banks": tool_list_banks,
    "get_bank": tool_get_bank,
    "list_agreements": tool_list_agreements,
    "list_tables": tool_list_tables,
    "get_table": tool_get_table,
    "update_table": tool_update_table,
    "create_table": tool_create_table,
    "delete_table": tool_delete_table,
    "create_agreement": tool_create_agreement,
    "update_agreement": tool_update_agreement,
    "delete_agreement": tool_delete_agreement,
    "normalize_agreements": tool_normalize_agreements,
    "create_tables_batch": tool_create_tables_batch,
    "list_layouts": tool_list_layouts,
    "delete_layout": tool_delete_layout,
    "list_restore_points": tool_list_restore_points,
    "restore_restore_point": tool_restore_restore_point,
}


def tool_list_restore_points(limit: int = 20) -> dict:
    """Lista pontos de restauração não restaurados."""
    from .restore_points import list_restore_points
    return {"restore_points": list_restore_points(limit=limit)}


def tool_restore_restore_point(restore_point_id: str) -> dict:
    """Desfaz uma operação destrutiva usando o ponto de restauração."""
    from .restore_points import restore_restore_point, RestorePointError
    try:
        return restore_restore_point(restore_point_id)
    except RestorePointError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        return {"error": f"Erro ao restaurar: {str(exc)}"}


# ─── Registro de ferramentas estendidas (users, companies, etc.) ──────────────
# Mantemos as definitions/handlers base acima e mesclamos as adicionais. Assim
# o llm.py continua importando apenas TOOL_DEFINITIONS / dispatch_tool daqui.

from . import tools_extended as _tools_extended  # noqa: E402

TOOL_DEFINITIONS.extend(_tools_extended.TOOL_DEFS_EXTRA)
TOOL_HANDLERS.update(_tools_extended.TOOL_HANDLERS_EXTRA)

# Lista de ferramentas explicitamente bloqueadas (mexem em pagamentos).
FORBIDDEN_TOOLS: frozenset[str] = _tools_extended.PAYMENTS_FORBIDDEN_TOOLS


def dispatch_tool(name: str, arguments: str | dict) -> str:
    """
    Executa a ferramenta `name` com os argumentos fornecidos.
    Retorna string JSON com o resultado.
    """
    if name in FORBIDDEN_TOOLS:
        return json.dumps(
            {"error": f"Ferramenta '{name}' bloqueada: o agente não opera no módulo de pagamentos."}
        )

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
        logger.info(
            "dispatch_tool name=%s args=%s -> %s",
            name,
            json.dumps(kwargs, default=str, ensure_ascii=False)[:500],
            json.dumps(result, default=str, ensure_ascii=False)[:500],
        )
        return json.dumps(result, default=str, ensure_ascii=False)
    except Exception as exc:
        logger.exception("Erro ao executar ferramenta '%s': %s", name, exc)
        return json.dumps({"error": str(exc)})
