"""Gera fluxo ETL a partir de documentação de API (LLM + heurística)."""
import copy
import json
import logging
import re
from typing import Any

from proposal_etl.meta import AUTH_TYPES, resolve_auth_config
from proposal_etl.models import default_flow_definition

logger = logging.getLogger(__name__)

AUTH_TYPE_IDS = {a['id'] for a in AUTH_TYPES}

_LLM_SCHEMA = """
Retorne APENAS JSON válido (sem markdown) no formato:
{
  "name": "Nome sugerido para o fluxo",
  "schedule_trigger": { "cron": "0 8 * * 1-5", "timezone": "America/Sao_Paulo" },
  "http_request": {
    "method": "GET ou POST",
    "url": "URL do endpoint de dados (propostas/operações)",
    "auth_type": "...",
    "auth_config": { ... }
  },
  "paginate_http": {
    "use_instead_of_http_request": true,
    "method": "GET ou POST",
    "url": "URL paginada",
    "auth_type": "...",
    "auth_config": { ... },
    "pagination_mode": "page|offset|cursor|next_url",
    "param_location": "query|body",
    "items_path": "$.data",
    "page_param": "page",
    "page_start": 1,
    "page_size": 100,
    "max_pages": 100,
    "has_more_path": "$.has_more (opcional)"
  },
  "extract_items": { "items_path": "JSONPath da lista, ex: $.data ou $.results" },
  "map_fields": {
    "mappings": [
      { "source_path": "campo na resposta JSON", "layout_field": "nome do campo do layout" }
    ]
  },
  "create_batch": { "layout_id": "uuid do layout se informado no contexto" },
  "warnings": ["avisos sobre o que o usuário precisa preencher manualmente"]
}

Regras:
- Use client_credentials_json quando auth for POST JSON com client_id e client_secret.
- NUNCA inclua client_secret, api_key, token ou senhas reais — apenas placeholders vazios.
- items_path deve apontar para o array de registros na resposta.
- source_path usa dot notation (ex: cliente.cpf) ou nome simples do campo.
- layout_field deve ser um dos campos do layout listados no contexto, se houver.
- Se não souber o JSONPath exato, use $.data e avise no warnings.
"""


def _parse_json_from_llm(raw: str) -> dict:
    clean = raw.strip()
    if '```' in clean:
        parts = clean.split('```')
        for part in parts:
            part = part.strip()
            if part.startswith('json'):
                part = part[4:].strip()
            if part.startswith('{'):
                clean = part
                break
    return json.loads(clean)


def _call_llm(prompt: str, api_key: str, provider: str, model: str | None) -> str:
    if provider == 'openai':
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model or 'gpt-4o',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=2000,
            temperature=0,
        )
        return resp.choices[0].message.content or ''
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model or 'claude-3-5-sonnet-20241022',
        max_tokens=2000,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return resp.content[0].text if resp.content else ''


def _extract_urls(documentation: str) -> list[str]:
    found: list[str] = []
    for match in re.finditer(
        r"curl\s+[^\n]*--location\s+['\"]([^'\"]+)['\"]",
        documentation,
        re.IGNORECASE,
    ):
        url = match.group(1).rstrip('.,;)')
        if url not in found:
            found.append(url)
    for match in re.finditer(
        r"curl\s+[^\n]*['\"](https?://[^'\"]+)['\"]",
        documentation,
        re.IGNORECASE,
    ):
        url = match.group(1).rstrip('.,;)')
        if url not in found:
            found.append(url)
    for match in re.finditer(r'https?://[^\s\'"<>]+', documentation):
        url = match.group(0).rstrip('.,;)')
        if url not in found:
            found.append(url)
    return found


def _extract_client_id(documentation: str) -> str:
    match = re.search(r'"client_id"\s*:\s*"([^"]+)"', documentation)
    return match.group(1) if match else ''


def _guess_token_url(urls: list[str]) -> str:
    for url in urls:
        lower = url.lower()
        if '/auth/' in lower or '/token' in lower or 'oauth' in lower:
            return url
    return ''


def _guess_data_url(urls: list[str], token_url: str) -> str:
    for url in urls:
        if url == token_url:
            continue
        lower = url.lower()
        if any(k in lower for k in ('proposta', 'proposal', 'operac', 'lote', 'batch', 'pagamento')):
            return url
    for url in urls:
        if url != token_url:
            return url
    return ''


def _heuristic_generate(
    documentation: str,
    *,
    layout_id: str | None,
    layout_fields: list[dict],
) -> dict[str, Any]:
    urls = _extract_urls(documentation)
    token_url = _guess_token_url(urls)
    data_url = _guess_data_url(urls, token_url)
    client_id = _extract_client_id(documentation)
    has_client_secret = 'client_secret' in documentation.lower()

    auth_type = 'none'
    auth_config: dict[str, str] = {}
    if token_url and (client_id or has_client_secret):
        auth_type = 'client_credentials_json'
        auth_config = {
            'token_url': token_url,
            'client_id': client_id,
            'client_secret': '',
            'token_field': 'access_token',
        }
    elif 'bearer' in documentation.lower() or 'authorization' in documentation.lower():
        auth_type = 'bearer'
        auth_config = {'token': ''}

    method = 'POST' if re.search(r'\bPOST\b', documentation, re.IGNORECASE) else 'GET'

    warnings = [
        'Rascunho gerado por heurística (sem IA). Revise URLs, JSONPath e mapeamentos.',
        'Preencha client_secret e credenciais manualmente no editor.',
    ]
    if not data_url:
        warnings.append('Não foi possível identificar a URL do endpoint de dados.')
    if not layout_id:
        warnings.append('Selecione o layout no nó "Criar lote".')

    mappings = []
    if layout_fields and documentation:
        doc_lower = documentation.lower()
        for field in layout_fields[:20]:
            name = field['name']
            label = (field.get('label') or name).lower()
            if name.lower() in doc_lower or label in doc_lower:
                mappings.append({'source_path': name, 'layout_field': name})

    return {
        'name': 'Fluxo ETL (rascunho)',
        'schedule_trigger': {'cron': '0 8 * * 1-5', 'timezone': 'America/Sao_Paulo'},
        'http_request': {
            'method': method,
            'url': data_url,
            'auth_type': auth_type,
            'auth_config': auth_config,
        },
        'extract_items': {'items_path': '$.data'},
        'map_fields': {'mappings': mappings},
        'create_batch': {'layout_id': layout_id or ''},
        'warnings': warnings,
    }


def _apply_spec_to_flow(spec: dict[str, Any], layout_id: str | None) -> dict:
    flow = copy.deepcopy(default_flow_definition())
    nodes_by_type = {n['type']: n for n in flow['nodes']}

    if spec.get('paginate_http'):
        http_node = nodes_by_type.get('http_request')
        if http_node:
            http_node['type'] = 'paginate_http'
            http_node['data']['label'] = 'Paginar API'
            nodes_by_type['paginate_http'] = http_node

    for node_type, key in [
        ('schedule_trigger', 'schedule_trigger'),
        ('http_request', 'http_request'),
        ('paginate_http', 'paginate_http'),
        ('extract_items', 'extract_items'),
        ('map_fields', 'map_fields'),
        ('create_batch', 'create_batch'),
    ]:
        patch = spec.get(key) or {}
        if not patch:
            continue
        node = nodes_by_type.get(node_type)
        if not node:
            continue
        data = node.setdefault('data', {})
        if node_type in ('http_request', 'paginate_http'):
            if patch.get('method'):
                data['method'] = str(patch['method']).upper()
            if patch.get('url'):
                data['url'] = patch['url']
            if patch.get('auth_type') in AUTH_TYPE_IDS:
                data['auth_type'] = patch['auth_type']
            if patch.get('auth_config') is not None:
                cfg = dict(patch['auth_config'])
                cfg.pop('client_secret', None)
                data['auth_config'] = resolve_auth_config(data.get('auth_type', 'none'), cfg)
            if node_type == 'paginate_http':
                _apply_pagination_fields(data, patch)
        elif node_type == 'extract_items' and patch.get('items_path'):
            data['items_path'] = patch['items_path']
        elif node_type == 'map_fields' and patch.get('mappings') is not None:
            data['mappings'] = patch['mappings']
        elif node_type == 'create_batch':
            lid = patch.get('layout_id') or layout_id or ''
            if lid:
                data['layout_id'] = str(lid)
        elif node_type == 'schedule_trigger':
            for k in ('cron', 'timezone'):
                if patch.get(k):
                    data[k] = patch[k]

    return flow


def _apply_pagination_fields(data: dict, patch: dict) -> None:
    for key in (
        'pagination_mode', 'param_location', 'items_path', 'page_param', 'page_start',
        'page_size_param', 'offset_param', 'limit_param', 'offset_start',
        'cursor_param', 'cursor_path', 'next_url_path', 'has_more_path', 'max_pages', 'page_size',
    ):
        if patch.get(key) is not None and patch.get(key) != '':
            data[key] = patch[key]
    if 'items_path' not in data:
        data.setdefault('items_path', '$.data')
    data.setdefault('pagination_mode', 'page')
    data.setdefault('max_pages', 100)
    data.setdefault('page_size', 100)


def generate_flow_from_documentation(
    documentation: str,
    *,
    layout_id: str | None = None,
    layout_fields: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Retorna dict com name, flow_definition, warnings, source (llm|heuristic).
    """
    documentation = (documentation or '').strip()
    if not documentation:
        raise ValueError('Documentação é obrigatória.')

    layout_fields = layout_fields or []
    field_lines = '\n'.join(
        f"  - {f['name']}: {f.get('label', f['name'])} ({f.get('data_type', 'text')})"
        for f in layout_fields
    ) or '  (nenhum layout selecionado)'

    prompt = (
        'Você configura fluxos ETL que consultam APIs bancárias e importam propostas.\n\n'
        f'CAMPOS DO LAYOUT (layout_field deve ser um destes nomes):\n{field_lines}\n\n'
        f'LAYOUT_ID: {layout_id or "(não informado)"}\n\n'
        f'TIPOS DE AUTH DISPONÍVEIS: {", ".join(sorted(AUTH_TYPE_IDS))}\n\n'
        f'DOCUMENTAÇÃO / EXEMPLOS:\n{documentation[:12000]}\n\n'
        f'{_LLM_SCHEMA}'
    )

    spec: dict[str, Any] | None = None
    source = 'heuristic'

    try:
        from core.models import SystemSettings
        settings = SystemSettings.get_solo()
        if settings.ai_api_key:
            raw = _call_llm(prompt, settings.ai_api_key, settings.ai_provider, settings.ai_model)
            spec = _parse_json_from_llm(raw)
            source = 'llm'
    except Exception as exc:
        logger.warning('generate_flow_from_documentation LLM falhou: %s', exc)

    if not spec:
        spec = _heuristic_generate(
            documentation,
            layout_id=layout_id,
            layout_fields=layout_fields,
        )

    name = (spec.get('name') or 'Fluxo ETL (IA)').strip()[:255]
    warnings = list(spec.get('warnings') or [])
    if source == 'llm':
        warnings.insert(0, 'Rascunho gerado por IA. Revise credenciais, URLs e mapeamentos antes de executar.')
    warnings.append('Preencha client_secret e demais credenciais no editor antes de executar.')

    flow_definition = _apply_spec_to_flow(spec, layout_id)

    return {
        'name': name,
        'flow_definition': flow_definition,
        'warnings': warnings,
        'source': source,
    }
