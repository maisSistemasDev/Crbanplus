"""Cliente HTTP compartilhado pelo ETL."""
import requests

from proposal_etl.services.auth_handler import AuthHandler, AuthSession, REQUEST_TIMEOUT
from proposal_etl.services.date_utils import resolve_dynamic_dict, resolve_dynamic_string


def execute_http_request(
    *,
    url: str,
    method: str = 'GET',
    auth_type: str | None = 'none',
    auth_config: dict | None = None,
    headers: dict | None = None,
    query_params: dict | None = None,
    body: dict | None = None,
    date_format: str | None = None,
    date_timezone: str | None = None,
    auth_session: AuthSession | None = None,
) -> tuple[int, dict]:
    fmt = date_format or '%Y-%m-%d'
    tz = date_timezone or 'America/Sao_Paulo'

    url = resolve_dynamic_string((url or '').strip(), date_format=fmt, timezone=tz)
    if not url:
        raise ValueError('URL é obrigatória.')

    method = (method or 'GET').upper()
    if auth_session:
        headers = auth_session.apply(auth_type or 'none', auth_config, headers)
    else:
        headers = AuthHandler(auth_type, auth_config or {}).apply(headers or {})
    query_params = resolve_dynamic_dict(query_params, date_format=fmt, timezone=tz)
    body = resolve_dynamic_dict(body, date_format=fmt, timezone=tz)

    if method == 'GET':
        resp = requests.get(url, headers=headers, params=query_params, timeout=REQUEST_TIMEOUT)
    elif method == 'POST':
        resp = requests.post(
            url,
            headers=headers,
            json=body or {},
            params=query_params,
            timeout=REQUEST_TIMEOUT,
        )
    else:
        raise ValueError(f'Método HTTP não suportado: {method}')

    resp.raise_for_status()
    try:
        payload = resp.json()
    except ValueError:
        payload = {'raw_text': resp.text[:5000]}
    return resp.status_code, payload
