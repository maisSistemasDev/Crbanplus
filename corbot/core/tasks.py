"""
Tasks Celery para importação em lote de entidades via CSV/XLSX.
"""
import logging
import re

from celery import shared_task
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

    if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path, dtype=str)

    records = df.to_dict(orient='records')

    def _clean(v):
        if v is None:
            return None
        if isinstance(v, float) and math.isnan(v):
            return None
        return str(v).strip() if str(v).strip() not in ('', 'nan', 'NaN', 'None') else None

    return [{k: _clean(v) for k, v in row.items()} for row in records]


# ─────────────────────────────────────────────────────────────────────────────
# Funções de criação por tipo
# ─────────────────────────────────────────────────────────────────────────────

def _create_user_row(row: dict, role: str, requesting_company_id) -> str | None:
    """
    Cria um usuário (vendedor/lider/gerente) a partir de uma linha do CSV.
    Retorna None em caso de sucesso, ou uma string de erro.
    """
    from core.models import User, ExtraData, Company

    required = ['cpf', 'email', 'first_name', 'password']
    for f in required:
        if not row.get(f):
            return f"Campo obrigatório ausente: '{f}'"

    cpf_clean = re.sub(r'\D', '', row['cpf'])

    company = None
    if row.get('company_document'):
        try:
            company = Company.objects.get(document=re.sub(r'\D', '', row['company_document']))
        except Company.DoesNotExist:
            return f"Corban não encontrado: {row['company_document']}"
    elif requesting_company_id:
        try:
            company = Company.objects.get(id=requesting_company_id)
        except Company.DoesNotExist:
            pass

    leader = None
    if row.get('leader_cpf'):
        leader_cpf = re.sub(r'\D', '', row['leader_cpf'])
        try:
            leader = User.objects.get(cpf=leader_cpf, role__in=[User.LIDER, User.GERENTE])
        except User.DoesNotExist:
            return f"Líder com CPF {leader_cpf} não encontrado"

    with transaction.atomic():
        user = User.objects.create_user(
            cpf=cpf_clean,
            email=row['email'],
            first_name=row['first_name'],
            last_name=row.get('last_name') or '',
            role=role,
            company=company,
            leader=leader,
        )
        user.set_password(row['password'])
        user.save()

        # Dados extras (optional)
        extra_fields = ['rg', 'rg_emission_date', 'rg_emission_organ',
                        'birth_date', 'phone', 'pix_key', 'pix_type']
        extra = {k: row[k] for k in extra_fields if row.get(k)}
        if extra:
            ExtraData.objects.create(user=user, **extra)

    return None  # sucesso


def _create_corban_row(row: dict) -> str | None:
    """
    Cria um Company (corban) e seu usuário administrador (empresa_admin).
    """
    from core.models import Company, User

    required = ['name', 'document', 'admin_cpf', 'admin_email', 'admin_first_name', 'admin_password']
    for f in required:
        if not row.get(f):
            return f"Campo obrigatório ausente: '{f}'"

    document = re.sub(r'\D', '', row['document'])
    admin_cpf = re.sub(r'\D', '', row['admin_cpf'])

    with transaction.atomic():
        company = Company.objects.create(
            name=row['name'],
            trading_name=row.get('trading_name') or '',
            person_type=row.get('person_type') or Company.PERSON_TYPE_PJ,
            document=document,
            primary_color=row.get('primary_color') or '#3498db',
            secondary_color=row.get('secondary_color') or '#2c3e50',
            accent_color=row.get('accent_color') or '#e74c3c',
        )

        user = User.objects.create_user(
            cpf=admin_cpf,
            password=row['admin_password'],
            email=row['admin_email'],
            first_name=row['admin_first_name'],
            last_name=row.get('admin_last_name') or '',
            role=User.EMPRESA_ADMIN,
            company=company,
        )

    return None  # sucesso


def _create_bank_row(row: dict) -> str | None:
    """
    Cria ou atualiza um Bank a partir de uma linha do CSV.
    Usa `name` como chave de upsert.
    """
    from bank.models import Bank

    if not row.get('name'):
        return "Campo obrigatório ausente: 'name'"

    is_active_raw = row.get('is_active', 'true')
    is_active = str(is_active_raw).strip().lower() not in ('false', '0', 'no', 'nao', 'não')

    website = row.get('website') or None

    with transaction.atomic():
        Bank.objects.update_or_create(
            name=row['name'].strip(),
            defaults={
                'code': row.get('code') or None,
                'website': website,
                'is_active': is_active,
            },
        )

    return None  # sucesso


def _create_bank_access_row(row: dict, created_by) -> str | None:
    """
    Cria um BankAccess vinculando ao usuário pelo CPF.
    """
    from core.models import User
    from bank.models import Bank
    from bank_access.models import BankAccess

    required = ['cpf', 'bank_name', 'username', 'password']
    for f in required:
        if not row.get(f):
            return f"Campo obrigatório ausente: '{f}'"

    cpf_clean = re.sub(r'\D', '', row['cpf'])
    try:
        user = User.objects.get(cpf=cpf_clean)
    except User.DoesNotExist:
        return f"Usuário com CPF {cpf_clean} não encontrado"

    try:
        bank = Bank.objects.get(name__iexact=row['bank_name'].strip())
    except Bank.DoesNotExist:
        return f"Banco '{row['bank_name']}' não encontrado"
    except Bank.MultipleObjectsReturned:
        return f"Múltiplos bancos encontrados com o nome '{row['bank_name']}'"

    is_active_raw = row.get('is_active', 'true')
    is_active = str(is_active_raw).strip().lower() not in ('false', '0', 'no', 'nao', 'não')

    with transaction.atomic():
        BankAccess.objects.update_or_create(
            bank=bank,
            username=row['username'],
            defaults={
                'password': row['password'],
                'is_active': is_active,
                'user': user,
                'created_by': created_by,
            },
        )

    return None  # sucesso


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
        job.errors = [{'linha': 0, 'erro': f'Erro ao ler arquivo: {exc}'}]
        job.save(update_fields=['status', 'errors'])
        _push_progress(job_id, job)
        return

    job.total_rows = len(rows)
    job.save(update_fields=['total_rows'])

    requesting_company_id = str(job.created_by.company_id) if job.created_by and job.created_by.company_id else None

    PUSH_EVERY = 5  # envia WS a cada N linhas

    for idx, row in enumerate(rows, start=1):
        error_msg = None
        try:
            if job.entity_type == ImportJob.ENTITY_CORBAN:
                error_msg = _create_corban_row(row)
            elif job.entity_type == ImportJob.ENTITY_BANK_ACCESS:
                error_msg = _create_bank_access_row(row, job.created_by)
            elif job.entity_type == ImportJob.ENTITY_BANK:
                error_msg = _create_bank_row(row)
            else:
                error_msg = _create_user_row(row, job.entity_type, requesting_company_id)
        except IntegrityError:
            error_msg = 'Registro duplicado (CPF/email/documento já existe)'
        except Exception as exc:
            error_msg = f'Erro inesperado: {exc}'

        job.processed_rows = idx
        if error_msg:
            job.error_count += 1
            job.errors = job.errors + [{'linha': idx, 'dado': row.get('cpf') or row.get('document') or str(idx), 'erro': error_msg}]
        else:
            job.created_count += 1

        if idx % PUSH_EVERY == 0 or idx == len(rows):
            job.save(update_fields=['processed_rows', 'created_count', 'error_count', 'errors'])
            _push_progress(job_id, job)

    job.status = ImportJob.STATUS_DONE
    job.save(update_fields=['status'])
    _push_progress(job_id, job)

    logger.info(
        'ImportJob %s concluído: %d criados, %d erros (total %d)',
        job_id, job.created_count, job.error_count, job.total_rows,
    )
