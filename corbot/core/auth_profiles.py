"""
Autenticação com múltiplos perfis por pessoa (ex.: vendedor + admin de corban).

Cada perfil é um registro User independente (role, company, ExtraData, senha).
O login_document agrupa perfis que compartilham o mesmo CPF/CNPJ de acesso.
"""
import re

from django.contrib.auth import get_user_model

User = get_user_model()

CORBAN_ROLES = frozenset({User.EMPRESA_ADMIN})
TEAM_ROLES = frozenset({User.VENDEDOR, User.LIDER, User.GERENTE})


def normalize_login_document(value: str) -> str:
    return re.sub(r'\D', '', str(value or ''))


def build_profile_username(login_document: str, role: str, company_id) -> str:
    suffix = str(company_id) if company_id else 'none'
    return f'{login_document}:{role}:{suffix}'


def get_profile_type(user) -> str:
    """Retorna 'promotora', 'corban' ou 'vendedor' para a tela de seleção."""
    if user.role in (User.ADMIN, User.COLABORADOR):
        return 'promotora'
    if user.role == User.EMPRESA_ADMIN:
        return 'corban'
    return 'vendedor'


def get_profile_label(user) -> str:
    role_label = user.get_role_display()
    if user.role in (User.ADMIN, User.COLABORADOR):
        return f'{role_label} — Promotora'
    company = user.company.name if user.company else 'Sem empresa'
    if user.role == User.EMPRESA_ADMIN:
        return f'Corban — {company}'
    return f'{role_label} — {company}'


def serialize_login_profile(user) -> dict:
    return {
        'user_id': user.id,
        'profile_type': get_profile_type(user),
        'role': user.role,
        'role_label': user.get_role_display(),
        'company_name': user.company.name if user.company else None,
        'label': get_profile_label(user),
    }


def _candidates_for_document(login_doc: str):
    """Usuários ativos cujo login_document ou CNPJ da empresa bate com o documento."""
    from core.models import Company

    qs = User.objects.filter(is_active=True).select_related('company')

    by_login = qs.filter(login_document=login_doc)
    if by_login.exists():
        return by_login

    # Fallback: admin de corban PJ que faz login pelo CNPJ da empresa
    try:
        company = Company.objects.get(document=login_doc)
        return qs.filter(company=company, role=User.EMPRESA_ADMIN)
    except Company.DoesNotExist:
        return qs.none()


def find_users_for_login(document: str, password: str) -> list:
    """
    Retorna perfis cujo documento de login coincide e a senha confere.
    Perfis com senhas diferentes são ignorados (não entram na seleção).
    """
    login_doc = normalize_login_document(document)
    if not login_doc:
        return []

    matched = []
    for user in _candidates_for_document(login_doc):
        if user.check_password(password):
            matched.append(user)

    return matched


def ensure_profile_credentials(user, *, login_document=None, cpf=None):
    """
    Preenche username/login_document antes de salvar um novo perfil.
    Chamado pelo User.save() e pelo UserManager.
    """
    if cpf:
        user.cpf = re.sub(r'\D', '', cpf)
    if login_document:
        user.login_document = normalize_login_document(login_document)
    elif not user.login_document and user.cpf:
        user.login_document = normalize_login_document(user.cpf)

    if not user.username and user.login_document and user.role:
        company_id = user.company_id if user.company_id else None
        user.username = build_profile_username(user.login_document, user.role, company_id)
