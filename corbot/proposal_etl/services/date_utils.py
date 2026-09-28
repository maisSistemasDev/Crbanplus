"""Datas dinâmicas relativas ao dia da execução (d, d-7, d-1)."""
import re
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

# Valor inteiro: d, d-7, d -7, d+0, {d-7}, d-7|%d/%m/%Y
_DATE_VALUE_RE = re.compile(
    r'^\s*\{?\s*d\s*([+-]\s*\d+)?\s*\}?\s*(?:\|(?P<fmt>[^|{}]+))?\s*$',
    re.IGNORECASE,
)

# Trecho em URL/texto: {d-7} ou {d-7|%d/%m/%Y}
_INLINE_DATE_RE = re.compile(
    r'\{d\s*([+-]\s*\d+)?(?:\|([^{}]+))?\}',
    re.IGNORECASE,
)


def _reference_date(timezone: str) -> date:
    return datetime.now(ZoneInfo(timezone)).date()


def _format_date(base: date, offset_days: int, fmt: str) -> str:
    return (base + timedelta(days=offset_days)).strftime(fmt)


def _parse_offset(offset_str: str | None) -> int:
    if not offset_str:
        return 0
    return int(offset_str.replace(' ', ''))


def resolve_date_expression(
    expr: str,
    *,
    date_format: str = '%Y-%m-%d',
    timezone: str = 'America/Sao_Paulo',
) -> str:
    """Converte expressão de data dinâmica em string formatada."""
    if expr is None:
        return expr
    text = str(expr).strip()
    if not text:
        return text

    match = _DATE_VALUE_RE.match(text)
    if match:
        fmt = (match.group('fmt') or date_format).strip()
        offset = _parse_offset(match.group(1))
        return _format_date(_reference_date(timezone), offset, fmt)

    return resolve_dynamic_string(text, date_format=date_format, timezone=timezone)


def resolve_dynamic_string(
    text: str,
    *,
    date_format: str = '%Y-%m-%d',
    timezone: str = 'America/Sao_Paulo',
) -> str:
    if not text or '{' not in text:
        return text

    base = _reference_date(timezone)

    def repl(match: re.Match) -> str:
        offset = _parse_offset(match.group(1))
        fmt = (match.group(2) or date_format).strip()
        return _format_date(base, offset, fmt)

    return _INLINE_DATE_RE.sub(repl, text)


def resolve_dynamic_value(
    value: Any,
    *,
    date_format: str = '%Y-%m-%d',
    timezone: str = 'America/Sao_Paulo',
) -> Any:
    if isinstance(value, str):
        resolved = resolve_date_expression(value, date_format=date_format, timezone=timezone)
        if resolved != value:
            return resolved
        return resolve_dynamic_string(value, date_format=date_format, timezone=timezone)
    if isinstance(value, dict):
        return resolve_dynamic_dict(value, date_format=date_format, timezone=timezone)
    if isinstance(value, list):
        return [
            resolve_dynamic_value(v, date_format=date_format, timezone=timezone)
            for v in value
        ]
    return value


def resolve_dynamic_dict(
    data: dict | None,
    *,
    date_format: str = '%Y-%m-%d',
    timezone: str = 'America/Sao_Paulo',
) -> dict:
    if not data:
        return {}
    return {
        str(k): resolve_dynamic_value(v, date_format=date_format, timezone=timezone)
        for k, v in data.items()
    }
