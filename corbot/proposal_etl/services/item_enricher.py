"""Busca detalhes de cada item via HTTP (enriquecimento)."""
import re
import time
from typing import Any

from proposal_etl.services.http_client import execute_http_request
from proposal_etl.services.json_utils import get_value_from_item, resolve_json_path

_PLACEHOLDER_RE = re.compile(r'\{(\w+(?:\.\w+)*)\}')


def _resolve_extraction_path(source: Any, body: Any, path: str) -> Any:
    path = (path or '').strip()
    if not path:
        return None
    if path.startswith('$.'):
        return resolve_json_path(body, path)
    return resolve_json_path(source, path)


def _apply_variable_extractions(
    item: dict,
    *,
    detail: Any,
    body: Any,
    extractions: list | None,
) -> dict:
    if not extractions:
        return item
    out = dict(item)
    for ext in extractions:
        if not isinstance(ext, dict):
            continue
        name = (ext.get('name') or ext.get('var') or '').strip()
        path = (ext.get('path') or '').strip()
        if not name or not path:
            continue
        out[name] = _resolve_extraction_path(detail, body, path)
    return out


def build_url_from_template(template: str, item: dict) -> str:
    def repl(match: re.Match) -> str:
        path = match.group(1)
        value = get_value_from_item(item, path)
        if value is None or value == '':
            raise ValueError(f'Campo "{path}" não encontrado no item para montar a URL.')
        return str(value)

    return _PLACEHOLDER_RE.sub(repl, template.strip())


def fetch_item_details(
    data: dict,
    input_data: dict,
    *,
    limit_items: int | None = None,
    ctx=None,
) -> dict[str, Any]:
    items = input_data.get('items') or []
    if not items:
        raise ValueError('Nenhum item recebido para buscar detalhes.')

    url_template = (data.get('url_template') or '').strip()
    if not url_template:
        raise ValueError('URL template é obrigatória (ex: https://api.../propostas/{id}).')

    method = (data.get('method') or 'GET').upper()
    id_field = (data.get('id_field') or 'id').strip()
    detail_path = (data.get('detail_path') or '').strip() or None
    merge_mode = (data.get('merge_mode') or 'merge').strip().lower()
    delay_ms = max(0, int(data.get('delay_ms') or 0))
    if ctx:
        auth_type, _ = ctx.resolve_auth(data)
        meta = ctx.node_meta()
        ctx.logger.log_http(
            **meta,
            message='Detalhar itens — início',
            url=url_template,
            method=method,
            extra={
                'items_count': len(items),
                'limit': limit_items,
                'auth_type': auth_type,
            },
        )
    if ctx:
        auth_type, auth_config = ctx.resolve_auth(data)
        auth_session = ctx.auth_session
    else:
        auth_type = data.get('auth_type')
        auth_config = data.get('auth_config') or {}
        auth_session = None
    errors: list[str] = []

    enriched: list[dict] = []
    to_process = items[:limit_items] if limit_items else items
    rest = items[len(to_process):] if limit_items else []

    for idx, item in enumerate(to_process):
        if not isinstance(item, dict):
            enriched.append({'value': item})
            continue

        try:
            url = build_url_from_template(url_template, item)
        except ValueError as exc:
            errors.append(str(exc))
            enriched.append(dict(item))
            continue

        if delay_ms and idx > 0:
            time.sleep(delay_ms / 1000.0)

        try:
            status_code, body = execute_http_request(
                url=url,
                method=method,
                auth_type=auth_type,
                auth_config=auth_config,
                headers=data.get('headers') or {},
                query_params=data.get('query_params') or {},
                body=data.get('body') or {},
                date_format=data.get('date_format') or '%Y-%m-%d',
                date_timezone=data.get('date_timezone') or 'America/Sao_Paulo',
                auth_session=auth_session,
            )
            detail: Any = resolve_json_path(body, detail_path) if detail_path else body
            extractions = data.get('variable_extractions') or []
            if merge_mode == 'extract':
                merged = _apply_variable_extractions(
                    item,
                    detail=detail,
                    body=body,
                    extractions=extractions,
                )
                merged['_detail_status'] = status_code
            elif merge_mode == 'nest':
                nest_key = (data.get('merge_key') or 'detail').strip() or 'detail'
                merged = {**item, nest_key: detail, f'_{nest_key}_status': status_code}
            elif merge_mode == 'prefix':
                prefix = (data.get('merge_prefix') or '').strip()
                if prefix and not prefix.endswith('_'):
                    prefix = f'{prefix}_'
                if isinstance(detail, dict):
                    prefixed = {f'{prefix}{k}': v for k, v in detail.items()}
                    merged = {**item, **prefixed, '_detail_status': status_code}
                else:
                    merged = {**item, f'{prefix}detail': detail, '_detail_status': status_code}
            elif isinstance(detail, dict):
                merged = {**item, **detail}
            else:
                merged = {**item, 'detail': detail, '_detail_status': status_code}
            if merge_mode != 'extract' and extractions:
                merged = _apply_variable_extractions(
                    merged,
                    detail=detail,
                    body=body,
                    extractions=extractions,
                )
            enriched.append(merged)
        except Exception as exc:
            errors.append(f'Item {idx}: {exc}')
            enriched.append({**item, '_detail_error': str(exc)})

    if rest:
        enriched.extend(rest)

    result: dict[str, Any] = {
        'items': enriched,
        'count': len(enriched),
        'details_fetched': len(to_process),
    }
    if errors:
        result['errors'] = errors[:10]
        result['error_count'] = len(errors)
    return result
