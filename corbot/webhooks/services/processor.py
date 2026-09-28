"""Processa payloads recebidos via webhook."""
from __future__ import annotations

from typing import Any

from proposal_etl.services.json_utils import resolve_json_path
from proposal_etl.services.node_handlers import run_map_fields
from webhooks.models import WebhookDelivery, WebhookEndpoint
from webhooks.services.batch_pool import create_proposal_batch_from_rows


def extract_items(payload: Any, items_path: str) -> list[dict]:
    if items_path and str(items_path).strip():
        data = resolve_json_path(payload, items_path.strip())
    else:
        data = payload

    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    raise ValueError('Payload não contém objetos para mapear (esperado objeto ou lista).')


def map_items(items: list[dict], mappings: list[dict]) -> list[dict]:
    if not mappings:
        raise ValueError('Nenhum mapeamento configurado no webhook.')
    result = run_map_fields({'mappings': mappings}, {'items': items})
    rows = result.get('rows') or []
    if not rows:
        raise ValueError('Nenhuma linha gerada pelo mapeamento.')
    return rows


def process_webhook_payload(
    endpoint: WebhookEndpoint,
    payload: Any,
    *,
    source_ip: str | None = None,
    create_batch: bool = True,
    auto_process: bool | None = None,
) -> WebhookDelivery:
    delivery = WebhookDelivery.objects.create(
        endpoint=endpoint,
        status=WebhookDelivery.STATUS_RECEIVED,
        raw_payload=payload if isinstance(payload, (dict, list)) else {'value': payload},
        source_ip=source_ip,
    )

    try:
        items = extract_items(payload, endpoint.items_path or '')
        delivery.items_count = len(items)
        rows = map_items(items, endpoint.mappings or [])
        delivery.mapped_rows = rows[:50]
        delivery.status = WebhookDelivery.STATUS_MAPPED
        delivery.save(update_fields=['items_count', 'mapped_rows', 'status'])

        should_create = create_batch and endpoint.layout_id
        if not should_create:
            return delivery

        batch, created = create_proposal_batch_from_rows(
            rows,
            str(endpoint.layout_id),
            bank_id=endpoint.bank_id,
        )
        delivery.proposal_batch = batch
        delivery.batch_created = created
        delivery.status = (
            WebhookDelivery.STATUS_BATCH_CREATED
            if created
            else WebhookDelivery.STATUS_APPENDED
        )
        delivery.save(update_fields=['proposal_batch', 'status', 'batch_created'])

        run_auto = endpoint.auto_process if auto_process is None else auto_process
        if run_auto and created:
            from proposals.tasks import process_proposal_batch_with_pipeline
            process_proposal_batch_with_pipeline.delay(batch.id)

        return delivery
    except Exception as exc:
        delivery.status = WebhookDelivery.STATUS_FAILED
        delivery.error_message = str(exc)
        delivery.save(update_fields=['status', 'error_message'])
        raise


def preview_webhook_mapping(endpoint: WebhookEndpoint, payload: Any) -> dict:
    items = extract_items(payload, endpoint.items_path or '')
    rows = map_items(items, endpoint.mappings or [])
    return {
        'items_count': len(items),
        'rows_count': len(rows),
        'sample_item': items[0] if items else None,
        'sample_row': rows[0] if rows else None,
        'rows_preview': rows[:5],
    }
