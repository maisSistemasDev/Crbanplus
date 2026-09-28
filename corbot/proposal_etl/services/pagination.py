"""Paginação automática de APIs HTTP para o ETL."""
import copy
from typing import Any

from proposal_etl.services.http_client import execute_http_request
from proposal_etl.services.http_helpers import int_or_default, prepare_url_and_query
from proposal_etl.services.json_utils import resolve_json_path


def _is_truthy(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in ('', 'false', '0', 'null', 'none')
    if isinstance(value, list):
        return len(value) > 0
    return True


def _extract_page_items(body: dict, items_path: str) -> list:
    items = resolve_json_path(body, items_path)
    if items is None:
        return []
    if not isinstance(items, list):
        return [items]
    return items


def _resolve_last_path(body: dict, last_path: str | None) -> str | None:
    """Detecta paginação estilo Spring (campo ``last`` na raiz)."""
    if last_path:
        return last_path
    if isinstance(body, dict) and 'last' in body:
        return '$.last'
    return None


def _should_stop_after_page(
    body: dict,
    page_items: list,
    *,
    page_size: int,
    mode: str,
    last_path: str | None,
    has_more_path: str | None,
    stop_when_partial: bool,
) -> bool:
    if not page_items:
        return True

    effective_last_path = _resolve_last_path(body, last_path)
    if effective_last_path:
        is_last = resolve_json_path(body, effective_last_path)
        return _is_truthy(is_last)

    if has_more_path is not None:
        has_more = resolve_json_path(body, has_more_path)
        return not _is_truthy(has_more)

    if stop_when_partial and mode in ('page', 'offset'):
        resp_size = resolve_json_path(body, '$.size')
        try:
            expected = int(resp_size) if resp_size is not None else page_size
        except (TypeError, ValueError):
            expected = page_size
        expected = max(1, expected)
        if len(page_items) < expected:
            return True

    return False


def paginate_http_request(
    data: dict,
    *,
    max_pages_override: int | None = None,
    ctx=None,
) -> dict[str, Any]:
    """
    Executa requisições paginadas e agrega todos os itens.

    Modos (pagination_mode):
      - page: parâmetro numérico de página (page=1, 2, 3...)
      - offset: offset/limit
      - cursor: cursor da resposta anterior no query/body
      - next_url: URL absoluta da próxima página em $.path
    """
    base_url = (data.get('url') or '').strip()
    if not base_url:
        raise ValueError('URL é obrigatória no nó Paginar API.')

    http_opts = {
        'date_format': data.get('date_format') or '%Y-%m-%d',
        'date_timezone': data.get('date_timezone') or 'America/Sao_Paulo',
    }
    current_url, base_query = prepare_url_and_query(
        base_url,
        data.get('query_params') or {},
        date_format=http_opts['date_format'],
        date_timezone=http_opts['date_timezone'],
    )

    mode = (data.get('pagination_mode') or 'page').strip().lower()
    items_path = data.get('items_path') or '$.data'
    has_more_path = (data.get('has_more_path') or '').strip() or None
    last_path = (data.get('last_path') or '').strip() or None
    max_pages = int(max_pages_override or data.get('max_pages') or 100)
    max_pages = max(1, min(max_pages, 500))
    page_size = int(data.get('page_size') or 100)
    page_size = max(1, page_size)
    stop_when_partial = bool(data.get('stop_when_partial', False))
    param_location = (data.get('param_location') or 'query').strip().lower()

    method = (data.get('method') or 'GET').upper()
    if ctx:
        auth_type, auth_config = ctx.resolve_auth(data)
    else:
        auth_type = data.get('auth_type')
        auth_config = data.get('auth_config') or {}
    auth_session = ctx.auth_session if ctx else None
    base_headers = data.get('headers') or {}
    base_body = dict(data.get('body') or {})
    if param_location == 'body':
        base_body = {**base_query, **base_body}
        base_query = {}

    all_items: list = []
    pages_fetched = 0
    last_body: dict = {}
    last_status = 0

    page_number = int_or_default(data.get('page_start'), 0)
    offset = int_or_default(data.get('offset_start'), 0)
    cursor: str | None = None

    while pages_fetched < max_pages:
        query_params = copy.deepcopy(base_query)
        body = copy.deepcopy(base_body)

        if mode == 'page':
            page_param = data.get('page_param') or 'page'
            _set_param(param_location, query_params, body, page_param, page_number)
            if data.get('page_size_param'):
                _set_param(
                    param_location,
                    query_params,
                    body,
                    data['page_size_param'],
                    page_size,
                )
        elif mode == 'offset':
            offset_param = data.get('offset_param') or 'offset'
            limit_param = data.get('limit_param') or 'limit'
            _set_param(param_location, query_params, body, offset_param, offset)
            _set_param(param_location, query_params, body, limit_param, page_size)
        elif mode == 'cursor':
            cursor_param = data.get('cursor_param') or 'cursor'
            if cursor is not None:
                _set_param(param_location, query_params, body, cursor_param, cursor)
        elif mode == 'next_url':
            if pages_fetched > 0 and not current_url:
                break
        else:
            raise ValueError(f'Modo de paginação desconhecido: {mode}')

        if ctx and pages_fetched == 0:
            meta = ctx.node_meta()
            ctx.logger.log_http(
                **meta,
                message='Paginação — requisição inicial',
                url=current_url,
                method=method,
                query_params=query_params,
                extra={
                    'pagination_mode': mode,
                    'auth_type': auth_type,
                    'page': page_number,
                    'resolved_filters': {
                        k: v for k, v in query_params.items()
                        if k not in (data.get('page_param') or 'page', data.get('page_size_param') or 'size')
                    },
                },
            )

        last_status, last_body = execute_http_request(
            url=current_url,
            method=method,
            auth_type=auth_type,
            auth_config=auth_config,
            headers=base_headers,
            query_params=query_params,
            body=body if method == 'POST' else None,
            auth_session=auth_session,
            **http_opts,
        )

        page_items = _extract_page_items(last_body, items_path)
        pages_fetched += 1

        if page_items:
            all_items.extend(page_items)

        if _should_stop_after_page(
            last_body,
            page_items,
            page_size=page_size,
            mode=mode,
            last_path=last_path,
            has_more_path=has_more_path,
            stop_when_partial=stop_when_partial,
        ):
            break

        if mode == 'page':
            page_number += 1
        elif mode == 'offset':
            offset += page_size
        elif mode == 'cursor':
            cursor_path = data.get('cursor_path') or '$.meta.next_cursor'
            next_cursor = resolve_json_path(last_body, cursor_path)
            if not next_cursor or not str(next_cursor).strip():
                break
            cursor = str(next_cursor)
        elif mode == 'next_url':
            next_url_path = data.get('next_url_path') or '$.links.next'
            next_url = resolve_json_path(last_body, next_url_path)
            if not next_url or not str(next_url).strip():
                break
            current_url = str(next_url).strip()

    result: dict[str, Any] = {
        'body': last_body,
        'status_code': last_status,
        'items': all_items,
        'count': len(all_items),
        'pages_fetched': pages_fetched,
        'pagination_mode': mode,
    }
    if isinstance(last_body, dict):
        for key in ('total_elements', 'total_pages', 'number', 'size', 'last'):
            if key in last_body:
                result[f'api_{key}'] = last_body[key]
    return result


def _set_param(location: str, query: dict, body: dict, name: str, value: Any) -> None:
    if location == 'body':
        body[name] = value
    else:
        query[name] = value
