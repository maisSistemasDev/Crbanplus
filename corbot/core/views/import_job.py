"""
Views para importação em lote via CSV/XLSX.
"""
import os
import uuid

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from core.base_views import BaseApiView
from core.models import ImportJob
from core.permissions import IsAdmin, IsPromotoraAdmin


def _allowed_role(user, entity_type: str) -> bool:
    """Verifica se o usuário tem permissão para importar o tipo solicitado."""
    role = getattr(user, 'role', None)
    if role == 'admin':
        return True
    if entity_type == 'corban':
        return role == 'admin'
    if entity_type in ('vendedor', 'lider'):
        return role in ('admin', 'empresa_admin', 'gerente')
    if entity_type == 'gerente':
        return role in ('admin', 'empresa_admin')
    if entity_type == 'bank_access':
        return role in ('admin', 'empresa_admin', 'gerente')
    if entity_type == 'bank':
        return role == 'admin'
    return False


TEMPLATES = {
    'vendedor': [
        'cpf', 'email', 'first_name', 'last_name', 'password',
        'cpf_corban', 'leader_cpf', 'company_document', 'enrollment',
        'pix_key', 'pix_type', 'phone', 'birth_date',
        'rg', 'rg_emission_date', 'rg_emission_organ',
    ],
    'lider': [
        'cpf', 'email', 'first_name', 'last_name', 'password',
        'cpf_corban', 'company_document', 'enrollment',
        'pix_key', 'pix_type', 'phone',
    ],
    'gerente': [
        'cpf', 'email', 'first_name', 'last_name', 'password',
        'cpf_corban', 'company_document', 'enrollment',
    ],
    'corban': [
        'name', 'trading_name', 'document', 'person_type',
        'primary_color', 'secondary_color', 'accent_color',
        'admin_cpf', 'admin_email', 'admin_first_name', 'admin_last_name', 'admin_password',
        'admin_enrollment', 'admin_pix_key', 'admin_pix_type',
    ],
    'bank_access': [
        'cpf', 'bank_name', 'username', 'password', 'is_master',
        'notes', 'link', 'is_active',
    ],
    'bank': [
        'name', 'code', 'website', 'is_active',
    ],
}

REQUIRED_FIELDS = {
    'vendedor': ['cpf', 'email', 'first_name', 'password', 'cpf_corban'],
    'lider': ['cpf', 'email', 'first_name', 'password', 'cpf_corban'],
    'gerente': ['cpf', 'email', 'first_name', 'password', 'cpf_corban'],
    'corban': ['name', 'document', 'admin_cpf', 'admin_email', 'admin_first_name', 'admin_password'],
    'bank_access': ['cpf', 'bank_name', 'username', 'password'],
    'bank': ['name'],
}

EXAMPLE_ROWS = {
    'vendedor': [
        {'cpf': '12345678900', 'email': 'vendedor@empresa.com', 'first_name': 'João',
         'last_name': 'Silva', 'password': 'Senha@123', 'cpf_corban': '98765432100',
         'leader_cpf': '', 'company_document': '', 'enrollment': 'MAT001',
         'pix_key': '12345678900', 'pix_type': 'CPF',
         'phone': '11999999999', 'birth_date': '01/01/1990',
         'rg': '', 'rg_emission_date': '', 'rg_emission_organ': ''},
    ],
    'lider': [
        {'cpf': '98765432100', 'email': 'lider@empresa.com', 'first_name': 'Maria',
         'last_name': 'Souza', 'password': 'Senha@123', 'cpf_corban': '11122233344',
         'company_document': '', 'enrollment': 'MAT002',
         'pix_key': '98765432100', 'pix_type': 'CPF',
         'phone': '11988888888'},
    ],
    'gerente': [
        {'cpf': '11122233300', 'email': 'gerente@empresa.com', 'first_name': 'Carlos',
         'last_name': 'Mendes', 'password': 'Senha@123', 'cpf_corban': '11122233344',
         'company_document': '', 'enrollment': 'MAT003'},
    ],
    'corban': [
        {'name': 'Corban Exemplo LTDA', 'trading_name': 'Corban Exemplo',
         'document': '12345678000195', 'person_type': 'PJ',
         'primary_color': '#3498db', 'secondary_color': '#2c3e50', 'accent_color': '#e74c3c',
         'admin_cpf': '98765432100', 'admin_email': 'admin@corbanexemplo.com',
         'admin_first_name': 'Admin', 'admin_last_name': 'Corban', 'admin_password': 'Senha@123',
         'admin_enrollment': 'ADM001',
         'admin_pix_key': '98765432100', 'admin_pix_type': 'CPF'},
    ],
    'bank_access': [
        {'cpf': '12345678900', 'bank_name': 'Nome do Banco', 'username': 'vendedor@banco.com',
         'password': 'senha_banco', 'is_master': 'false', 'notes': '', 'link': '',
         'is_active': 'true'},
    ],
    'bank': [
        {'name': 'Banco Exemplo', 'code': '001', 'website': 'https://bancoexemplo.com.br', 'is_active': 'true'},
    ],
}


def _serialize_import_job(job: ImportJob) -> dict:
    return {
        'job_id': str(job.id),
        'entity_type': job.entity_type,
        'status': job.status,
        'total_rows': job.total_rows,
        'processed_rows': job.processed_rows,
        'created_count': job.created_count,
        'updated_count': job.updated_count,
        'error_count': job.error_count,
        'progress_pct': job.progress_pct,
        'errors': job.errors,
        'has_error_report': bool(job.error_file_path or job.error_count),
        'created_at': job.created_at,
        'update_existing': job.update_existing,
    }


def _get_import_job_for_user(user, job_id):
    try:
        return ImportJob.objects.get(id=job_id, created_by=user)
    except ImportJob.DoesNotExist:
        if getattr(user, 'role', '') == 'admin':
            return ImportJob.objects.get(id=job_id)
        raise


def _import_jobs_queryset(user):
    qs = ImportJob.objects.all().order_by('-created_at')
    if getattr(user, 'role', '') != 'admin':
        qs = qs.filter(created_by=user)
    return qs


class ImportJobCreateView(BaseApiView):
    """
    POST /core/import/
    Recebe arquivo CSV/XLSX + entity_type, cria ImportJob e despacha task Celery.
    """
    parser_classes = [MultiPartParser]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Lista importações recentes do usuário (persiste após refresh)."""
        qs = _import_jobs_queryset(request.user)
        entity_type = request.GET.get('entity_type', '').strip()
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        limit = min(int(request.GET.get('limit', 15)), 50)
        jobs = qs[:limit]
        return Response([_serialize_import_job(j) for j in jobs])

    def post(self, request):
        entity_type = request.data.get('entity_type', '').strip()
        if entity_type not in ImportJob.ENTITY_CHOICES._value2member_map_ if hasattr(ImportJob.ENTITY_CHOICES, '_value2member_map_') else [c[0] for c in ImportJob.ENTITY_CHOICES]:
            pass  # validated below

        valid_types = [c[0] for c in ImportJob.ENTITY_CHOICES]
        if entity_type not in valid_types:
            return Response(
                {'error': f'entity_type inválido. Use: {", ".join(valid_types)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not _allowed_role(request.user, entity_type):
            return Response({'error': 'Sem permissão para importar este tipo.'}, status=status.HTTP_403_FORBIDDEN)

        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'Arquivo não enviado.'}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ('.csv', '.xlsx', '.xls'):
            return Response({'error': 'Formato não suportado. Use CSV ou XLSX.'}, status=status.HTTP_400_BAD_REQUEST)

        # Salva arquivo
        filename = f'imports/{uuid.uuid4().hex}{ext}'
        path = default_storage.save(filename, ContentFile(file.read()))
        full_path = default_storage.path(path)

        update_existing_raw = request.data.get('update_existing', 'false')
        update_existing = str(update_existing_raw).strip().lower() in (
            'true', '1', 'yes', 'sim', 'on',
        )

        # Cria job
        job = ImportJob.objects.create(
            entity_type=entity_type,
            file_path=full_path,
            created_by=request.user,
            update_existing=update_existing,
        )

        # Despacha task
        from core.tasks import process_import_job
        process_import_job.delay(str(job.id))

        return Response(_serialize_import_job(job), status=status.HTTP_202_ACCEPTED)


class ImportJobStatusView(BaseApiView):
    """
    GET /core/import/{job_id}/
    Retorna o status atual do ImportJob.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        try:
            job = _get_import_job_for_user(request.user, job_id)
        except ImportJob.DoesNotExist:
            return Response({'error': 'Job não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(_serialize_import_job(job))


class ImportJobErrorsExportView(BaseApiView):
    """
    GET /core/import/{job_id}/errors.xlsx/
    Baixa o log de erros da importação em Excel.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        from django.http import HttpResponse
        import os

        from core.import_error_report import build_import_errors_xlsx

        try:
            job = _get_import_job_for_user(request.user, job_id)
        except ImportJob.DoesNotExist:
            return Response({'error': 'Job não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not job.errors:
            return Response({'error': 'Nenhum erro registrado nesta importação.'}, status=status.HTTP_404_NOT_FOUND)

        if job.error_file_path and os.path.isfile(job.error_file_path):
            with open(job.error_file_path, 'rb') as handle:
                content = handle.read()
        else:
            content = build_import_errors_xlsx(job)

        filename = f'import_erros_{job.entity_type}_{job.id}.xlsx'
        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class ImportTemplateView(BaseApiView):
    """
    GET /core/import/template/{entity_type}/
    Retorna CSV de exemplo para download.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, entity_type):
        valid_types = [c[0] for c in ImportJob.ENTITY_CHOICES]
        if entity_type not in valid_types:
            return Response({'error': 'entity_type inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        import csv
        import io
        from django.http import HttpResponse

        columns = TEMPLATES[entity_type]
        example_rows = EXAMPLE_ROWS[entity_type]
        required = REQUIRED_FIELDS[entity_type]

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=columns)
        writer.writeheader()
        for row in example_rows:
            writer.writerow({c: row.get(c, '') for c in columns})

        response = HttpResponse(buf.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="template_{entity_type}.csv"'
        # Campos obrigatórios como header extra informativo
        response['X-Required-Fields'] = ','.join(required)
        return response
