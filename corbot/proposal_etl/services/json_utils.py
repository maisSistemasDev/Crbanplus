"""Utilitários JSON path simples para o ETL."""
import re
from typing import Any


def resolve_json_path(data: Any, path: str) -> Any:
    if not path or path in ('$', ''):
        return data
    path = path.strip()
    if path.startswith('$.'):
        path = path[2:]
    elif path.startswith('$'):
        path = path[1:].lstrip('.')
    current = data
    for part in path.split('.'):
        if part == '':
            continue
        match = re.match(r'^(\w+)\[(\d+)\]$', part)
        if match:
            key, idx = match.group(1), int(match.group(2))
            current = current[key][idx]
        elif isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            return None
        if current is None:
            return None
    return current


def get_value_from_item(item: dict, path: str) -> Any:
    if not path:
        return None
    path = path.strip()
    if path.startswith('$.'):
        path = path[2:]
    elif path.startswith('$'):
        path = path[1:].lstrip('.')
    current: Any = item
    for part in path.split('.'):
        if not part:
            continue
        match = re.match(r'^(\w+)\[(\d+)\]$', part)
        if match:
            key, idx = match.group(1), int(match.group(2))
            if not isinstance(current, dict):
                return None
            arr = current.get(key)
            if not isinstance(arr, list) or idx >= len(arr):
                return None
            current = arr[idx]
        elif isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            current = current[idx] if idx < len(current) else None
        else:
            return None
        if current is None:
            return None
    return current


def apply_transform(value: Any, transform: str | None) -> Any:
    if value is None or not transform:
        return value
    if transform == 'strip' and isinstance(value, str):
        return value.strip()
    if transform == 'upper' and isinstance(value, str):
        return value.upper()
    if transform == 'lower' and isinstance(value, str):
        return value.lower()
    if transform == 'format_cpf':
        digits = re.sub(r'\D', '', str(value))
        if len(digits) >= 11:
            digits = digits[-11:]
            return f'{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}'
        return value
    if transform == 'digits_only':
        return re.sub(r'\D', '', str(value))
    return value


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def evaluate_mapping_condition(item: dict, condition: dict | None) -> bool:
    if not condition:
        return True
    path = (condition.get('path') or '').strip()
    if not path:
        return True
    op = (condition.get('op') or 'eq').strip().lower()
    expected = condition.get('value')
    actual = get_value_from_item(item, path)

    if op == 'empty':
        return _is_empty(actual)
    if op == 'not_empty':
        return not _is_empty(actual)
    if op == 'contains':
        if _is_empty(actual) or expected is None:
            return False
        return str(expected) in str(actual)
    if op == 'ne':
        return str(actual) != str(expected)
    return str(actual) == str(expected)


class SkipFieldMapping:
    """Sentinela: não incluir o campo na linha mapeada."""


SKIP_FIELD_MAPPING = SkipFieldMapping()


def resolve_mapping_value(item: dict, mapping: dict) -> Any:
    """Resolve valor do mapeamento com condição, fallback e transformação."""
    when = mapping.get('when')
    if when and not evaluate_mapping_condition(item, when):
        if mapping.get('skip_if_unmatched'):
            return SKIP_FIELD_MAPPING
        if mapping.get('else_source_path'):
            path = mapping['else_source_path']
        else:
            return None
    else:
        path = mapping.get('source_path', '')

    value = get_value_from_item(item, path) if path else None

    fallback = (mapping.get('fallback_source_path') or '').strip()
    if _is_empty(value) and fallback:
        value = get_value_from_item(item, fallback)

    return apply_transform(value, mapping.get('transform'))
