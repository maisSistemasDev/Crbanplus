import re
import unicodedata

from core.models import User, ExtraData

# Colunas alternativas comuns em planilhas de importação
_IMPORT_COLUMN_ALIASES = {
    'chave_pix': 'pix_key',
    'tipo_pix': 'pix_type',
    'tipo_de_chave': 'pix_type',
    'tipo_chave': 'pix_type',
    'admin_chave_pix': 'admin_pix_key',
    'admin_tipo_pix': 'admin_pix_type',
    'admin_tipo_de_chave': 'admin_pix_type',
    'cpf_do_corban': 'cpf_corban',
    'cpf_admin': 'cpf_corban',
    'admin_cpf_corban': 'cpf_corban',
    'enrollment': 'matricula',
    'matricula': 'matricula',
    'admin_enrollment': 'admin_matricula',
    'admin_matricula': 'admin_matricula',
    'observacao': 'notes',
    'observação': 'notes',
    'observation': 'notes',
    'link_acesso': 'link',
    'url': 'link',
    'master': 'is_master',
    'is_master': 'is_master',
    'acesso_master': 'is_master',
}

_VALID_PIX_TYPES = {choice[0] for choice in ExtraData.PIX_TYPE_CHOICES}

_PIX_TYPE_ALIASES = {
    'cpf': 'CPF',
    'cnpj': 'CNPJ',
    'email': 'EMAIL',
    'e-mail': 'EMAIL',
    'e_mail': 'EMAIL',
    'mail': 'EMAIL',
    'celular': 'CELULAR',
    'telefone': 'CELULAR',
    'phone': 'CELULAR',
    'chave_aleatoria': 'CHAVE_ALEATORIA',
    'chave aleatoria': 'CHAVE_ALEATORIA',
    'chave aleatória': 'CHAVE_ALEATORIA',
    'aleatoria': 'CHAVE_ALEATORIA',
    'aleatória': 'CHAVE_ALEATORIA',
    'random': 'CHAVE_ALEATORIA',
    'uuid': 'CHAVE_ALEATORIA',
}


def _digits(value) -> str:
    """Mantém apenas dígitos. Aceita None/int/float/str."""
    if value is None:
        return ''
    return re.sub(r'\D', '', str(value))


def normalize_cpf(value) -> str:
    """
    Normaliza CPF para 11 dígitos.

    Excel/pandas costumam ler CPF como número e perder zeros à esquerda
    (ex.: '08054241569' vira 8054241569 com 10 dígitos). Aqui aplicamos
    zfill quando o resultado tem entre 1 e 11 dígitos para restaurar o zero.
    """
    digits = _digits(value)
    if 1 <= len(digits) <= 11:
        digits = digits.zfill(11)
    return digits


def normalize_cnpj(value) -> str:
    """Normaliza CNPJ para 14 dígitos (mesma lógica do normalize_cpf)."""
    digits = _digits(value)
    if 1 <= len(digits) <= 14:
        digits = digits.zfill(14)
    return digits


def normalize_document(value, person_type: str | None = None) -> str:
    """
    Normaliza CPF ou CNPJ baseado em person_type (PF/PJ).

    Se person_type não for fornecido, decide pelo tamanho:
    até 11 dígitos → CPF; de 12 a 14 → CNPJ.
    """
    digits = _digits(value)
    if person_type and person_type.upper() in ('PF', 'CPF'):
        return normalize_cpf(digits)
    if person_type and person_type.upper() in ('PJ', 'CNPJ'):
        return normalize_cnpj(digits)
    if len(digits) <= 11:
        return normalize_cpf(digits)
    return normalize_cnpj(digits)


_ROLE_MATRICULA_SUFFIX = {
    User.VENDEDOR: 'V',
    User.LIDER: 'L',
    User.GERENTE: 'G',
    User.EMPRESA_ADMIN: 'A',
}


def matricula_taken(company, matricula, exclude_user_id=None) -> bool:
    """Verifica se matrícula já existe na empresa."""
    if not company or not matricula:
        return False
    qs = User.objects.filter(company=company, matricula=matricula)
    if exclude_user_id:
        qs = qs.exclude(pk=exclude_user_id)
    return qs.exists()


def ensure_unique_matricula(user, company, preferred: str | None = None) -> str:
    """
    Garante matrícula única por (company, matricula).

    Acesso duplo (corban + vendedor, mesmo CPF) usa sufixo por role
    (ex.: 70716065444-V para vendedor quando admin já usa 70716065444).
    """
    if not company:
        return preferred or user.matricula or user.cpf

    base = (preferred or user.matricula or user.cpf or '').strip() or user.cpf

    if not matricula_taken(company, base, user.pk):
        return base

    suffix = _ROLE_MATRICULA_SUFFIX.get(user.role, 'P')
    for candidate in (f'{user.cpf}-{suffix}', f'{base}-{suffix}'):
        if candidate and not matricula_taken(company, candidate, user.pk):
            return candidate

    for n in range(2, 100):
        candidate = f'{user.cpf}-{suffix}{n}'
        if not matricula_taken(company, candidate, user.pk):
            return candidate

    import uuid
    return f'{user.cpf}-{uuid.uuid4().hex[:6]}'


def normalize_import_row(row: dict) -> dict:
    """
    Normaliza nomes de colunas de planilhas (sinônimos → nomes canônicos).
    """
    out: dict = {}
    for key, value in row.items():
        normalized_key = re.sub(r'\s+', '_', str(key).strip().lower())
        canonical = _IMPORT_COLUMN_ALIASES.get(normalized_key, normalized_key)
        if canonical not in out or out[canonical] is None:
            out[canonical] = value
    return out


def normalize_pix_type(value) -> str | None:
    """
    Converte rótulos comuns de planilha (email, telefone, E-mail…) para o
    código armazenado em ExtraData (EMAIL, CELULAR, CPF…).
    """
    if value is None:
        return None
    raw = str(value).strip()
    if not raw or raw.lower() in ('nan', 'none', '-', 'n/a'):
        return None

    upper = raw.upper().replace('-', '_').replace(' ', '_')
    if upper in _VALID_PIX_TYPES:
        return upper

    lower = raw.lower().strip()
    if lower in _PIX_TYPE_ALIASES:
        return _PIX_TYPE_ALIASES[lower]

    no_accent = ''.join(
        c for c in unicodedata.normalize('NFD', lower)
        if unicodedata.category(c) != 'Mn'
    )
    return _PIX_TYPE_ALIASES.get(no_accent) or _PIX_TYPE_ALIASES.get(no_accent.replace(' ', '_'))


def infer_pix_type_from_key(pix_key: str, fallback: str = 'CPF') -> str:
    """Infere o tipo PIX pela forma da chave quando a planilha não informa."""
    if not pix_key:
        return fallback

    key = str(pix_key).strip()
    if '@' in key:
        return 'EMAIL'

    if re.match(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        key.lower(),
    ):
        return 'CHAVE_ALEATORIA'

    digits = _digits(key)
    if len(digits) == 14:
        return 'CNPJ'
    if len(digits) == 11:
        # Celular BR: DDD + 9 dígitos começando com 9
        if digits[2] == '9':
            return 'CELULAR'
        return 'CPF'
    if 10 <= len(digits) <= 11:
        return 'CELULAR'

    return fallback


def pix_type_label(code: str | None) -> str:
    """Retorna label legível do tipo PIX para relatórios."""
    labels = dict(ExtraData.PIX_TYPE_CHOICES)
    if code and code in labels:
        return labels[code]
    return labels.get('CPF', 'CPF')


def resolve_pix_fields(
    pix_key_raw,
    pix_type_raw,
    *,
    fallback_key: str | None = None,
) -> tuple[str | None, str | None]:
    """
    Normaliza par pix_key/pix_type vindos de import ou export.
    Infere o tipo pela chave quando necessário.
    """
    pix_key = (str(pix_key_raw).strip() if pix_key_raw else '') or None
    pix_type = normalize_pix_type(pix_type_raw)
    if pix_key and not pix_type:
        pix_type = infer_pix_type_from_key(pix_key, fallback='CPF')
    if not pix_key and fallback_key:
        pix_key = fallback_key
        if not pix_type:
            pix_type = infer_pix_type_from_key(pix_key, fallback='CPF')
    return pix_key, pix_type


class UserInstance:
    def __init__(self, user: User):
        self.user = user
        self.name = user.get_full_name()
        self.email = user.email
        self.cpf = user.cpf
        self.extra_data = self._load_extra_data()
        self.phone = None
        self.pix_key = None
        self.pix_type = None
        self.birth_date = None
        self.role = user.role
        self.leader = user.leader
        self.company = user.company if user.company else None
        self.is_active = user.is_active
        self.is_staff = user.is_staff
        self.is_superuser = user.is_superuser if user.is_superuser else False
    
    def _load_extra_data(self) -> ExtraData:
        try:
            extra_data = ExtraData.objects.get(user=self.user)
            self.pix_key = extra_data.pix_key
            self.pix_type = extra_data.pix_type
            self.birth_date = extra_data.birth_date
            return extra_data
        except ExtraData.DoesNotExist:
            return None

    def __str__(self):
        return f"UserInstance(user={self.user.id}, name={self.name}, email={self.email}, cpf={self.cpf}, extra_data={self.extra_data})"