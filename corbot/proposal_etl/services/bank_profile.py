"""Perfil ETL reutilizável por banco (paginação, auth, detalhes)."""
from __future__ import annotations

from typing import Any


def _node_order(flow_definition: dict) -> list[str]:
    nodes = {n['id']: n for n in flow_definition.get('nodes', [])}
    incoming = {nid: 0 for nid in nodes}
    adjacency: dict[str, list[str]] = {nid: [] for nid in nodes}
    for edge in flow_definition.get('edges', []):
        src, tgt = edge.get('source'), edge.get('target')
        if src in adjacency and tgt in incoming:
            adjacency[src].append(tgt)
            incoming[tgt] += 1
    order: list[str] = []
    queue = [nid for nid, count in incoming.items() if count == 0]
    while queue:
        node_id = queue.pop(0)
        order.append(node_id)
        for tgt in adjacency.get(node_id, []):
            incoming[tgt] -= 1
            if incoming[tgt] == 0:
                queue.append(tgt)
    for nid in nodes:
        if nid not in order:
            order.append(nid)
    return order


def _strip_node_meta(data: dict) -> dict:
    out = {k: v for k, v in data.items() if k not in ('label', 'nodeType')}
    return out


def _merge_node_data(current: dict, patch: dict) -> dict:
    merged = {**current}
    for key, value in patch.items():
        if key in ('label', 'nodeType'):
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    if patch.get('label'):
        merged['label'] = patch['label']
    return merged


def extract_settings_from_flow(flow_definition: dict) -> dict[str, Any]:
    """Extrai defaults dos nós do fluxo para salvar como perfil do banco."""
    nodes_by_id = {n['id']: n for n in flow_definition.get('nodes', [])}
    order = _node_order(flow_definition)

    settings: dict[str, Any] = {}
    detail_steps: list[dict] = []

    for node_id in order:
        node = nodes_by_id.get(node_id)
        if not node:
            continue
        node_type = node.get('type')
        data = _strip_node_meta(node.get('data') or {})

        if node_type == 'paginate_http' and 'paginate_http' not in settings:
            settings['paginate_http'] = data
        elif node_type == 'extract_items' and 'extract_items' not in settings:
            settings['extract_items'] = data
        elif node_type == 'fetch_item_details':
            step = {**data}
            if node.get('data', {}).get('label'):
                step['label'] = node['data']['label']
            detail_steps.append(step)

    if detail_steps:
        settings['detail_steps'] = detail_steps

    return settings


def apply_settings_to_flow(flow_definition: dict, settings: dict) -> dict:
    """Aplica perfil do banco aos nós existentes do fluxo."""
    if not settings:
        return flow_definition

    definition = {
        'nodes': [dict(n) for n in flow_definition.get('nodes', [])],
        'edges': list(flow_definition.get('edges', [])),
        'viewport': flow_definition.get('viewport'),
    }
    nodes_by_id = {n['id']: n for n in definition['nodes']}
    order = _node_order(definition)

    detail_steps = settings.get('detail_steps') or []
    detail_idx = 0

    for node_id in order:
        node = nodes_by_id.get(node_id)
        if not node:
            continue
        node_type = node.get('type')
        data = node.setdefault('data', {})

        if node_type == 'paginate_http' and settings.get('paginate_http'):
            node['data'] = _merge_node_data(data, settings['paginate_http'])
        elif node_type == 'extract_items' and settings.get('extract_items'):
            node['data'] = _merge_node_data(data, settings['extract_items'])
        elif node_type == 'fetch_item_details' and detail_idx < len(detail_steps):
            patch = dict(detail_steps[detail_idx])
            label = patch.pop('label', None)
            node['data'] = _merge_node_data(data, patch)
            if label:
                node['data']['label'] = label
            detail_idx += 1

    return definition
