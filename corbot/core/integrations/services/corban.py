"""Criação transacional de Corbans via integração."""
from __future__ import annotations

import re
import secrets

from django.db import transaction
from rest_framework.exceptions import ValidationError

from core.models import Company, User
from core.serializers import CompanySerializer
from payments.models import CommissionGroupByCompany


@transaction.atomic
def create_corban(
    *,
    company_data: dict,
    admin_user_data: dict | None = None,
    commission_group_by_company_id: int | None = None,
) -> dict:
    admin_user_data = admin_user_data or {}

    company_serializer = CompanySerializer(data=company_data)
    if not company_serializer.is_valid():
        raise ValidationError({'company': company_serializer.errors})

    document = re.sub(r'\D', '', company_data.get('document', ''))
    if Company.objects.filter(document=document).exists():
        raise ValidationError({'company': {'document': ['Corban com este documento já existe.']}})

    company = company_serializer.save()

    if User.objects.filter(role=User.EMPRESA_ADMIN, company=company).exists():
        raise ValidationError({'detail': 'Já existe administrador para este Corban.'})

    password = admin_user_data.get('password')
    temporary_password = None
    if not password:
        password = secrets.token_urlsafe(16)
        temporary_password = password

    email = admin_user_data.get('email') or company.email
    if not email:
        email = f'{document}@corban.local'

    admin_user = User.objects.create_user(
        cpf=document,
        login_document=document,
        password=password,
        email=email,
        first_name=company.name,
        last_name='',
        matricula=admin_user_data.get('matricula'),
        certificado=admin_user_data.get('certificado'),
        role=User.EMPRESA_ADMIN,
        company=company,
        is_active=True,
    )

    if commission_group_by_company_id:
        _assign_company_to_promotora_group(company, commission_group_by_company_id)

    result = {
        'company_id': str(company.id),
        'admin_user_id': admin_user.id,
        'login_document': document,
        'company_name': company.name,
    }
    if temporary_password:
        result['temporary_password'] = temporary_password
    return result


def _assign_company_to_promotora_group(company: Company, group_id: int) -> None:
    try:
        target = CommissionGroupByCompany.objects.get(id=group_id, is_active=True)
    except CommissionGroupByCompany.DoesNotExist:
        raise ValidationError({
            'commission_group_by_company_id': ['Grupo de Corbans da promotora não encontrado.'],
        })

    for old_group in CommissionGroupByCompany.objects.filter(companies=company):
        old_group.companies.remove(company)
    target.companies.add(company)
