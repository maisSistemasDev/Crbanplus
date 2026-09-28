"""Executores de nós do fluxo ETL."""
from __future__ import annotations

from typing import TYPE_CHECKING

from proposal_etl.services.batch_factory import create_proposal_batch_from_rows
from proposal_etl.services.http_helpers import http_options_from_node
from proposal_etl.services.http_client import execute_http_request
from proposal_etl.services.json_utils import (
    SKIP_FIELD_MAPPING,
    get_value_from_item,
    resolve_mapping_value,
)
from proposal_etl.services.item_enricher import fetch_item_details
from proposal_etl.services.pagination import paginate_http_request
from proposal_etl.services.schedule_utils import build_schedule_summary, human_schedule_to_cron

if TYPE_CHECKING:
    from proposal_etl.services.run_context import EtlRunContext


def run_schedule_trigger(data: dict, _input: dict, ctx: EtlRunContext | None = None) -> dict:
    cron = human_schedule_to_cron(data)
    summary = build_schedule_summary(data)
    return {
        'triggered': True,
        'cron': cron,
        'timezone': data.get('timezone'),
        'schedule_mode': data.get('schedule_mode'),
        'schedule_time': data.get('schedule_time'),
        'schedule_summary': summary,
    }


def run_http_request(data: dict, _input: dict, ctx: EtlRunContext | None = None) -> dict:
    auth_type, auth_config = _resolve_auth(data, ctx)
    opts = http_options_from_node(data)
    if ctx:
        ctx.logger.log_http(
            **ctx.node_meta(),
            message='Requisição HTTP',
            url=data.get('url', ''),
            method=data.get('method', 'GET'),
            query_params=data.get('query_params') or {},
            extra={'auth_type': auth_type, 'use_shared_auth': _uses_shared(data, ctx)},
        )
    status_code, body = execute_http_request(
        url=data.get('url', ''),
        method=data.get('method', 'GET'),
        auth_type=auth_type,
        auth_config=auth_config,
        headers=data.get('headers') or {},
        query_params=data.get('query_params') or {},
        body=data.get('body') or {},
        auth_session=ctx.auth_session if ctx else None,
        **opts,
    )
    return {'status_code': status_code, 'body': body}


def run_paginate_http(
    data: dict,
    _input: dict,
    max_pages_override: int | None = None,
    ctx: EtlRunContext | None = None,
) -> dict:
    return paginate_http_request(data, max_pages_override=max_pages_override, ctx=ctx)


def run_fetch_item_details(
    data: dict,
    input_data: dict,
    limit_items: int | None = None,
    ctx: EtlRunContext | None = None,
) -> dict:
    return fetch_item_details(data, input_data, limit_items=limit_items, ctx=ctx)


def run_extract_items(data: dict, input_data: dict, ctx: EtlRunContext | None = None) -> dict:
    items_path = data.get('items_path') or '$.data'
    if input_data.get('items') is not None:
        items = input_data['items']
        if not isinstance(items, list):
            items = [items]
        return {'items': items, 'count': len(items)}

    body = input_data.get('body', input_data)
    items = resolve_json_path(body, items_path)
    if items is None:
        raise ValueError(f'Nenhuma lista encontrada em {items_path}')
    if not isinstance(items, list):
        items = [items]
    return {'items': items, 'count': len(items)}


def run_map_fields(data: dict, input_data: dict, ctx: EtlRunContext | None = None) -> dict:
    items = input_data.get('items') or []
    mappings = data.get('mappings') or []
    rows = []
    for item in items:
        row = {}
        for mapping in mappings:
            source_path = mapping.get('source_path', '')
            layout_field = mapping.get('layout_field', '')
            header_name = mapping.get('header_name') or source_path
            if not layout_field or not source_path:
                continue
            value = resolve_mapping_value(item, mapping)
            if value is SKIP_FIELD_MAPPING:
                continue
            row[header_name] = value
        rows.append(row)
    return {'rows': rows, 'count': len(rows)}


def run_create_batch(data: dict, input_data: dict, etl_run=None, ctx: EtlRunContext | None = None) -> dict:
    layout_id = data.get('layout_id') or ''
    if not layout_id:
        raise ValueError('Layout é obrigatório no nó Criar lote.')
    rows = input_data.get('rows') or []
    if not rows:
        raise ValueError('Nenhuma linha para criar o lote.')
    batch = create_proposal_batch_from_rows(rows, layout_id, etl_run=etl_run)
    return {
        'proposal_batch_id': str(batch.id),
        'total_rows': batch.total_rows,
        'layout_id': str(batch.layout_id),
    }


def _resolve_auth(data: dict, ctx: EtlRunContext | None) -> tuple[str, dict]:
    if ctx:
        return ctx.resolve_auth(data)
    return data.get('auth_type') or 'none', dict(data.get('auth_config') or {})


def _uses_shared(data: dict, ctx: EtlRunContext | None) -> bool:
    if not ctx or not ctx.flow.shared_auth_enabled:
        return False
    use_shared = data.get('use_shared_auth')
    if use_shared is None:
        return True
    return bool(use_shared)


NODE_HANDLERS = {
    'schedule_trigger': run_schedule_trigger,
    'http_request': run_http_request,
    'paginate_http': run_paginate_http,
    'fetch_item_details': run_fetch_item_details,
    'extract_items': run_extract_items,
    'map_fields': run_map_fields,
    'create_batch': run_create_batch,
}
