"""
Ferramentas estendidas do agente IA.

Cobre as demais entidades do sistema (usuários, corbans, acessos bancários,
grupos de comissão, propostas, comissões), expostas como function-calls.

Política de segurança: NÃO expomos operações sobre o módulo de pagamentos
(Payment, PaymentManual, Withdraw, CorbanPayTransaction) nem alteração de
release_status de Commission. A IA pode VER comissões, mas não liberar/pagar.

Esta lista de definições e handlers é mesclada com as ferramentas base em
``ai_agent.tools`` no fim daquele módulo.
"""
from __future__ import annotations

import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)


# ─── Helpers compartilhados ──────────────────────────────────────────────────


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
    except (ValueError, AttributeError, TypeError):
        return False


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _normalize_cpf(value) -> str:
    digits = _digits(value)
    if 1 <= len(digits) <= 11:
        digits = digits.zfill(11)
    return digits


def _normalize_cnpj(value) -> str:
    digits = _digits(value)
    if 1 <= len(digits) <= 14:
        digits = digits.zfill(14)
    return digits


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return date.fromisoformat(text) if fmt == "%Y-%m-%d" else date.strptime(text, fmt).date()  # type: ignore[attr-defined]
        except (ValueError, AttributeError):
            continue
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _resolve_user(value: str):
    """Aceita id (int), CPF (com ou sem formatação) ou email."""
    from core.models import User

    raw = str(value).strip()
    # ID inteiro
    if raw.isdigit() and len(raw) <= 9:
        try:
            return User.objects.get(pk=int(raw))
        except User.DoesNotExist:
            pass

    # CPF
    cpf = _normalize_cpf(raw)
    if len(cpf) == 11:
        try:
            return User.objects.get(cpf=cpf)
        except User.DoesNotExist:
            pass

    # Email
    if "@" in raw:
        try:
            return User.objects.get(email__iexact=raw)
        except User.DoesNotExist:
            pass

    raise User.DoesNotExist(f"Usuário '{value}' não encontrado.")


def _resolve_company(value: str):
    """Aceita UUID, CNPJ/CPF (document) ou nome (exato → icontains)."""
    from core.models import Company

    raw = str(value).strip()
    if _is_uuid(raw):
        return Company.objects.get(pk=raw)

    digits = _digits(raw)
    if digits:
        for doc in (digits, _normalize_cpf(digits), _normalize_cnpj(digits)):
            try:
                return Company.objects.get(document=doc)
            except Company.DoesNotExist:
                continue

    try:
        return Company.objects.get(name__iexact=raw)
    except Company.MultipleObjectsReturned:
        raise
    except Company.DoesNotExist:
        pass

    qs = Company.objects.filter(name__icontains=raw)
    if qs.count() == 1:
        return qs.first()
    if qs.count() > 1:
        raise Company.MultipleObjectsReturned(
            f"Múltiplos corbans encontrados para '{value}'. Use o UUID."
        )
    raise Company.DoesNotExist(f"Corban '{value}' não encontrado.")


def _user_summary(user) -> dict:
    return {
        "id": user.id,
        "cpf": user.cpf,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "role": user.role,
        "company": str(user.company_id) if user.company_id else None,
        "company_name": user.company.name if user.company_id else None,
        "leader": user.leader_id,
        "is_active": user.is_active,
    }


def _company_summary(company) -> dict:
    return {
        "id": str(company.id),
        "name": company.name,
        "trading_name": company.trading_name,
        "document": company.document,
        "person_type": company.person_type,
        "email": company.email,
        "phone": company.phone,
        "is_active": company.is_active,
        "is_promotora": company.is_promotora,
    }


# ─── USERS ───────────────────────────────────────────────────────────────────


def tool_list_users(
    role: str | None = None,
    company: str | None = None,
    leader: str | None = None,
    search: str | None = None,
    is_active: bool | None = None,
    limit: int = 50,
) -> dict:
    from core.models import User

    qs = User.objects.select_related("company", "leader")
    if role:
        qs = qs.filter(role=role)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    if company:
        try:
            company_obj = _resolve_company(company)
            qs = qs.filter(company=company_obj)
        except Exception:
            qs = qs.filter(company__name__icontains=company)
    if leader:
        try:
            leader_obj = _resolve_user(leader)
            qs = qs.filter(leader=leader_obj)
        except Exception:
            return {"error": f"Líder '{leader}' não encontrado."}
    if search:
        from core.search_utils import apply_user_list_search

        qs = apply_user_list_search(qs, search)

    total = qs.count()
    qs = qs[: max(1, min(int(limit or 50), 200))]
    return {
        "users": [_user_summary(u) for u in qs],
        "total": total,
        "shown": qs.count() if hasattr(qs, "count") else len(list(qs)),
    }


def tool_get_user(user_id: str) -> dict:
    from core.models import User

    try:
        user = _resolve_user(user_id)
    except User.DoesNotExist:
        return {"error": f"Usuário '{user_id}' não encontrado."}

    extra = getattr(user, "extra_data", None)
    return {
        **_user_summary(user),
        "extra_data": (
            {
                "phone": extra.phone,
                "birth_date": str(extra.birth_date) if extra.birth_date else None,
                "rg": extra.rg,
                "rg_emission_date": str(extra.rg_emission_date) if extra.rg_emission_date else None,
                "rg_emission_organ": extra.rg_emission_organ,
                "pix_key": extra.pix_key,
                "pix_type": extra.pix_type,
            }
            if extra
            else None
        ),
    }


def tool_create_user(
    cpf: str,
    email: str,
    first_name: str,
    password: str,
    role: str = "vendedor",
    last_name: str | None = None,
    company: str | None = None,
    leader: str | None = None,
    phone: str | None = None,
    pix_key: str | None = None,
    pix_type: str | None = None,
    birth_date: str | None = None,
) -> dict:
    from core.models import User, ExtraData

    cpf_clean = _normalize_cpf(cpf)
    if len(cpf_clean) != 11:
        return {"error": f"CPF inválido: {cpf}"}

    valid_roles = {r[0] for r in User.ROLE_CHOICES}
    if role not in valid_roles:
        return {"error": f"role inválida: {role}. Opções: {', '.join(sorted(valid_roles))}"}

    company_obj = None
    if company:
        try:
            company_obj = _resolve_company(company)
        except Exception as exc:
            return {"error": f"Corban '{company}': {exc}"}

    leader_obj = None
    if leader:
        try:
            leader_obj = _resolve_user(leader)
        except User.DoesNotExist:
            return {"error": f"Líder '{leader}' não encontrado."}

    if User.objects.filter(cpf=cpf_clean).exists():
        return {"error": f"Já existe usuário com CPF {cpf_clean}."}
    if User.objects.filter(email__iexact=email).exists():
        return {"error": f"Já existe usuário com email {email}."}

    user = User.objects.create_user(
        cpf=cpf_clean,
        email=email,
        first_name=first_name,
        last_name=last_name or "",
        role=role,
        company=company_obj,
        leader=leader_obj,
    )
    user.set_password(password)
    user.save()

    extra_payload = {
        k: v
        for k, v in {
            "phone": phone,
            "pix_key": pix_key,
            "pix_type": pix_type,
            "birth_date": _parse_date(birth_date),
        }.items()
        if v
    }
    if extra_payload:
        ExtraData.objects.create(user=user, **extra_payload)

    return {"success": True, "user": _user_summary(user)}


def tool_update_user(
    user_id: str,
    email: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    company: str | None = None,
    leader: str | None = None,
    new_password: str | None = None,
    phone: str | None = None,
    pix_key: str | None = None,
    pix_type: str | None = None,
    birth_date: str | None = None,
) -> dict:
    from core.models import User, ExtraData

    try:
        user = _resolve_user(user_id)
    except User.DoesNotExist:
        return {"error": f"Usuário '{user_id}' não encontrado."}

    updated: list[str] = []

    if email is not None:
        user.email = email
        updated.append("email")
    if first_name is not None:
        user.first_name = first_name
        updated.append("first_name")
    if last_name is not None:
        user.last_name = last_name
        updated.append("last_name")
    if role is not None:
        valid_roles = {r[0] for r in User.ROLE_CHOICES}
        if role not in valid_roles:
            return {"error": f"role inválida: {role}"}
        user.role = role
        updated.append("role")
    if is_active is not None:
        user.is_active = is_active
        updated.append("is_active")
    if company is not None:
        if company == "":
            user.company = None
        else:
            try:
                user.company = _resolve_company(company)
            except Exception as exc:
                return {"error": f"Corban '{company}': {exc}"}
        updated.append("company")
    if leader is not None:
        if leader == "":
            user.leader = None
        else:
            try:
                user.leader = _resolve_user(leader)
            except User.DoesNotExist:
                return {"error": f"Líder '{leader}' não encontrado."}
        updated.append("leader")

    if new_password:
        user.set_password(new_password)
        updated.append("password")

    if updated:
        user.save()

    if any(v is not None for v in (phone, pix_key, pix_type, birth_date)):
        extra, _created = ExtraData.objects.get_or_create(user=user)
        if phone is not None:
            extra.phone = phone or None
        if pix_key is not None:
            extra.pix_key = pix_key or None
        if pix_type is not None:
            extra.pix_type = pix_type or None
        if birth_date is not None:
            extra.birth_date = _parse_date(birth_date)
        extra.save()
        updated.append("extra_data")

    return {"success": True, "updated_fields": updated, "user": _user_summary(user)}


def tool_delete_user(user_id: str, hard: bool = False) -> dict:
    """
    Remove um usuário. Por padrão apenas desativa (is_active=False).
    Passe hard=True para excluir definitivamente.
    """
    from core.models import User

    try:
        user = _resolve_user(user_id)
    except User.DoesNotExist:
        return {"error": f"Usuário '{user_id}' não encontrado."}

    if hard:
        info = {"id": user.id, "cpf": user.cpf, "email": user.email}
        user.delete()
        return {"success": True, "deleted": info}

    user.is_active = False
    user.save(update_fields=["is_active"])
    return {"success": True, "deactivated": _user_summary(user)}


# ─── COMPANIES (Corbans) ─────────────────────────────────────────────────────


def tool_list_companies(
    search: str | None = None,
    is_active: bool | None = None,
    limit: int = 50,
) -> dict:
    from core.models import Company
    from django.db.models import Q

    qs = Company.objects.all()
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    if search:
        from core.search_utils import apply_company_list_search

        qs = apply_company_list_search(qs, search)

    total = qs.count()
    qs = qs[: max(1, min(int(limit or 50), 200))]
    return {"companies": [_company_summary(c) for c in qs], "total": total}


def tool_get_company(company_id: str) -> dict:
    try:
        company = _resolve_company(company_id)
    except Exception as exc:
        return {"error": str(exc)}
    return _company_summary(company)


def tool_create_company(
    name: str,
    document: str,
    person_type: str = "PJ",
    trading_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    primary_color: str | None = None,
    secondary_color: str | None = None,
    accent_color: str | None = None,
) -> dict:
    from core.models import Company

    person_type = (person_type or "PJ").strip().upper()
    if person_type not in ("PF", "PJ"):
        return {"error": "person_type deve ser 'PF' ou 'PJ'."}

    doc = _normalize_cpf(document) if person_type == "PF" else _normalize_cnpj(document)
    expected = 11 if person_type == "PF" else 14
    if len(doc) != expected:
        return {"error": f"Documento inválido. Esperado {expected} dígitos para {person_type}."}

    if Company.objects.filter(document=doc).exists():
        return {"error": f"Já existe corban com documento {doc}."}

    company = Company.objects.create(
        name=name,
        trading_name=trading_name or "",
        person_type=person_type,
        document=doc,
        email=email or None,
        phone=phone or None,
        primary_color=primary_color or "#3498db",
        secondary_color=secondary_color or "#2c3e50",
        accent_color=accent_color or "#e74c3c",
    )
    return {"success": True, "company": _company_summary(company)}


def tool_update_company(
    company_id: str,
    name: str | None = None,
    trading_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    primary_color: str | None = None,
    secondary_color: str | None = None,
    accent_color: str | None = None,
    is_active: bool | None = None,
) -> dict:
    try:
        company = _resolve_company(company_id)
    except Exception as exc:
        return {"error": str(exc)}

    updated: list[str] = []
    for field, value in (
        ("name", name),
        ("trading_name", trading_name),
        ("email", email),
        ("phone", phone),
        ("primary_color", primary_color),
        ("secondary_color", secondary_color),
        ("accent_color", accent_color),
        ("is_active", is_active),
    ):
        if value is not None:
            setattr(company, field, value)
            updated.append(field)

    if updated:
        company.save()
    return {"success": True, "updated_fields": updated, "company": _company_summary(company)}


# ─── BANK ACCESS ─────────────────────────────────────────────────────────────


def tool_list_bank_accesses(
    user: str | None = None,
    bank: str | None = None,
    is_active: bool | None = None,
    limit: int = 50,
) -> dict:
    from bank_access.models import BankAccess

    qs = BankAccess.objects.select_related("bank", "user")
    if user:
        try:
            user_obj = _resolve_user(user)
            qs = qs.filter(user=user_obj)
        except Exception:
            qs = qs.filter(user__cpf__icontains=_digits(user) or user)
    if bank:
        from .tools import _resolve_bank  # lazy: usa o resolvedor das ferramentas base

        try:
            bank_obj = _resolve_bank(bank)
            qs = qs.filter(bank=bank_obj)
        except Exception:
            qs = qs.filter(bank__name__icontains=bank)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)

    total = qs.count()
    qs = qs[: max(1, min(int(limit or 50), 200))]
    return {
        "bank_accesses": [
            {
                "id": str(a.id),
                "bank": a.bank.name,
                "username": a.username,
                "is_active": a.is_active,
                "user": a.user.cpf if a.user else None,
                "user_name": a.user.get_full_name() if a.user else None,
            }
            for a in qs
        ],
        "total": total,
    }


def tool_create_bank_access(
    bank: str,
    username: str,
    password: str,
    user: str | None = None,
    is_active: bool = True,
) -> dict:
    from bank_access.models import BankAccess
    from .tools import _resolve_bank

    try:
        bank_obj = _resolve_bank(bank)
    except Exception as exc:
        return {"error": str(exc)}

    user_obj = None
    if user:
        try:
            user_obj = _resolve_user(user)
        except Exception:
            return {"error": f"Usuário '{user}' não encontrado."}

    obj, created = BankAccess.objects.update_or_create(
        bank=bank_obj,
        username=username,
        defaults={"password": password, "is_active": is_active, "user": user_obj},
    )
    return {
        "success": True,
        "created": created,
        "bank_access": {
            "id": str(obj.id),
            "bank": bank_obj.name,
            "username": obj.username,
            "is_active": obj.is_active,
            "user": user_obj.cpf if user_obj else None,
        },
    }


def tool_update_bank_access(
    access_id: str,
    username: str | None = None,
    password: str | None = None,
    is_active: bool | None = None,
    user: str | None = None,
) -> dict:
    from bank_access.models import BankAccess

    try:
        access = BankAccess.objects.get(pk=access_id)
    except BankAccess.DoesNotExist:
        return {"error": f"Acesso '{access_id}' não encontrado."}

    updated: list[str] = []
    if username is not None:
        access.username = username
        updated.append("username")
    if password is not None:
        access.password = password
        updated.append("password")
    if is_active is not None:
        access.is_active = is_active
        updated.append("is_active")
    if user is not None:
        if user == "":
            access.user = None
        else:
            try:
                access.user = _resolve_user(user)
            except Exception:
                return {"error": f"Usuário '{user}' não encontrado."}
        updated.append("user")

    if updated:
        access.save()
    return {"success": True, "updated_fields": updated}


# ─── COMMISSION GROUPS (Equipes) ─────────────────────────────────────────────


def _commission_group_summary(group) -> dict:
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "company": str(group.company_id) if group.company_id else None,
        "company_name": group.company.name if group.company_id else None,
        "is_active": group.is_active,
        "by_leader": group.by_leader,
        "leader": group.leader_id,
        "color": group.color,
        "sellers": list(group.sellers.values_list("id", flat=True)),
        "leaders": list(group.leaders.values_list("id", flat=True)),
    }


def tool_list_commission_groups(
    company: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    limit: int = 50,
) -> dict:
    from payments.models import CommissionGroup

    qs = CommissionGroup.objects.select_related("company", "leader")
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    if company:
        try:
            company_obj = _resolve_company(company)
            qs = qs.filter(company=company_obj)
        except Exception:
            qs = qs.filter(company__name__icontains=company)
    if search:
        qs = qs.filter(name__icontains=search)

    total = qs.count()
    qs = qs[: max(1, min(int(limit or 50), 200))]
    return {"commission_groups": [_commission_group_summary(g) for g in qs], "total": total}


def tool_get_commission_group(group_id: str) -> dict:
    from payments.models import CommissionGroup

    try:
        group = CommissionGroup.objects.select_related("company", "leader").get(pk=group_id)
    except CommissionGroup.DoesNotExist:
        return {"error": f"Equipe '{group_id}' não encontrada."}
    return _commission_group_summary(group)


def tool_create_commission_group(
    name: str,
    company: str | None = None,
    description: str | None = None,
    by_leader: bool = False,
    leader: str | None = None,
    color: str | None = None,
) -> dict:
    from payments.models import CommissionGroup

    company_obj = None
    if company:
        try:
            company_obj = _resolve_company(company)
        except Exception as exc:
            return {"error": str(exc)}

    leader_obj = None
    if leader:
        try:
            leader_obj = _resolve_user(leader)
        except Exception:
            return {"error": f"Líder '{leader}' não encontrado."}

    group = CommissionGroup.objects.create(
        name=name,
        description=description or None,
        company=company_obj,
        by_leader=by_leader,
        leader=leader_obj,
        color=color or "#ffff",
    )
    return {"success": True, "commission_group": _commission_group_summary(group)}


def tool_update_commission_group(
    group_id: str,
    name: str | None = None,
    description: str | None = None,
    is_active: bool | None = None,
    by_leader: bool | None = None,
    leader: str | None = None,
    color: str | None = None,
    company: str | None = None,
) -> dict:
    from payments.models import CommissionGroup

    try:
        group = CommissionGroup.objects.get(pk=group_id)
    except CommissionGroup.DoesNotExist:
        return {"error": f"Equipe '{group_id}' não encontrada."}

    updated: list[str] = []
    for field, value in (
        ("name", name),
        ("description", description),
        ("is_active", is_active),
        ("by_leader", by_leader),
        ("color", color),
    ):
        if value is not None:
            setattr(group, field, value)
            updated.append(field)

    if leader is not None:
        if leader == "":
            group.leader = None
        else:
            try:
                group.leader = _resolve_user(leader)
            except Exception:
                return {"error": f"Líder '{leader}' não encontrado."}
        updated.append("leader")

    if company is not None:
        if company == "":
            group.company = None
        else:
            try:
                group.company = _resolve_company(company)
            except Exception:
                return {"error": f"Corban '{company}' não encontrado."}
        updated.append("company")

    if updated:
        group.save()
    return {"success": True, "updated_fields": updated, "commission_group": _commission_group_summary(group)}


def tool_set_commission_group_members(
    group_id: str,
    sellers: list[str] | None = None,
    leaders: list[str] | None = None,
    add: bool = True,
) -> dict:
    """
    Atualiza vendedores/líderes de uma equipe.
    Se add=True, adiciona; se add=False, REMOVE.
    Para substituir tudo, use add=False com a lista completa atual e depois add=True.
    """
    from payments.models import CommissionGroup

    try:
        group = CommissionGroup.objects.get(pk=group_id)
    except CommissionGroup.DoesNotExist:
        return {"error": f"Equipe '{group_id}' não encontrada."}

    def _resolve_many(values):
        out = []
        for v in values or []:
            try:
                out.append(_resolve_user(v))
            except Exception:
                continue
        return out

    seller_objs = _resolve_many(sellers)
    leader_objs = _resolve_many(leaders)

    op = "add" if add else "remove"
    if seller_objs:
        getattr(group.sellers, op)(*seller_objs)
    if leader_objs:
        getattr(group.leaders, op)(*leader_objs)

    return {"success": True, "operation": op, "commission_group": _commission_group_summary(group)}


# ─── PROPOSALS / COMMISSIONS (read-only) ─────────────────────────────────────


def tool_list_proposals(
    seller: str | None = None,
    company: str | None = None,
    bank: str | None = None,
    contract_number: str | None = None,
    client_document: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> dict:
    from proposals.models import Proposal

    qs = Proposal.objects.select_related("seller", "company", "bank", "agreement", "table")
    if seller:
        try:
            qs = qs.filter(seller=_resolve_user(seller))
        except Exception:
            qs = qs.filter(seller__cpf__icontains=_digits(seller) or seller)
    if company:
        try:
            qs = qs.filter(company=_resolve_company(company))
        except Exception:
            qs = qs.filter(company__name__icontains=company)
    if bank:
        from .tools import _resolve_bank

        try:
            qs = qs.filter(bank=_resolve_bank(bank))
        except Exception:
            qs = qs.filter(bank__name__icontains=bank)
    if contract_number:
        qs = qs.filter(contract_number__icontains=contract_number)
    if client_document:
        qs = qs.filter(client_document__icontains=_digits(client_document))
    if status:
        qs = qs.filter(status=status)

    total = qs.count()
    qs = qs.order_by("-uploaded_at")[: max(1, min(int(limit or 50), 200))]
    return {
        "proposals": [
            {
                "id": str(p.id),
                "contract_number": p.contract_number,
                "client_name": p.client_name,
                "client_document": p.client_document,
                "amount": str(p.amount),
                "status": p.status,
                "seller": p.seller.cpf if p.seller_id else None,
                "company": p.company.name if p.company_id else None,
                "bank": p.bank.name,
                "agreement": p.agreement.name,
                "table": p.table.name_in_bank,
                "disbursement_date": str(p.disbursement_date),
                "release_date": str(p.release_date) if p.release_date else None,
            }
            for p in qs
        ],
        "total": total,
    }


def tool_list_proposal_batches(limit: int = 30) -> dict:
    from proposals.models import ProposalBatch

    qs = ProposalBatch.objects.select_related("layout", "layout__bank").order_by("-created_at")
    total = qs.count()
    qs = qs[: max(1, min(int(limit or 30), 100))]
    return {
        "batches": [
            {
                "id": str(b.id),
                "status": b.status,
                "bank": b.layout.bank.name if b.layout_id and b.layout.bank_id else None,
                "total_rows": b.total_rows,
                "processed_rows": b.processed_rows,
                "errored_rows": b.errored_rows,
                "created_at": str(b.created_at),
                "processed_at": str(b.processed_at) if b.processed_at else None,
            }
            for b in qs
        ],
        "total": total,
    }


def tool_list_commissions(
    user: str | None = None,
    company: str | None = None,
    role: str | None = None,
    release_status: str | None = None,
    limit: int = 50,
) -> dict:
    """Listagem de comissões (somente leitura). Liberar/pagar é fluxo de pagamento, bloqueado."""
    from payments.models import Commission

    qs = Commission.objects.select_related("user", "company", "proposal")
    if user:
        try:
            qs = qs.filter(user=_resolve_user(user))
        except Exception:
            qs = qs.filter(user__cpf__icontains=_digits(user) or user)
    if company:
        try:
            qs = qs.filter(company=_resolve_company(company))
        except Exception:
            qs = qs.filter(company__name__icontains=company)
    if role:
        qs = qs.filter(role=role)
    if release_status:
        qs = qs.filter(release_status=release_status)

    total = qs.count()
    qs = qs.order_by("-created_at")[: max(1, min(int(limit or 50), 200))]
    return {
        "commissions": [
            {
                "id": c.id,
                "proposal": str(c.proposal_id) if c.proposal_id else None,
                "user": c.user.cpf if c.user_id else None,
                "user_name": c.user.get_full_name() if c.user_id else None,
                "company": c.company.name if c.company_id else None,
                "role": c.role,
                "release_status": c.release_status,
                "created_at": str(c.created_at),
            }
            for c in qs
        ],
        "total": total,
        "note": "Liberação/pagamento de comissões é fluxo financeiro e está fora do escopo do agente.",
    }


# ─── Definições JSON-Schema ──────────────────────────────────────────────────


def _fn(name: str, description: str, properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }


_USER_FIELDS = {
    "email": {"type": "string"},
    "first_name": {"type": "string"},
    "last_name": {"type": "string"},
    "role": {
        "type": "string",
        "description": "admin, colaborador, empresa_admin, gerente, lider, vendedor",
    },
    "company": {"type": "string", "description": "UUID, CNPJ ou nome do corban"},
    "leader": {"type": "string", "description": "ID, CPF ou email do líder"},
    "phone": {"type": "string"},
    "pix_key": {"type": "string"},
    "pix_type": {"type": "string", "description": "CPF, CNPJ, EMAIL, CELULAR, CHAVE_ALEATORIA"},
    "birth_date": {"type": "string", "description": "YYYY-MM-DD ou DD/MM/YYYY"},
}


TOOL_DEFS_EXTRA: list[dict] = [
    # ── USERS ──
    _fn(
        "list_users",
        "Lista usuários do sistema (vendedores, líderes, gerentes, admins). "
        "Permite filtrar por papel, corban, líder, busca textual e status.",
        {
            "role": {"type": "string"},
            "company": {"type": "string"},
            "leader": {"type": "string"},
            "search": {"type": "string", "description": "Nome, email ou CPF (parcial)."},
            "is_active": {"type": "boolean"},
            "limit": {"type": "integer"},
        },
    ),
    _fn(
        "get_user",
        "Retorna detalhes de um usuário pelo id, CPF ou email (inclui dados extras).",
        {"user_id": {"type": "string"}},
        required=["user_id"],
    ),
    _fn(
        "create_user",
        "Cria um novo usuário. Para vendedores/líderes/gerentes, informe a 'company'.",
        {
            "cpf": {"type": "string"},
            "email": {"type": "string"},
            "first_name": {"type": "string"},
            "password": {"type": "string"},
            "last_name": {"type": "string"},
            **_USER_FIELDS,
        },
        required=["cpf", "email", "first_name", "password"],
    ),
    _fn(
        "update_user",
        "Atualiza um usuário. Passe apenas os campos a alterar. "
        "Use 'company' ou 'leader' = '' para limpar a referência.",
        {"user_id": {"type": "string"}, "new_password": {"type": "string"}, **_USER_FIELDS, "is_active": {"type": "boolean"}},
        required=["user_id"],
    ),
    _fn(
        "delete_user",
        "Remove um usuário. Por padrão apenas DESATIVA (is_active=False). "
        "Passe hard=true para excluir definitivamente.",
        {"user_id": {"type": "string"}, "hard": {"type": "boolean"}},
        required=["user_id"],
    ),
    # ── COMPANIES ──
    _fn(
        "list_companies",
        "Lista corbans (empresas). Filtros opcionais.",
        {
            "search": {"type": "string", "description": "Nome ou documento (parcial)."},
            "is_active": {"type": "boolean"},
            "limit": {"type": "integer"},
        },
    ),
    _fn(
        "get_company",
        "Retorna detalhes de um corban (UUID, CNPJ/CPF ou nome).",
        {"company_id": {"type": "string"}},
        required=["company_id"],
    ),
    _fn(
        "create_company",
        "Cria um novo corban (empresa parceira).",
        {
            "name": {"type": "string"},
            "document": {"type": "string", "description": "CPF (PF) ou CNPJ (PJ)."},
            "person_type": {"type": "string", "description": "PF ou PJ. Padrão: PJ."},
            "trading_name": {"type": "string"},
            "email": {"type": "string"},
            "phone": {"type": "string"},
            "primary_color": {"type": "string"},
            "secondary_color": {"type": "string"},
            "accent_color": {"type": "string"},
        },
        required=["name", "document"],
    ),
    _fn(
        "update_company",
        "Atualiza dados de um corban.",
        {
            "company_id": {"type": "string"},
            "name": {"type": "string"},
            "trading_name": {"type": "string"},
            "email": {"type": "string"},
            "phone": {"type": "string"},
            "primary_color": {"type": "string"},
            "secondary_color": {"type": "string"},
            "accent_color": {"type": "string"},
            "is_active": {"type": "boolean"},
        },
        required=["company_id"],
    ),
    # ── BANK ACCESS ──
    _fn(
        "list_bank_accesses",
        "Lista acessos bancários cadastrados. Filtros: usuário, banco, ativo.",
        {
            "user": {"type": "string"},
            "bank": {"type": "string"},
            "is_active": {"type": "boolean"},
            "limit": {"type": "integer"},
        },
    ),
    _fn(
        "create_bank_access",
        "Cria/atualiza um acesso bancário (upsert por bank+username).",
        {
            "bank": {"type": "string"},
            "username": {"type": "string"},
            "password": {"type": "string"},
            "user": {"type": "string", "description": "CPF/email/id do vendedor associado."},
            "is_active": {"type": "boolean"},
        },
        required=["bank", "username", "password"],
    ),
    _fn(
        "update_bank_access",
        "Atualiza um acesso bancário existente.",
        {
            "access_id": {"type": "string"},
            "username": {"type": "string"},
            "password": {"type": "string"},
            "is_active": {"type": "boolean"},
            "user": {"type": "string"},
        },
        required=["access_id"],
    ),
    # ── COMMISSION GROUPS ──
    _fn(
        "list_commission_groups",
        "Lista grupos de comissão (equipes).",
        {
            "company": {"type": "string"},
            "is_active": {"type": "boolean"},
            "search": {"type": "string"},
            "limit": {"type": "integer"},
        },
    ),
    _fn(
        "get_commission_group",
        "Retorna detalhes de uma equipe pelo id.",
        {"group_id": {"type": "string"}},
        required=["group_id"],
    ),
    _fn(
        "create_commission_group",
        "Cria uma nova equipe (grupo de comissão).",
        {
            "name": {"type": "string"},
            "company": {"type": "string"},
            "description": {"type": "string"},
            "by_leader": {"type": "boolean"},
            "leader": {"type": "string"},
            "color": {"type": "string"},
        },
        required=["name"],
    ),
    _fn(
        "update_commission_group",
        "Atualiza uma equipe. Passe apenas os campos a alterar.",
        {
            "group_id": {"type": "string"},
            "name": {"type": "string"},
            "description": {"type": "string"},
            "is_active": {"type": "boolean"},
            "by_leader": {"type": "boolean"},
            "leader": {"type": "string"},
            "color": {"type": "string"},
            "company": {"type": "string"},
        },
        required=["group_id"],
    ),
    _fn(
        "set_commission_group_members",
        "Adiciona ou remove vendedores/líderes de uma equipe. "
        "add=true adiciona, add=false remove.",
        {
            "group_id": {"type": "string"},
            "sellers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Lista de CPFs/IDs/emails de vendedores.",
            },
            "leaders": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Lista de CPFs/IDs/emails de líderes.",
            },
            "add": {"type": "boolean"},
        },
        required=["group_id"],
    ),
    # ── PROPOSALS / COMMISSIONS (read) ──
    _fn(
        "list_proposals",
        "Lista propostas (read-only). Filtros: vendedor, corban, banco, contrato, CPF do cliente, status.",
        {
            "seller": {"type": "string"},
            "company": {"type": "string"},
            "bank": {"type": "string"},
            "contract_number": {"type": "string"},
            "client_document": {"type": "string"},
            "status": {"type": "string"},
            "limit": {"type": "integer"},
        },
    ),
    _fn(
        "list_proposal_batches",
        "Lista lotes de processamento de propostas (read-only).",
        {"limit": {"type": "integer"}},
    ),
    _fn(
        "list_commissions",
        "Lista comissões (read-only). NÃO altera status: liberação/pagamento é fluxo financeiro.",
        {
            "user": {"type": "string"},
            "company": {"type": "string"},
            "role": {"type": "string", "description": "vendedor, lider, empresa"},
            "release_status": {"type": "string"},
            "limit": {"type": "integer"},
        },
    ),
]


TOOL_HANDLERS_EXTRA: dict[str, Any] = {
    "list_users": tool_list_users,
    "get_user": tool_get_user,
    "create_user": tool_create_user,
    "update_user": tool_update_user,
    "delete_user": tool_delete_user,
    "list_companies": tool_list_companies,
    "get_company": tool_get_company,
    "create_company": tool_create_company,
    "update_company": tool_update_company,
    "list_bank_accesses": tool_list_bank_accesses,
    "create_bank_access": tool_create_bank_access,
    "update_bank_access": tool_update_bank_access,
    "list_commission_groups": tool_list_commission_groups,
    "get_commission_group": tool_get_commission_group,
    "create_commission_group": tool_create_commission_group,
    "update_commission_group": tool_update_commission_group,
    "set_commission_group_members": tool_set_commission_group_members,
    "list_proposals": tool_list_proposals,
    "list_proposal_batches": tool_list_proposal_batches,
    "list_commissions": tool_list_commissions,
}


# Lista de nomes que NUNCA devem ser executados, mesmo se aparecerem em
# TOOL_HANDLERS por engano (defesa em profundidade contra alterações futuras).
PAYMENTS_FORBIDDEN_TOOLS = frozenset(
    {
        "create_payment",
        "update_payment",
        "delete_payment",
        "approve_payment",
        "create_manual_payment",
        "update_manual_payment",
        "create_withdraw",
        "update_withdraw",
        "release_commission",
        "pay_commission",
        "update_commission_status",
        "create_corban_pay_transaction",
    }
)
