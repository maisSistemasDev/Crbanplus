"""Cria ProposalBatch pending a partir de linhas mapeadas."""
import csv
import io
import uuid
from datetime import datetime

from django.core.files.base import ContentFile

from proposals.models import Layout, ProposalBatch, ProposalFile
from proposal_etl.models import ProposalEtlRun


def create_proposal_batch_from_rows(
    rows: list[dict],
    layout_id: str,
    etl_run: ProposalEtlRun | None = None,
) -> ProposalBatch:
    layout = Layout.objects.prefetch_related('map_fields').get(id=layout_id)
    fields = list(layout.map_fields.all().order_by('index'))
    if not fields:
        raise ValueError('Layout sem campos mapeados.')

    buffer = io.StringIO()
    headers = [f.header_name or f.name for f in fields]
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow(headers)

    for row in rows:
        line = []
        for field in fields:
            val = row.get(field.header_name, row.get(field.name, ''))
            if val is None:
                val = ''
            line.append(str(val))
        writer.writerow(line)

    csv_bytes = buffer.getvalue().encode('utf-8-sig')
    filename = f'etl_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}.csv'

    proposal_file = ProposalFile.objects.create(
        file=ContentFile(csv_bytes, name=filename),
    )
    batch = ProposalBatch.objects.create(
        file=proposal_file,
        layout=layout,
        status='pending',
        total_rows=len(rows),
    )
    if etl_run:
        batch.etl_run = etl_run
        batch.save(update_fields=['etl_run'])

    return batch
