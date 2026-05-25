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
        'leader_cpf', 'company_document',
        'pix_key', 'pix_type', 'phone', 'birth_date',
        'rg', 'rg_emission_date', 'rg_emission_organ',
    ],
    'lider': [
        'cpf', 'email', 'first_name', 'last_name', 'password',
        'company_document',
        'pix_key', 'pix_type', 'phone',
    ],
    'gerente': [
        'cpf', 'email', 'first_name', 'last_name', 'password',
        'company_document',
    ],
    'corban': [
        'name', 'trading_name', 'document', 'person_type',
        'primary_color', 'secondary_color', 'accent_color',
        'admin_cpf', 'admin_email', 'admin_first_name', 'admin_last_name', 'admin_password',
    ],
    'bank_access': [
        'cpf', 'bank_name', 'username', 'password', 'is_active',
    ],
    'bank': [
        'name', 'code', 'website', 'is_active',
    ],
}

REQUIRED_FIELDS = {
    'vendedor': ['cpf', 'email', 'first_name', 'password'],
    'lider': ['cpf', 'email', 'first_name', 'password'],
    'gerente': ['cpf', 'email', 'first_name', 'password'],
    'corban': ['name', 'document', 'admin_cpf', 'admin_email', 'admin_first_name', 'admin_password'],
    'bank_access': ['cpf', 'bank_name', 'username', 'password'],
    'bank': ['name'],
}

EXAMPLE_ROWS = {
    'vendedor': [
        {'cpf': '12345678900', 'email': 'vendedor@empresa.com', 'first_name': 'João',
         'last_name': 'Silva', 'password': 'Senha@123', 'leader_cpf': '',
         'company_document': '', 'pix_key': '12345678900', 'pix_type': 'cpf',
         'phone': '11999999999', 'birth_date': '01/01/1990',
         'rg': '', 'rg_emission_date': '', 'rg_emission_organ': ''},
    ],
    'lider': [
        {'cpf': '98765432100', 'email': 'lider@empresa.com', 'first_name': 'Maria',
         'last_name': 'Souza', 'password': 'Senha@123', 'company_document': '',
         'pix_key': '98765432100', 'pix_type': 'cpf', 'phone': '11988888888'},
    ],
    'gerente': [
        {'cpf': '11122233300', 'email': 'gerente@empresa.com', 'first_name': 'Carlos',
         'last_name': 'Mendes', 'password': 'Senha@123', 'company_document': ''},
    ],
    'corban': [
        {'name': 'Corban Exemplo LTDA', 'trading_name': 'Corban Exemplo',
         'document': '12345678000195', 'person_type': 'PJ',
         'primary_color': '#3498db', 'secondary_color': '#2c3e50', 'accent_color': '#e74c3c',
         'admin_cpf': '98765432100', 'admin_email': 'admin@corbanexemplo.com',
         'admin_first_name': 'Admin', 'admin_last_name': 'Corban', 'admin_password': 'Senha@123'},
    ],
    'bank_access': [
        {'cpf': '12345678900', 'bank_name': 'Nome do Banco', 'username': 'usuario_banco',
         'password': 'senha_banco', 'is_active': 'true'},
    ],
    'bank': [
        {'name': 'Banco Exemplo', 'code': '001', 'website': 'https://bancoexemplo.com.br', 'is_active': 'true'},
    ],
}


class ImportJobCreateView(BaseApiView):
    """
    POST /core/import/
    Recebe arquivo CSV/XLSX + entity_type, cria ImportJob e despacha task Celery.
    """
    parser_classes = [MultiPartParser]
    permission_classes = [permissions.IsAuthenticated]

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

        # Cria job
        job = ImportJob.objects.create(
            entity_type=entity_type,
            file_path=full_path,
            created_by=request.user,
        )

        # Despacha task
        from core.tasks import process_import_job
        process_import_job.delay(str(job.id))

        return Response({
            'job_id': str(job.id),
            'entity_type': job.entity_type,
            'status': job.status,
            'total_rows': job.total_rows,
            'processed_rows': job.processed_rows,
            'created_count': job.created_count,
            'error_count': job.error_count,
            'progress_pct': job.progress_pct,
            'errors': job.errors,
            'created_at': job.created_at,
        }, status=status.HTTP_202_ACCEPTED)


class ImportJobStatusView(BaseApiView):
    """
    GET /core/import/{job_id}/
    Retorna o status atual do ImportJob.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        try:
            job = ImportJob.objects.get(id=job_id, created_by=request.user)
        except ImportJob.DoesNotExist:
            # admins podem ver qualquer job
            if getattr(request.user, 'role', '') != 'admin':
                return Response({'error': 'Job não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
            try:
                job = ImportJob.objects.get(id=job_id)
            except ImportJob.DoesNotExist:
                return Response({'error': 'Job não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'job_id': str(job.id),
            'entity_type': job.entity_type,
            'status': job.status,
            'total_rows': job.total_rows,
            'processed_rows': job.processed_rows,
            'created_count': job.created_count,
            'error_count': job.error_count,
            'progress_pct': job.progress_pct,
            'errors': job.errors,
            'created_at': job.created_at,
        })


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
