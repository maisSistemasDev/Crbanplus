"""Criação transacional de vendedores via integração."""
from __future__ import annotations

import re
import secrets

from django.db import transaction
from rest_framework.exceptions import ValidationError

from core.integration_permissions import assert_api_key_company_access
from core.models import APIKey, Company, ExtraData, User, validate_pix_binding
from payments.models import CommissionGroup


@transaction.atomic
def create_seller(
    *,
    api_key: APIKey,
    company_id: str,
    cpf: str,
    email: str,
    first_name: str = '',
    last_name: str = '',
    password: str | None = None,
    leader_id: int | None = None,
    commission_group_id: int | None = None,
    matricula: str | None = None,
    certificado: str | None = None,
    extra_data: dict | None = None,
) -> dict:
    assert_api_key_company_access(api_key, company_id)

    try:
        company = Company.objects.get(id=company_id, is_active=True)
    except Company.DoesNotExist:
        raise ValidationError({'company_id': ['Corban não encontrado.']})

    cpf = re.sub(r'\D', '', cpf or '')
    if len(cpf) != 11:
        raise ValidationError({'cpf': ['CPF deve ter 11 dígitos.']})

    if User.objects.filter(login_document=cpf, role=User.VENDEDOR, company=company).exists():
        raise ValidationError({'cpf': ['Já existe vendedor com este CPF neste Corban.']})

    pix_error = validate_pix_binding(
        pix_type=(extra_data or {}).get('pix_type'),
        pix_key=(extra_data or {}).get('pix_key'),
        cpf=cpf,
        cnpj=company.document,
    )
    if pix_error:
        raise ValidationError({'extra_data': {'pix_key': [pix_error]}})

    leader = None
    if leader_id:
        leader = User.objects.filter(
            id=leader_id,
            company=company,
            role=User.LIDER,
        ).first()
        if not leader:
            raise ValidationError({'leader_id': ['Líder não encontrado neste Corban.']})

    temporary_password = None
    if not password:
        password = secrets.token_urlsafe(16)
        temporary_password = password

    user = User.objects.create_user(
        cpf=cpf,
        login_document=cpf,
        password=password,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=User.VENDEDOR,
        company=company,
        leader=leader,
        matricula=matricula,
        certificado=certificado,
        is_active=True,
    )
    ExtraData.objects.create(user=user, **(extra_data or {}))

    if commission_group_id:
        _add_user_to_commission_group(user, company, commission_group_id)

    result = {
        'user_id': user.id,
        'cpf': cpf,
        'company_id': str(company.id),
        'commission_group_id': commission_group_id,
    }
    if temporary_password:
        result['temporary_password'] = temporary_password
    return result


def _add_user_to_commission_group(user: User, company: Company, group_id: int) -> CommissionGroup:
    try:
        group = CommissionGroup.objects.get(id=group_id, company=company, is_active=True)
    except CommissionGroup.DoesNotExist:
        raise ValidationError({'commission_group_id': ['Grupo de comissionamento não encontrado.']})
    group.sellers.add(user)
    return group
