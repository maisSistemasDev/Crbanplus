"""Agendamento humano ↔ expressão cron."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

WEEKDAY_LABELS = {
    0: 'Dom',
    1: 'Seg',
    2: 'Ter',
    3: 'Qua',
    4: 'Qui',
    5: 'Sex',
    6: 'Sáb',
}

SCHEDULE_MODES = ('daily', 'weekdays', 'weekly', 'custom')


def parse_time_hhmm(value: str) -> tuple[int, int]:
    raw = (value or '08:00').strip()
    parts = raw.split(':')
    hour = int(parts[0]) if parts else 8
    minute = int(parts[1]) if len(parts) > 1 else 0
    hour = max(0, min(23, hour))
    minute = max(0, min(59, minute))
    return minute, hour


def human_schedule_to_cron(data: dict) -> str:
    mode = (data.get('schedule_mode') or 'weekdays').strip().lower()
    minute, hour = parse_time_hhmm(data.get('schedule_time') or '08:00')

    if mode == 'custom':
        return (data.get('cron') or '0 8 * * 1-5').strip()

    if mode == 'daily':
        return f'{minute} {hour} * * *'

    if mode == 'weekdays':
        return f'{minute} {hour} * * 1-5'

    if mode == 'weekly':
        days = data.get('schedule_weekdays') or [1, 2, 3, 4, 5]
        if not isinstance(days, list):
            days = [1, 2, 3, 4, 5]
        days = sorted({int(d) for d in days if 0 <= int(d) <= 6})
        if not days:
            days = [1]
        return f'{minute} {hour} * * {",".join(str(d) for d in days)}'

    return f'{minute} {hour} * * 1-5'


def cron_to_human_summary(cron: str, mode: str | None = None, time_str: str | None = None) -> str:
    cron = (cron or '').strip()
    mode = (mode or '').strip().lower()
    time_label = time_str or ''

    if mode == 'daily':
        return f'Todos os dias às {time_label or cron}'
    if mode == 'weekdays':
        return f'Segunda a sexta às {time_label or cron}'
    if mode == 'weekly':
        return f'Dias selecionados às {time_label or cron}'
    if mode == 'custom':
        return f'Cron personalizado: {cron}'
    return cron


def build_schedule_summary(data: dict) -> str:
    mode = (data.get('schedule_mode') or 'weekdays').strip().lower()
    time_str = (data.get('schedule_time') or '08:00').strip()
    tz = (data.get('timezone') or 'America/Sao_Paulo').strip()

    if mode == 'daily':
        return f'Todos os dias às {time_str} ({tz})'
    if mode == 'weekdays':
        return f'Segunda a sexta às {time_str} ({tz})'
    if mode == 'weekly':
        days = data.get('schedule_weekdays') or [1, 2, 3, 4, 5]
        if not isinstance(days, list):
            days = [1, 2, 3, 4, 5]
        labels = [WEEKDAY_LABELS.get(int(d), str(d)) for d in sorted(days)]
        return f'{", ".join(labels)} às {time_str} ({tz})'
    if mode == 'custom':
        cron = (data.get('cron') or '').strip()
        return f'Cron: {cron} ({tz})'
    return f'{time_str} ({tz})'


def cron_matches_now(cron_expr: str, tz_name: str, *, now: datetime | None = None) -> bool:
    """Verifica se o cron dispara no minuto atual (sem croniter)."""
    parts = (cron_expr or '').strip().split()
    if len(parts) != 5:
        return False

    tz = ZoneInfo(tz_name or 'America/Sao_Paulo')
    dt = (now or datetime.now(tz)).astimezone(tz)
    minute_f, hour_f, dom_f, month_f, dow_f = parts

    cron_dow = dt.isoweekday() % 7  # 0=domingo … 6=sábado (estilo Vixie)

    return (
        _field_matches(minute_f, dt.minute, 0, 59)
        and _field_matches(hour_f, dt.hour, 0, 23)
        and _field_matches(dom_f, dt.day, 1, 31)
        and _field_matches(month_f, dt.month, 1, 12)
        and _field_matches(dow_f, cron_dow, 0, 6)
    )


def _field_matches(field: str, value: int, min_val: int, max_val: int) -> bool:
    field = field.strip()
    if field == '*':
        return True
    for part in field.split(','):
        part = part.strip()
        if '/' in part:
            base, step_s = part.split('/', 1)
            step = int(step_s)
            if base == '*':
                if (value - min_val) % step == 0:
                    return True
                continue
            part = base
        if '-' in part:
            start_s, end_s = part.split('-', 1)
            start, end = int(start_s), int(end_s)
            if start <= value <= end:
                return True
        elif int(part) == value:
            return True
    return False


def get_schedule_from_flow(flow_definition: dict) -> dict | None:
    for node in flow_definition.get('nodes', []):
        if node.get('type') == 'schedule_trigger':
            return node.get('data') or {}
    return None
