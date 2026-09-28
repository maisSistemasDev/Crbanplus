"""Resolução de acesso bancário a partir do login da proposta."""
import re

from bank_access.models import BankAccess
from core.models import User
from core.utils import normalize_cpf

_EMAIL_RE = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE,
)
_EMAIL_CORE_RE = re.compile(
    r'(.+@.+?\.(?:com\.br|com|net|org|br|co|io))(?:\.[a-z0-9]+)*$',
    re.IGNORECASE,
)
_COMPACT_DOMAINS = (
    ('AUTOPROMOTORACOMBR', 'autopromotora.com.br'),
    ('AUTOPROMOTORACOM', 'autopromotora.com'),
    ('HOTMAILCOMBR', 'hotmail.com.br'),
    ('OUTLOOKCOMBR', 'outlook.com.br'),
    ('YAHOOCOMBR', 'yahoo.com.br'),
    ('GOOGLEMAILCOM', 'googlemail.com'),
    ('PROTONMAILCOM', 'protonmail.com'),
    ('GMAILCOM', 'gmail.com'),
    ('HOTMAILCOM', 'hotmail.com'),
    ('OUTLOOKCOM', 'outlook.com'),
    ('ICLOUDCOM', 'icloud.com'),
    ('YAHOOCOM', 'yahoo.com'),
    ('BOLCOMBR', 'bol.com.br'),
    ('UOLCOMBR', 'uol.com.br'),
    ('IGCOMBR', 'ig.com.br'),
    ('TERRACOMBR', 'terra.com.br'),
    ('LIVECOM', 'live.com'),
    ('YMAILCOM', 'ymail.com'),
    ('MSNCOM', 'msn.com'),
    ('MECOM', 'me.com'),
)
_LEADING_CODE_RE = re.compile(r'^(?:\d{1,6}_|-+)')
_CPF_MASK_RE = re.compile(r'(?<!\d)(\d{3})[.\s]?(\d{3})[.\s]?(\d{3})[-\s]?(\d{2})(?!\d)')
_EMPTY_LOGINS = frozenset(('', 'nan', 'none', 'null'))


def bank_access_queryset_for_actor(qs, actor):
    """Acessos visíveis ao usuário autenticado conforme hierarquia."""
    if actor.role in (User.ADMIN, User.COLABORADOR):
        if actor.role == User.ADMIN and actor.company_id:
            return qs.filter(user__company=actor.company)
        return qs
    if actor.role == User.EMPRESA_ADMIN:
        if actor.company_id:
            return qs.filter(user__company=actor.company)
        return qs
    if actor.role == User.GERENTE:
        if actor.company_id:
            return qs.filter(user__company=actor.company)
        return qs
    if actor.role == User.LIDER:
        return qs.filter(user__in=actor.team_members.all())
    return qs.filter(user=actor)


def filter_bank_accesses_by_user_profile(qs, user_id):
    """
    Filtra acessos do perfil informado e de outros perfis com o mesmo login_document
    (ex.: vendedor + corban no mesmo CPF).
    """
    target = User.objects.filter(pk=user_id).only('id', 'login_document').first()
    if not target:
        return qs.none()
    if target.login_document:
        profile_ids = User.objects.filter(
            login_document=target.login_document,
        ).values_list('id', flat=True)
        return qs.filter(user_id__in=profile_ids)
    return qs.filter(user_id=target.id)


def _stringify_login(value) -> str:
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    if re.fullmatch(r'\d+\.0+', text):
        return text.split('.', 1)[0]
    return text


def reconstruct_compact_email(value) -> str | None:
    """Reconstrói e-mail de logins da Prata sem @ (ex.: NOME950GMAILCOM → nome950@gmail.com)."""
    text = _stringify_login(value)
    if not text or '@' in text:
        return None
    blob = text.split()[0].upper().replace('.', '')
    blob = _LEADING_CODE_RE.sub('', blob)
    for token, domain in _COMPACT_DOMAINS:
        idx = blob.find(token)
        if idx <= 0:
            continue
        local = re.sub(r'[^A-Z0-9._%+-]', '', blob[:idx]).strip('._-').lower()
        if len(local) >= 3:
            return f'{local}@{domain}'
    return None


def extract_emails(value) -> list[str]:
    """E-mails encontrados no texto, em minúsculas (ignora texto extra ao redor)."""
    found = [match.group(0).lower() for match in _EMAIL_RE.finditer(_stringify_login(value))]
    extra: list[str] = []
    for email in found:
        core = _EMAIL_CORE_RE.match(email)
        if core:
            cleaned = core.group(1).lower()
            if cleaned != email:
                extra.append(cleaned)
    reconstructed = reconstruct_compact_email(value)
    if reconstructed:
        extra.append(reconstructed)
    seen: set[str] = set()
    ordered: list[str] = []
    for email in found + extra:
        if email not in seen:
            seen.add(email)
            ordered.append(email)
    return ordered


def extract_cpf_digits(value, *, force: bool = False) -> str | None:
    """
    CPF de 11 dígitos a partir do valor do arquivo ou do cadastro.

    Ignora pontuação (015.642.352-87 == 01564235287). Se force=True (banco
    com login por CPF), extrai os dígitos mesmo com texto extra ao redor.
    """
    text = _stringify_login(value)
    if not text:
        return None
    if not force and extract_emails(text):
        return None

    masked = _CPF_MASK_RE.search(text)
    if masked:
        return normalize_cpf(''.join(masked.groups()))

    digits = re.sub(r'\D', '', text)
    if 9 <= len(digits) <= 11:
        return normalize_cpf(digits)
    return None


def login_values_match(file_value, stored_value, login_type: str | None = None) -> bool:
    """Compara login do arquivo com username/alias cadastrado, normalizando CPF e e-mail."""
    from bank.models import Bank

    left = _stringify_login(file_value)
    right = _stringify_login(stored_value)
    if not left or not right:
        return False
    if left.lower() in _EMPTY_LOGINS or right.lower() in _EMPTY_LOGINS:
        return False

    force_cpf = login_type == Bank.ACCESS_LOGIN_CPF
    left_emails = extract_emails(left)
    right_emails = extract_emails(right)
    left_cpf = extract_cpf_digits(left, force=force_cpf)
    right_cpf = extract_cpf_digits(right, force=force_cpf)

    if force_cpf and left_cpf and right_cpf:
        return left_cpf == right_cpf

    if left_emails:
        right_set = set(right_emails)
        right_set.add(right.lower().strip())
        if any(email in right_set for email in left_emails):
            return True

    if left_cpf and right_cpf and left_cpf == right_cpf:
        return True

    return left.lower().strip() == right.lower().strip()


def resolve_bank_access(bank, login) -> BankAccess | None:
    """
    Localiza BankAccess pelo login dentro do banco da proposta.
    CPF: ignora pontuação nos dois lados.
    E-mail: usa só o endereço, mesmo com texto extra (ex.: "ana@x.com (gerente)").
    """
    value = _stringify_login(login)
    if not value or value.lower() in _EMPTY_LOGINS:
        return None

    login_type = getattr(bank, 'access_login_type', None)
    qs = BankAccess.objects.filter(bank=bank, is_active=True).select_related('user', 'bank')

    for item in qs:
        if login_values_match(value, item.username, login_type):
            return item
        aliases = item.alias or []
        if not isinstance(aliases, list):
            continue
        for alias in aliases:
            if login_values_match(value, alias, login_type):
                return item

    return None
