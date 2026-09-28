"""Cadastro público de vendedor via link de grupo."""
from __future__ import annotations

import re

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.models import ExtraData, User, validate_pix_binding
from payments.models import CommissionGroupRegistrationLink


def get_registration_info(link: CommissionGroupRegistrationLink) -> dict:
    group = link.commission_group
    return {
        'group_id': group.id,
        'group_name': group.name,
        'group_color': group.color,
        'company_id': str(link.company_id),
        'company_name': link.company.name,
        'allowed_role': link.allowed_role,
        'expires_at': link.expires_at.isoformat() if link.expires_at else None,
        'uses_remaining': (
            None if link.max_uses is None else max(0, link.max_uses - link.uses_count)
        ),
    }


@transaction.atomic
def register_seller_via_link(
    link: CommissionGroupRegistrationLink,
    *,
    cpf: str,
    email: str,
    first_name: str,
    last_name: str,
    password: str,
    extra_data: dict | None = None,
) -> dict:
    if not link.is_usable():
        raise ValidationError({'detail': ['Link de cadastro expirado, revogado ou esgotado.']})

    if link.allowed_role != User.VENDEDOR:
        raise ValidationError({'detail': ['Este link não permite cadastro de vendedor.']})

    cpf = re.sub(r'\D', '', cpf or '')
    if len(cpf) != 11:
        raise ValidationError({'cpf': ['CPF deve ter 11 dígitos.']})

    if len(password or '') < 6:
        raise ValidationError({'password': ['A senha deve ter pelo menos 6 caracteres.']})

    company = link.company
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

    user = User.objects.create_user(
        cpf=cpf,
        login_document=cpf,
        password=password,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=User.VENDEDOR,
        company=company,
        is_active=True,
    )
    ExtraData.objects.create(user=user, **(extra_data or {}))

    group = link.commission_group
    group.sellers.add(user)

    link.uses_count += 1
    link.save(update_fields=['uses_count', 'updated_at'])

    return {
        'user_id': user.id,
        'commission_group_id': group.id,
        'company_id': str(company.id),
        'registered_at': timezone.now().isoformat(),
    }
