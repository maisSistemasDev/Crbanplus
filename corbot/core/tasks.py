"""
Tasks Celery para importação em lote de entidades via CSV/XLSX.
"""
import logging
import re

from celery import shared_task

from core.utils import (
    normalize_cpf,
    normalize_cnpj,
    normalize_document,
    normalize_import_row,
    resolve_pix_fields,
    ensure_unique_matricula,
)
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db import transaction, IntegrityError

logger = logging.getLogger(__name__)


def _push_progress(job_id: str, job):
    """Envia atualização de progresso via WebSocket (best-effort)."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'import_job_{job_id}',
                {
                    'type': 'job_update',
                    'message': {
                        'job_id': job_id,
                        'status': job.status,
                        'total_rows': job.total_rows,
                        'processed_rows': job.processed_rows,
                        'created_count': job.created_count,
                        'error_count': job.error_count,
                        'progress_pct': job.progress_pct,
                    },
                },
            )
    except Exception as exc:
        logger.debug('WS push error (import_job %s): %s', job_id, exc)


def _read_file(file_path: str) -> list[dict]:
    """Lê CSV ou XLSX e retorna lista de dicts."""
    import pandas as pd
    import math

    # dtype=str em ambos: força colunas numéricas (CPF/CNPJ/telefone com zero
    # à esquerda) a serem lidas como texto e preservar os zeros.
    if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
        df = pd.read_excel(file_path, dtype=str)
    else:
        df = pd.read_csv(file_path, dtype=str)

    # Normaliza nomes das colunas: tira espaços, baixa para minúsculas e
    # troca espaços por underscore ("Chave Pix" → chave_pix).
    df.columns = [re.sub(r'\s+', '_', str(c).strip().lower()) for c in df.columns]

    records = df.to_dict(orient='records')

    def _clean(v):
        if v is None:
            return None
        if isinstance(v, float) and math.isnan(v):
            return None
        return str(v).strip() if str(v).strip() not in ('', 'nan', 'NaN', 'None') else None

    return [normalize_import_row({k: _clean(v) for k, v in row.items()}) for row in records]


# ─────────────────────────────────────────────────────────────────────────────
# Funções de criação por tipo
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_company_from_row(
    row: dict,
    requesting_company_id,
    *,
    promotora_import: bool = False,
) -> tuple:
    """
    Resolve a Company (corban) a partir da linha do import.

    Promotora (admin/colaborador): vínculo só por company_document ou cpf_corban.
    Corbans (gerente etc.): pode usar a empresa de quem disparou o import como fallback.

    Ordem de prioridade:
      1. company_document — CNPJ/CPF da empresa
      2. cpf_corban — admin do corban OU corban PF (document = CPF do admin)
      3. empresa do usuário que disparou o import (apenas se NÃO for promotora)
    """
    from django.db.models import Q
    from core.models import User, Company

    if row.get('company_document'):
        try:
            return Company.objects.get(
                document=normalize_document(row['company_document']),
            ), None
        except Company.DoesNotExist:
            return None, f"Corban não encontrado: {row['company_document']}"

    if row.get('cpf_corban'):
        admin_cpf = normalize_cpf(row['cpf_corban'])

        admin = User.objects.filter(
            Q(login_document=admin_cpf) | Q(cpf=admin_cpf),
            role=User.EMPRESA_ADMIN,
            company__isnull=False,
        ).select_related('company').first()
        if admin:
            return admin.company, None

        pf_corban = Company.objects.filter(
            document=admin_cpf,
            person_type=Company.PERSON_TYPE_PF,
            is_promotora=False,
        ).first()
        if pf_corban:
            return pf_corban, None

        return None, (
            f"Corban não encontrado para cpf_corban {admin_cpf} "
            f"(sem admin nem empresa PF com esse documento)"
        )

    if requesting_company_id and not promotora_import:
        try:
            return Company.objects.get(id=requesting_company_id), None
        except Company.DoesNotExist:
            pass

    return None, None


def _create_user_row(
    row: dict,
    role: str,
    requesting_company_id,
    update_existing: bool = False,
    *,
    promotora_import: bool = False,
) -> tuple[str | None, bool]:
    """
    Cria (ou atualiza, se update_existing=True) um usuário
    (vendedor/lider/gerente) a partir de uma linha do CSV.

    Retorna (error, was_updated):
      - (None, False) → criado
      - (None, True)  → atualizado
      - ("msg", _)    → erro
    """
    from core.models import User, ExtraData, Company

    # Em update_existing, password não é obrigatório (mantém o atual).
    required = ['cpf', 'email', 'first_name'] if update_existing else ['cpf', 'email', 'first_name', 'password']
    for f in required:
        if not row.get(f):
            return f"Campo obrigatório ausente: '{f}'", False

    cpf_clean = normalize_cpf(row['cpf'])

    if promotora_import and not row.get('cpf_corban') and not row.get('company_document'):
        return (
            "cpf_corban é obrigatório quando o import é feito pela promotora",
            False,
        )

    company, company_err = _resolve_company_from_row(
        row, requesting_company_id, promotora_import=promotora_import,
    )
    if company_err:
        return company_err, False
    if not company:
        if promotora_import:
            return (
                "Informe cpf_corban (CPF do admin do corban) para vincular à empresa",
                False,
            )
        return (
            "Informe cpf_corban (CPF do admin do corban) ou company_document "
            "para vincular à empresa",
            False,
        )

    leader = None
    if row.get('leader_cpf'):
        leader_cpf = normalize_cpf(row['leader_cpf'])
        try:
            leader = User.objects.get(cpf=leader_cpf, role__in=[User.LIDER, User.GERENTE])
        except User.DoesNotExist:
            return f"Líder com CPF {leader_cpf} não encontrado", False

    extra_fields = ['rg', 'rg_emission_date', 'rg_emission_organ',
                    'birth_date', 'phone']
    extra = {k: row[k] for k in extra_fields if row.get(k)}

    pix_key, pix_type = resolve_pix_fields(
        row.get('pix_key'),
        row.get('pix_type'),
    )
    if pix_key:
        extra['pix_key'] = pix_key
    if pix_type:
        extra['pix_type'] = pix_type

    existing = (
        User.objects.filter(cpf=cpf_clean, role=role, company=company).first()
        if update_existing else None
    )

    # Import de equipe nunca reaproveita perfil empresa_admin (acesso duplo).
    # Bug anterior: upsert só por CPF convertia corban → vendedor.
    if existing and existing.role == User.EMPRESA_ADMIN:
        existing = None

    # Mesma proteção do _create_corban_row: não rebaixar internos da
    # promotora pelo import de equipe.
    if existing and existing.role in (User.ADMIN, User.COLABORADOR):
        return (
            f"CPF {cpf_clean} pertence a um usuário interno da promotora "
            f"({existing.get_role_display()}); operação ignorada.",
            False,
        )

    with transaction.atomic():
        if existing:
            existing.email = row['email']
            existing.first_name = row['first_name']
            existing.last_name = row.get('last_name') or ''
            existing.role = role
            existing.company = company
            existing.leader = leader
            existing.matricula = ensure_unique_matricula(
                existing, company, row.get('matricula'),
            )
            if row.get('password'):
                existing.set_password(row['password'])
            existing.save()

            if extra:
                ExtraData.objects.update_or_create(user=existing, defaults=extra)
            elif pix_key or pix_type:
                ExtraData.objects.update_or_create(
                    user=existing,
                    defaults={'pix_key': pix_key, 'pix_type': pix_type},
                )
            return None, True

        user = User.objects.create_user(
            cpf=cpf_clean,
            login_document=cpf_clean,
            email=row['email'],
            first_name=row['first_name'],
            last_name=row.get('last_name') or '',
            role=role,
            company=company,
            leader=leader,
        )
        user.set_password(row['password'])
        user.matricula = ensure_unique_matricula(user, company, row.get('matricula'))
        user.save()

        if extra:
            ExtraData.objects.create(user=user, **extra)

    return None, False


def _create_corban_row(
    row: dict,
    update_existing: bool = False,
) -> tuple[str | None, bool]:
    """
    Cria (ou atualiza) um Company (corban) e seu usuário administrador
    (empresa_admin). Quando update_existing=True, identifica registros
    existentes pelo `document` da Company e pelo CPF do admin.

    Retorna (error, was_updated).
    """
    from core.models import Company, User, ExtraData

    base_required = ['name', 'document', 'admin_cpf', 'admin_email', 'admin_first_name']
    required = base_required if update_existing else base_required + ['admin_password']
    for f in required:
        if not row.get(f):
            return f"Campo obrigatório ausente: '{f}'", False

    person_type = (row.get('person_type') or Company.PERSON_TYPE_PJ).strip()
    document = normalize_document(row['document'], person_type=person_type)
    admin_cpf = normalize_cpf(row['admin_cpf'])

    # Aceita admin_pix_* (corban) ou pix_* (planilha genérica).
    pix_key, pix_type = resolve_pix_fields(
        row.get('admin_pix_key') or row.get('pix_key'),
        row.get('admin_pix_type') or row.get('pix_type'),
    )

    company_defaults = {
        'name': row['name'],
        'trading_name': row.get('trading_name') or '',
        'person_type': person_type,
        'primary_color': row.get('primary_color') or '#3498db',
        'secondary_color': row.get('secondary_color') or '#2c3e50',
        'accent_color': row.get('accent_color') or '#e74c3c',
    }

    existing_company = Company.objects.filter(document=document).first() if update_existing else None

    # Perfil admin deste corban (independente de vendedor com mesmo CPF)
    existing_admin = (
        User.objects.filter(company=existing_company, role=User.EMPRESA_ADMIN).first()
        if existing_company else None
    )

    # Proteção: usuários internos da promotora (por login_document / CPF)
    promotora_user = User.objects.filter(
        login_document=admin_cpf,
        role__in=(User.ADMIN, User.COLABORADOR),
    ).first()
    if promotora_user:
        return (
            f"CPF {admin_cpf} pertence a um usuário interno da promotora "
            f"({promotora_user.get_role_display()}); operação ignorada para preservar o cadastro.",
            False,
        )

    if existing_company and existing_company.is_promotora:
        return (
            f"Documento {document} pertence à própria promotora; "
            f"operação ignorada para preservar o cadastro.",
            False,
        )

    is_update = bool(existing_company or existing_admin)

    with transaction.atomic():
        if existing_company:
            for k, v in company_defaults.items():
                setattr(existing_company, k, v)
            existing_company.save()
            company = existing_company
        else:
            company = Company.objects.create(document=document, **company_defaults)

        if existing_admin:
            existing_admin.email = row['admin_email']
            existing_admin.first_name = row['admin_first_name']
            existing_admin.last_name = row.get('admin_last_name') or ''
            existing_admin.role = User.EMPRESA_ADMIN
            existing_admin.company = company
            existing_admin.login_document = admin_cpf
            admin_matricula = row.get('admin_matricula') or row.get('matricula')
            if admin_matricula:
                existing_admin.matricula = ensure_unique_matricula(
                    existing_admin, company, str(admin_matricula).strip(),
                )
            if row.get('admin_password'):
                existing_admin.set_password(row['admin_password'])
            existing_admin.save()
            user = existing_admin
        else:
            admin_matricula = row.get('admin_matricula') or row.get('matricula')
            user = User.objects.create_user(
                cpf=admin_cpf,
                login_document=admin_cpf,
                password=row['admin_password'],
                email=row['admin_email'],
                first_name=row['admin_first_name'],
                last_name=row.get('admin_last_name') or '',
                role=User.EMPRESA_ADMIN,
                company=company,
            )
            if admin_matricula:
                user.matricula = ensure_unique_matricula(
                    user, company, str(admin_matricula).strip(),
                )
                user.save(update_fields=['matricula'])

        if pix_key or pix_type:
            ExtraData.objects.update_or_create(
                user=user,
                defaults={'pix_key': pix_key, 'pix_type': pix_type},
            )

    return None, is_update


def _create_bank_row(row: dict) -> tuple[str | None, bool]:
    """
    Cria ou atualiza um Bank a partir de uma linha do CSV.
    Usa `name` como chave de upsert. Retorna (error, was_updated).
    """
    from bank.models import Bank

    if not row.get('name'):
        return "Campo obrigatório ausente: 'name'", False

    is_active_raw = row.get('is_active', 'true')
    is_active = str(is_active_raw).strip().lower() not in ('false', '0', 'no', 'nao', 'não')

    website = row.get('website') or None

    with transaction.atomic():
        _, created = Bank.objects.update_or_create(
            name=row['name'].strip(),
            defaults={
                'code': row.get('code') or None,
                'website': website,
                'is_active': is_active,
            },
        )

    return None, not created


def _create_bank_access_row(row: dict, created_by) -> tuple[str | None, bool]:
    """
    Cria um BankAccess vinculando ao usuário pelo CPF.
    Com perfil duplo, use is_master=true para perfil Corban ou false para vendedor.
    """
    from django.db.models import Q
    from core.models import User
    from bank.models import Bank
    from bank_access.models import BankAccess
    from bank_access.validators import validate_bank_access_instance

    required = ['cpf', 'bank_name', 'username', 'password']
    for f in required:
        if not row.get(f):
            return f"Campo obrigatório ausente: '{f}'", False

    cpf_clean = normalize_cpf(row['cpf'])
    is_master = str(row.get('is_master', '')).strip().lower() in (
        'true', '1', 'yes', 'sim', 'on',
    )

    users_qs = User.objects.filter(Q(cpf=cpf_clean) | Q(login_document=cpf_clean))
    if is_master:
        user = users_qs.filter(role=User.EMPRESA_ADMIN).first()
        if not user:
            return f"Perfil Corban (master) não encontrado para CPF {cpf_clean}", False
    else:
        user = users_qs.filter(role__in=(User.VENDEDOR, User.LIDER, User.GERENTE)).first()
        if not user:
            user = users_qs.exclude(role__in=(User.EMPRESA_ADMIN, User.ADMIN, User.COLABORADOR)).first()
        if not user:
            return f"Usuário de equipe não encontrado para CPF {cpf_clean}", False

    try:
        bank = Bank.objects.get(name__iexact=row['bank_name'].strip())
    except Bank.DoesNotExist:
        return f"Banco '{row['bank_name']}' não encontrado", False
    except Bank.MultipleObjectsReturned:
        return f"Múltiplos bancos encontrados com o nome '{row['bank_name']}'", False

    is_active_raw = row.get('is_active', 'true')
    is_active = str(is_active_raw).strip().lower() not in ('false', '0', 'no', 'nao', 'não')

    access = BankAccess(
        bank=bank,
        username=row['username'].strip(),
        password=row['password'],
        is_active=is_active,
        is_master=is_master,
        notes=(row.get('notes') or '').strip() or None,
        link=(row.get('link') or '').strip() or None,
        user=user,
        created_by=created_by,
    )

    try:
        validate_bank_access_instance(access)
    except Exception as exc:
        return str(exc), False

    with transaction.atomic():
        obj, created = BankAccess.objects.update_or_create(
            bank=bank,
            username=row['username'].strip(),
            defaults={
                'password': row['password'],
                'is_active': is_active,
                'is_master': is_master,
                'notes': access.notes,
                'link': access.link,
                'user': user,
                'created_by': created_by,
            },
        )

    return None, not created


# ─────────────────────────────────────────────────────────────────────────────
# Task principal
# ─────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True)
def process_import_job(self, job_id: str):
    """
    Processa um ImportJob: lê arquivo, cria entidades linha a linha,
    atualiza progresso a cada linha e via WebSocket.
    """
    from core.models import ImportJob, User

    try:
        job = ImportJob.objects.get(id=job_id)
    except ImportJob.DoesNotExist:
        logger.error('ImportJob %s não encontrado', job_id)
        return

    job.status = ImportJob.STATUS_PROCESSING
    job.save(update_fields=['status'])
    _push_progress(job_id, job)

    try:
        rows = _read_file(job.file_path)
    except Exception as exc:
        job.status = ImportJob.STATUS_FAILED
        job.errors = [{'linha': 0, 'dado': '', 'erro': f'Erro ao ler arquivo: {exc}'}]
        try:
            from core.import_error_report import save_import_error_report
            job.error_file_path = save_import_error_report(job)
        except Exception:
            logger.exception('Falha ao gerar Excel de erros (leitura) do ImportJob %s', job_id)
        job.save(update_fields=['status', 'errors', 'error_file_path'])
        _push_progress(job_id, job)
        return

    job.total_rows = len(rows)
    # Reseta contadores e força save inicial (com total_rows e zeros) para o
    # frontend conseguir mostrar 0/N e a barra em 0% imediatamente, sem ter
    # que esperar a primeira linha terminar.
    job.processed_rows = 0
    job.created_count = 0
    job.updated_count = 0
    job.error_count = 0
    job.errors = []
    job.save(update_fields=['total_rows', 'processed_rows', 'created_count', 'updated_count', 'error_count', 'errors'])
    _push_progress(job_id, job)

    requesting_company_id = str(job.created_by.company_id) if job.created_by and job.created_by.company_id else None
    update_existing = job.update_existing
    promotora_import = bool(
        job.created_by and getattr(job.created_by, 'is_promotora_user', False)
    )

    # Estratégia adaptativa: persiste a cada linha em arquivos pequenos
    # (responsividade) e a cada 5 linhas em grandes (menos I/O no banco).
    # Antes era fixo em 5, fazendo arquivos curtos (ex.: 3 corbans) só
    # atualizarem o status no fim — parecia travado.
    push_every = 1 if len(rows) <= 30 else 5

    for idx, row in enumerate(rows, start=1):
        error_msg = None
        was_updated = False
        try:
            if job.entity_type == ImportJob.ENTITY_CORBAN:
                error_msg, was_updated = _create_corban_row(row, update_existing=update_existing)
            elif job.entity_type == ImportJob.ENTITY_BANK_ACCESS:
                error_msg, was_updated = _create_bank_access_row(row, job.created_by)
            elif job.entity_type == ImportJob.ENTITY_BANK:
                error_msg, was_updated = _create_bank_row(row)
            else:
                error_msg, was_updated = _create_user_row(
                    row, job.entity_type, requesting_company_id,
                    update_existing=update_existing,
                    promotora_import=promotora_import,
                )
        except IntegrityError:
            # Quando update_existing está ligado, duplicados deveriam ter sido
            # tratados nos helpers; chegar aqui significa colisão em outra
            # constraint (ex.: email já usado por OUTRO usuário).
            error_msg = (
                'Registro duplicado em outro campo (provavelmente email/usuário já em uso)'
                if update_existing
                else 'Registro duplicado (CPF/email/documento já existe). '
                     'Marque "Atualizar cadastros existentes" para sobrescrever.'
            )
        except Exception as exc:
            error_msg = f'Erro inesperado: {exc}'

        job.processed_rows = idx
        if error_msg:
            job.error_count += 1
            job.errors = job.errors + [{'linha': idx, 'dado': row.get('cpf') or row.get('document') or str(idx), 'erro': error_msg}]
        elif was_updated:
            job.updated_count += 1
        else:
            job.created_count += 1

        if idx % push_every == 0 or idx == len(rows):
            job.save(update_fields=['processed_rows', 'created_count', 'updated_count', 'error_count', 'errors'])
            _push_progress(job_id, job)

    job.status = ImportJob.STATUS_DONE
    update_fields = ['status']
    if job.error_count > 0:
        try:
            from core.import_error_report import save_import_error_report
            job.error_file_path = save_import_error_report(job, rows)
            update_fields.append('error_file_path')
        except Exception as exc:
            logger.exception('Falha ao gerar Excel de erros do ImportJob %s: %s', job_id, exc)
    job.save(update_fields=update_fields)
    _push_progress(job_id, job)

    logger.info(
        'ImportJob %s concluído: %d criados, %d atualizados, %d erros (total %d)',
        job_id, job.created_count, job.updated_count, job.error_count, job.total_rows,
    )
