"""Log estruturado de execução ETL (console)."""
from __future__ import annotations

import copy
from datetime import datetime
from typing import Any

from django.utils import timezone

SENSITIVE_KEYS = frozenset({
    'password',
    'client_secret',
    'api_key',
    'token',
    'authorization',
    'secret',
})


def _sanitize_value(key: str, value: Any) -> Any:
    key_lower = key.lower()
    if any(s in key_lower for s in SENSITIVE_KEYS):
        return '***' if value else ''
    if isinstance(value, dict):
        return sanitize_params(value)
    if isinstance(value, list) and len(value) > 20:
        return {'_truncated': True, 'count': len(value), 'preview': value[:5]}
    return value


def sanitize_params(params: dict | None) -> dict:
    if not params:
        return {}
    out: dict[str, Any] = {}
    for key, value in params.items():
        out[key] = _sanitize_value(key, value)
    return out


def summarize_result(node_type: str, result: dict | None) -> dict:
    if not result:
        return {}
    summary: dict[str, Any] = {}
    for key in (
        'status_code',
        'count',
        'pages_fetched',
        'details_fetched',
        'pagination_mode',
        'triggered',
        'cron',
        'timezone',
        'schedule_summary',
        'total_rows',
        'proposal_batch_id',
        'error_count',
        '_items_capped',
        '_items_original_count',
        '_items_max',
        'api_total_elements',
        'api_total_pages',
        'api_number',
        'api_last',
    ):
        if key in result and result[key] is not None:
            summary[key] = result[key]
    if node_type in ('http_request', 'paginate_http') and isinstance(result.get('body'), dict):
        body = result['body']
        summary['body_keys'] = list(body.keys())[:12]
    if isinstance(result.get('errors'), list) and result['errors']:
        summary['errors_preview'] = result['errors'][:3]
    return summary


class ExecutionLogger:
    def __init__(self, run=None):
        self.run = run
        self.entries: list[dict[str, Any]] = []

    def log(
        self,
        *,
        level: str = 'info',
        node_id: str = '',
        node_type: str = '',
        node_label: str = '',
        message: str,
        params: dict | None = None,
        result: dict | None = None,
    ) -> None:
        entry = {
            'timestamp': timezone.now().isoformat(),
            'level': level,
            'node_id': node_id,
            'node_type': node_type,
            'node_label': node_label,
            'message': message,
            'params': sanitize_params(params),
            'result': summarize_result(node_type, result) if result else {},
        }
        self.entries.append(entry)
        self._persist()

    def log_http(
        self,
        *,
        node_id: str,
        node_type: str,
        node_label: str,
        message: str,
        url: str,
        method: str,
        query_params: dict | None = None,
        status_code: int | None = None,
        extra: dict | None = None,
    ) -> None:
        params = {
            'url': url,
            'method': method,
            'query_params': query_params or {},
            **(extra or {}),
        }
        result = {'status_code': status_code} if status_code is not None else {}
        self.log(
            level='info',
            node_id=node_id,
            node_type=node_type,
            node_label=node_label,
            message=message,
            params=params,
            result=result,
        )

    def _persist(self) -> None:
        if not self.run:
            return
        self.run.execution_log = copy.deepcopy(self.entries)
        self.run.save(update_fields=['execution_log', 'updated_at'])

    def as_list(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.entries)
