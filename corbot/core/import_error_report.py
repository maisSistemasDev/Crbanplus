"""Gera planilha Excel com o log de erros de importação em lote."""
from __future__ import annotations

import io
from typing import TYPE_CHECKING

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

if TYPE_CHECKING:
    from core.models import ImportJob

_HEADER_FILL = PatternFill('solid', fgColor='1F4E79')
_HEADER_FONT = Font(color='FFFFFF', bold=True)
_SUMMARY_LABEL_FONT = Font(bold=True)


def build_import_errors_xlsx(job: ImportJob, source_rows: list[dict] | None = None) -> bytes:
    """Monta workbook com resumo e detalhes dos erros."""
    wb = Workbook()

    ws_summary = wb.active
    ws_summary.title = 'Resumo'
    summary_rows = [
        ('Tipo', job.entity_type),
        ('Status', job.status),
        ('Total de linhas', job.total_rows),
        ('Processadas', job.processed_rows),
        ('Criados', job.created_count),
        ('Atualizados', job.updated_count),
        ('Erros', job.error_count),
        ('Atualizar existentes', 'Sim' if job.update_existing else 'Não'),
        ('Job ID', str(job.id)),
    ]
    for row_idx, (label, value) in enumerate(summary_rows, start=1):
        ws_summary.cell(row=row_idx, column=1, value=label).font = _SUMMARY_LABEL_FONT
        ws_summary.cell(row=row_idx, column=2, value=value)
    ws_summary.column_dimensions['A'].width = 22
    ws_summary.column_dimensions['B'].width = 40

    ws_errors = wb.create_sheet('Erros')
    extra_cols: list[str] = []
    if source_rows:
        keys: set[str] = set()
        for err in job.errors or []:
            line_no = err.get('linha')
            if isinstance(line_no, int) and 1 <= line_no <= len(source_rows):
                keys.update(source_rows[line_no - 1].keys())
        extra_cols = sorted(keys)

    headers = ['Linha', 'Identificador', 'Erro', *extra_cols]
    for col_idx, header in enumerate(headers, start=1):
        cell = ws_errors.cell(row=1, column=col_idx, value=header)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal='center')

    for row_idx, err in enumerate(job.errors or [], start=2):
        line_no = err.get('linha', '')
        ws_errors.cell(row=row_idx, column=1, value=line_no)
        ws_errors.cell(row=row_idx, column=2, value=err.get('dado', ''))
        ws_errors.cell(row=row_idx, column=3, value=err.get('erro', ''))

        if source_rows and isinstance(line_no, int) and 1 <= line_no <= len(source_rows):
            row_data = source_rows[line_no - 1]
            for col_offset, key in enumerate(extra_cols, start=4):
                value = row_data.get(key, '')
                if value is None:
                    value = ''
                ws_errors.cell(row=row_idx, column=col_offset, value=str(value))

    ws_errors.column_dimensions['A'].width = 8
    ws_errors.column_dimensions['B'].width = 18
    ws_errors.column_dimensions['C'].width = 48
    for col_offset, key in enumerate(extra_cols, start=4):
        from openpyxl.utils import get_column_letter
        letter = get_column_letter(col_offset)
        ws_errors.column_dimensions[letter].width = max(12, min(28, len(key) + 4))

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def save_import_error_report(job: ImportJob, source_rows: list[dict] | None = None) -> str:
    """Persiste o Excel de erros e retorna o caminho absoluto no storage."""
    content = build_import_errors_xlsx(job, source_rows)
    rel_path = f'imports/errors/{job.id}.xlsx'
    if default_storage.exists(rel_path):
        default_storage.delete(rel_path)
    saved = default_storage.save(rel_path, ContentFile(content))
    return default_storage.path(saved)
