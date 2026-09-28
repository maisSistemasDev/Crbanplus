"""Lotes diários de webhook — um lote aberto por banco/dia; novo após processado."""
from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction

from proposals.models import Layout, ProposalBatch, ProposalFile
from webhooks.models import WebhookDailyBatch


OPEN_BATCH_STATUSES = ('pending', 'processing')


def webhook_batch_date() -> date:
    tz_name = getattr(settings, 'WEBHOOK_BATCH_TIMEZONE', 'America/Sao_Paulo')
    from django.utils import timezone
    return timezone.now().astimezone(ZoneInfo(tz_name)).date()


def _layout_fields(layout: Layout):
    return list(layout.map_fields.all().order_by('index'))


def _row_to_csv_line(row: dict, fields) -> list[str]:
    line = []
    for field in fields:
        val = row.get(field.header_name, row.get(field.name, ''))
        if val is None:
            val = ''
        line.append(str(val))
    return line


def create_proposal_batch_from_rows(
    rows: list[dict],
    layout_id: str,
    *,
    bank_id,
    batch_date: date | None = None,
) -> tuple[ProposalBatch, bool]:
    """
    Cria lote do dia para o banco ou acrescenta linhas ao lote aberto do dia.
    Retorna (batch, created) — created=False quando reutilizou lote existente.
    """
    if not rows:
        raise ValueError('Nenhuma linha para o lote.')

    batch_date = batch_date or webhook_batch_date()
    layout = Layout.objects.prefetch_related('map_fields').get(id=layout_id)
    fields = _layout_fields(layout)
    if not fields:
        raise ValueError('Layout sem campos mapeados.')

    with transaction.atomic():
        daily = (
            WebhookDailyBatch.objects.select_for_update()
            .filter(
                bank_id=bank_id,
                batch_date=batch_date,
                proposal_batch__status__in=OPEN_BATCH_STATUSES,
            )
            .select_related('proposal_batch', 'proposal_batch__file', 'proposal_batch__layout')
            .order_by('-created_at')
            .first()
        )

        if daily:
            batch = append_rows_to_proposal_batch(daily.proposal_batch, rows, fields=fields)
            return batch, False

        batch = _create_new_batch(rows, layout, fields)
        WebhookDailyBatch.objects.create(
            bank_id=bank_id,
            batch_date=batch_date,
            proposal_batch=batch,
            layout=layout,
        )
        return batch, True


def _create_new_batch(rows: list[dict], layout: Layout, fields) -> ProposalBatch:
    buffer = io.StringIO()
    headers = [f.header_name or f.name for f in fields]
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow(headers)
    for row in rows:
        writer.writerow(_row_to_csv_line(row, fields))

    csv_bytes = buffer.getvalue().encode('utf-8-sig')
    filename = f'webhook_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}.csv'

    proposal_file = ProposalFile.objects.create(
        file=ContentFile(csv_bytes, name=filename),
    )
    return ProposalBatch.objects.create(
        file=proposal_file,
        layout=layout,
        status='pending',
        total_rows=len(rows),
    )


def append_rows_to_proposal_batch(
    batch: ProposalBatch,
    rows: list[dict],
    *,
    fields=None,
) -> ProposalBatch:
    if not rows:
        return batch

    if fields is None:
        fields = _layout_fields(batch.layout)

    batch.file.file.open('rb')
    raw = batch.file.file.read()
    batch.file.file.close()

    text = raw.decode('utf-8-sig') if raw else ''
    out = io.StringIO()

    if text.strip():
        out.write(text.rstrip('\n'))
        out.write('\n')
    else:
        headers = [f.header_name or f.name for f in fields]
        writer = csv.writer(out, delimiter=';')
        writer.writerow(headers)

    writer = csv.writer(out, delimiter=';', lineterminator='\n')
    for row in rows:
        writer.writerow(_row_to_csv_line(row, fields))

    new_bytes = out.getvalue().encode('utf-8-sig')
    batch.file.file.save(batch.file.file.name, ContentFile(new_bytes), save=True)
    batch.total_rows = (batch.total_rows or 0) + len(rows)
    batch.save(update_fields=['total_rows'])
    return batch
