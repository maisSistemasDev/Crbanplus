"""Grupos de comissionamento e links de cadastro via integração."""
from __future__ import annotations

from datetime import datetime

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from core.integration_permissions import assert_api_key_company_access
from core.models import APIKey, Company, User
from core.integrations.helpers import build_registration_url
from payments.models import (
    CommissionGroup,
    CommissionGroupRegistrationLink,
    CommissionRulesByUser,
)
from payments.serializers import CommissionRulesByUserSerializer
from payments.views.comission_group import validate_company_rules


def _parse_expires_at(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    parsed = parse_datetime(str(value))
    if not parsed:
        raise ValidationError({'registration': {'expires_at': ['Data de expiração inválida.']}})
    return parsed


@transaction.atomic
def create_commission_group(
    *,
    api_key: APIKey,
    name: str,
    company_id: str,
    description: str = '',
    color: str = '#3b82f6',
    commission_rules: list[dict] | None = None,
    registration: dict | None = None,
    request=None,
) -> dict:
    assert_api_key_company_access(api_key, company_id)

    if not name or not str(name).strip():
        raise ValidationError({'name': ['Obrigatório.']})

    try:
        company = Company.objects.get(id=company_id, is_active=True)
    except Company.DoesNotExist:
        raise ValidationError({'company_id': ['Corban não encontrado.']})

    rules_data = commission_rules or []
    if rules_data:
        errors = validate_company_rules(rules_data, company)
        if errors:
            raise ValidationError({'commission_rules': errors})

    group = CommissionGroup.objects.create(
        name=name,
        description=description or '',
        company=company,
        color=color or '#3b82f6',
        is_active=True,
        by_leader=False,
    )

    rules = []
    for rule in rules_data:
        rule_serializer = CommissionRulesByUserSerializer(data=rule)
        if not rule_serializer.is_valid():
            raise ValidationError({'commission_rules': rule_serializer.errors})
        rules.append(rule_serializer.save())
    if rules:
        group.commission_rules.set(rules)

    result = {
        'id': group.id,
        'name': group.name,
        'company_id': str(company.id),
    }

    if registration is not None:
        link = create_registration_link(
            api_key=api_key,
            group=group,
            company=company,
            expires_at=_parse_expires_at(registration.get('expires_at')),
            max_uses=registration.get('max_uses'),
            allowed_role=registration.get('allowed_role') or User.VENDEDOR,
            request=request,
        )
        result['registration'] = link

    return result


@transaction.atomic
def create_registration_link(
    *,
    api_key: APIKey | None = None,
    group: CommissionGroup,
    company: Company | None = None,
    expires_at=None,
    max_uses: int | None = None,
    allowed_role: str = User.VENDEDOR,
    created_by: User | None = None,
    request=None,
) -> dict:
    company = company or group.company
    if not company:
        raise ValidationError({'detail': ['Grupo sem Corban vinculado.']})

    if api_key:
        assert_api_key_company_access(api_key, company.id)

    allowed_role = allowed_role or User.VENDEDOR
    if allowed_role != User.VENDEDOR:
        raise ValidationError({'allowed_role': ['Apenas cadastro de vendedor é permitido.']})
    if expires_at and expires_at <= timezone.now():
        raise ValidationError({'expires_at': ['A expiração deve estar no futuro.']})
    if max_uses is not None:
        try:
            max_uses = int(max_uses)
        except (TypeError, ValueError):
            raise ValidationError({'max_uses': ['Informe um número inteiro válido.']})
        if max_uses < 1:
            raise ValidationError({'max_uses': ['Informe ao menos 1 uso.']})

    full_token, prefix, token_hash = CommissionGroupRegistrationLink.generate_token()
    link = CommissionGroupRegistrationLink.objects.create(
        commission_group=group,
        company=company,
        token_prefix=prefix,
        token_hash=token_hash,
        created_by_api_key=api_key,
        created_by=created_by,
        expires_at=expires_at,
        max_uses=max_uses,
        allowed_role=allowed_role,
    )

    return {
        'id': str(link.id),
        'url': build_registration_url(full_token, request=request),
        'token': full_token,
        'expires_at': link.expires_at.isoformat() if link.expires_at else None,
        'max_uses': link.max_uses,
        'uses_count': link.uses_count,
    }


@transaction.atomic
def revoke_registration_link(link_id: str, api_key: APIKey) -> None:
    try:
        link = CommissionGroupRegistrationLink.objects.select_related('company').get(id=link_id)
    except CommissionGroupRegistrationLink.DoesNotExist:
        raise ValidationError({'detail': ['Link de cadastro não encontrado.']})

    assert_api_key_company_access(api_key, link.company_id)
    link.is_active = False
    link.save(update_fields=['is_active', 'updated_at'])
