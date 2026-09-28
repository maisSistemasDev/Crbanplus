"""Validações de acesso bancário."""
import re

from django.core.exceptions import ValidationError

from core.utils import normalize_cpf


def _digits(value: str) -> str:
    return re.sub(r'\D', '', str(value or ''))


def validate_bank_access_instance(access, *, bank=None, user=None, username=None, is_master=None):
    """
    Regras:
      - Banco login CPF: username = CPF do usuário; no máximo 1 acesso por (user, bank).
      - Banco login email: vários acessos por (user, bank) com usernames diferentes.
      - is_master: só pode ser true no perfil Corban (empresa_admin).
      - Corban pode ter acessos extras não-master (logins de digitador/equipe).
    """
    from bank.models import Bank
    from bank_access.models import BankAccess

    bank = bank or access.bank
    user = user if user is not None else access.user
    username = username if username is not None else access.username
    is_master = access.is_master if is_master is None else is_master

    if user and is_master and user.role != user.EMPRESA_ADMIN:
        raise ValidationError(
            'Acesso master deve estar vinculado ao perfil Corban (empresa_admin).'
        )

    if not bank or not user:
        return

    login_type = getattr(bank, 'access_login_type', Bank.ACCESS_LOGIN_EMAIL)

    if login_type == Bank.ACCESS_LOGIN_CPF:
        user_cpf = normalize_cpf(user.cpf)
        login_cpf = normalize_cpf(username)
        if login_cpf != user_cpf:
            raise ValidationError(
                'Para bancos com login por CPF, o usuário do acesso deve ser o CPF do vendedor.'
            )

        qs = BankAccess.objects.filter(user=user, bank=bank)
        if access.pk:
            qs = qs.exclude(pk=access.pk)
        if qs.exists():
            raise ValidationError(
                'Este usuário já possui acesso neste banco (login por CPF permite apenas um).'
            )
