"""Metadados de autenticação HTTP para o ETL."""

AUTH_TYPES = [
    {
        'id': 'none',
        'label': 'Sem autenticação',
        'fields': [],
    },
    {
        'id': 'api_key',
        'label': 'API Key',
        'fields': [
            {'name': 'header_name', 'type': 'text', 'label': 'Nome do header', 'default': 'X-Api-Key'},
            {'name': 'api_key', 'type': 'password', 'label': 'Chave'},
        ],
    },
    {
        'id': 'bearer',
        'label': 'Bearer Token',
        'fields': [{'name': 'token', 'type': 'password', 'label': 'Token'}],
    },
    {
        'id': 'basic',
        'label': 'Basic Auth',
        'fields': [
            {'name': 'username', 'type': 'text', 'label': 'Usuário'},
            {'name': 'password', 'type': 'password', 'label': 'Senha'},
        ],
    },
    {
        'id': 'client_credentials_json',
        'label': 'Client ID + Secret (JSON → Bearer)',
        'fields': [
            {
                'name': 'token_url',
                'type': 'url',
                'label': 'URL do token',
                'default': 'https://gtw.unnotech.com.br/public/api/v1/auth/token',
            },
            {'name': 'client_id', 'type': 'text', 'label': 'Client ID'},
            {'name': 'client_secret', 'type': 'password', 'label': 'Client Secret'},
            {
                'name': 'token_field',
                'type': 'text',
                'label': 'Campo do token na resposta',
                'required': False,
                'default': 'access_token',
            },
        ],
    },
    {
        'id': 'oauth2_client_credentials',
        'label': 'OAuth2 Client Credentials',
        'fields': [
            {'name': 'token_url', 'type': 'url', 'label': 'URL do token'},
            {'name': 'client_id', 'type': 'text', 'label': 'Client ID'},
            {'name': 'client_secret', 'type': 'password', 'label': 'Client Secret'},
            {'name': 'scope', 'type': 'text', 'label': 'Scope', 'required': False},
        ],
    },
]


NODE_TYPES = [
    {'id': 'schedule_trigger', 'label': 'Agendamento', 'category': 'trigger'},
    {'id': 'http_request', 'label': 'HTTP Request', 'category': 'source'},
    {'id': 'paginate_http', 'label': 'Paginar API', 'category': 'source'},
    {'id': 'extract_items', 'label': 'Extrair lista', 'category': 'transform'},
    {'id': 'fetch_item_details', 'label': 'Detalhar itens', 'category': 'transform'},
    {'id': 'map_fields', 'label': 'Mapear campos', 'category': 'transform'},
    {'id': 'create_batch', 'label': 'Criar lote', 'category': 'output'},
]

PAGINATION_MODES = [
    {'id': 'page', 'label': 'Número de página (page=1,2,3...)'},
    {'id': 'offset', 'label': 'Offset + limit'},
    {'id': 'cursor', 'label': 'Cursor na resposta'},
    {'id': 'next_url', 'label': 'URL da próxima página'},
]

FIELD_TRANSFORMS = [
    {'id': '', 'label': 'Nenhuma'},
    {'id': 'strip', 'label': 'Remover espaços'},
    {'id': 'upper', 'label': 'MAIÚSCULAS'},
    {'id': 'lower', 'label': 'minúsculas'},
    {'id': 'format_cpf', 'label': 'Formatar CPF'},
    {'id': 'digits_only', 'label': 'Somente dígitos'},
]

CONDITION_OPERATORS = [
    {'id': 'eq', 'label': 'igual a'},
    {'id': 'ne', 'label': 'diferente de'},
    {'id': 'empty', 'label': 'vazio'},
    {'id': 'not_empty', 'label': 'não vazio'},
    {'id': 'contains', 'label': 'contém'},
]

DATE_EXPRESSION_HELP = {
    'syntax': 'd = hoje, d-7 = 7 dias atrás, d-1 = ontem, d+0 = hoje',
    'examples': [
        {'param': 'start_date', 'value': 'd-7'},
        {'param': 'end_date', 'value': 'd-1'},
    ],
    'formats': [
        {'id': '%Y-%m-%d', 'label': '2026-06-08 (ISO)'},
        {'id': '%d/%m/%Y', 'label': '08/06/2026 (BR)'},
        {'id': '%Y-%m-%dT00:00:00', 'label': 'ISO com hora'},
    ],
    'per_value_format': 'd-7|%d/%m/%Y',
    'inline_url': 'https://api.../propostas?start={d-7}&end={d-1}',
}


def resolve_auth_config(auth_type: str, auth_config: dict | None) -> dict:
    """Preenche campos de auth_config vazios com defaults do meta."""
    cfg = dict(auth_config or {})
    for auth in AUTH_TYPES:
        if auth['id'] != auth_type:
            continue
        for field in auth.get('fields', []):
            default = field.get('default')
            name = field.get('name')
            if not name or default is None:
                continue
            current = cfg.get(name)
            if current is None or (isinstance(current, str) and not current.strip()):
                cfg[name] = default
        break
    return cfg
