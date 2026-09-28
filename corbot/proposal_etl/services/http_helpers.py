"""Helpers compartilhados para nós HTTP do ETL."""
from typing import Any
from urllib.parse import parse_qsl, urlparse, urlunparse

from proposal_etl.services.date_utils import resolve_dynamic_dict, resolve_dynamic_string


def http_options_from_node(data: dict) -> dict:
    return {
        'date_format': data.get('date_format') or '%Y-%m-%d',
        'date_timezone': data.get('date_timezone') or 'America/Sao_Paulo',
    }


def int_or_default(value: Any, default: int) -> int:
    if value is None or value == '':
        return default
    return int(value)


def prepare_url_and_query(
    url: str,
    query_params: dict | None,
    *,
    date_format: str,
    date_timezone: str,
) -> tuple[str, dict]:
    """Unifica filtros da URL e query_params; resolve datas dinâmicas (d-7, etc.)."""
    resolved_url = resolve_dynamic_string(
        (url or '').strip(),
        date_format=date_format,
        timezone=date_timezone,
    )
    parsed = urlparse(resolved_url)
    url_query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    merged = {**url_query, **dict(query_params or {})}
    resolved_query = resolve_dynamic_dict(
        merged,
        date_format=date_format,
        timezone=date_timezone,
    )
    return clean_url, resolved_query
