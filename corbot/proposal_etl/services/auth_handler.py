"""Autenticação HTTP configurável para nós do ETL."""
import requests

from proposal_etl.meta import resolve_auth_config

REQUEST_TIMEOUT = 30

TOKEN_JSON_KEYS = ('access_token', 'token', 'bearer_token', 'accessToken')


def _extract_bearer_token(payload: dict, token_field: str | None = None) -> str:
    if token_field:
        parts = token_field.split('.')
        value = payload
        for part in parts:
            if not isinstance(value, dict):
                break
            value = value.get(part)
        if isinstance(value, str) and value:
            return value

    for key in TOKEN_JSON_KEYS:
        token = payload.get(key)
        if isinstance(token, str) and token:
            return token

    data = payload.get('data')
    if isinstance(data, dict):
        for key in TOKEN_JSON_KEYS:
            token = data.get(key)
            if isinstance(token, str) and token:
                return token

    raise ValueError('Resposta de autenticação não contém token Bearer.')


TOKEN_AUTH_TYPES = frozenset({'client_credentials_json', 'oauth2_client_credentials'})


class AuthHandler:
    def __init__(self, auth_type: str, auth_config: dict | None):
        self.auth_type = auth_type or 'none'
        self.auth_config = auth_config or {}

    def apply(self, headers: dict | None = None) -> dict:
        headers = dict(headers or {})
        cfg = resolve_auth_config(self.auth_type, self.auth_config)

        if self.auth_type == 'api_key':
            header_name = cfg.get('header_name', 'X-Api-Key')
            headers[header_name] = cfg.get('api_key', '')
        elif self.auth_type == 'bearer':
            token = cfg.get('token', '')
            headers['Authorization'] = f'Bearer {token}'
        elif self.auth_type == 'basic':
            import base64
            user = cfg.get('username', '')
            password = cfg.get('password', '')
            encoded = base64.b64encode(f'{user}:{password}'.encode()).decode()
            headers['Authorization'] = f'Basic {encoded}'
        elif self.auth_type == 'client_credentials_json':
            token = self._fetch_bearer_token_json(cfg)
            headers['Authorization'] = f'Bearer {token}'
        elif self.auth_type == 'oauth2_client_credentials':
            token = self._fetch_bearer_token_oauth(cfg)
            headers['Authorization'] = f'Bearer {token}'

        return headers

    def _fetch_bearer_token_json(self, cfg: dict) -> str:
        token_url = (cfg.get('token_url') or '').strip()
        if not token_url:
            raise ValueError('URL do token é obrigatória.')
        resp = requests.post(
            token_url,
            json={
                'client_id': cfg.get('client_id', ''),
                'client_secret': cfg.get('client_secret', ''),
            },
            headers={'Content-Type': 'application/json'},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return _extract_bearer_token(resp.json(), cfg.get('token_field') or None)

    def _fetch_bearer_token_oauth(self, cfg: dict) -> str:
        token_url = cfg.get('token_url', '')
        data = {
            'grant_type': 'client_credentials',
            'client_id': cfg.get('client_id', ''),
            'client_secret': cfg.get('client_secret', ''),
        }
        if cfg.get('scope'):
            data['scope'] = cfg['scope']
        resp = requests.post(token_url, data=data, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return _extract_bearer_token(resp.json(), cfg.get('token_field') or 'access_token')


class AuthSession:
    """Cache de token Bearer por execução (reutiliza sessão entre nós HTTP)."""

    def __init__(self) -> None:
        self._tokens: dict[str, str] = {}
        self._token_fetched = False

    def _cache_key(self, auth_type: str, auth_config: dict) -> str:
        cfg = resolve_auth_config(auth_type, auth_config)
        parts = [auth_type]
        for key in sorted(cfg.keys()):
            if key.lower() in ('client_secret', 'password', 'api_key', 'token'):
                parts.append(f'{key}=***')
            else:
                parts.append(f'{key}={cfg[key]}')
        return '|'.join(parts)

    def apply(self, auth_type: str, auth_config: dict | None, headers: dict | None = None) -> dict:
        auth_type = auth_type or 'none'
        headers = dict(headers or {})

        if auth_type not in TOKEN_AUTH_TYPES:
            return AuthHandler(auth_type, auth_config).apply(headers)

        key = self._cache_key(auth_type, auth_config or {})
        if key not in self._tokens:
            handler = AuthHandler(auth_type, auth_config)
            if auth_type == 'client_credentials_json':
                cfg = resolve_auth_config(auth_type, auth_config)
                self._tokens[key] = handler._fetch_bearer_token_json(cfg)
            else:
                cfg = resolve_auth_config(auth_type, auth_config)
                self._tokens[key] = handler._fetch_bearer_token_oauth(cfg)
            self._token_fetched = True

        headers['Authorization'] = f'Bearer {self._tokens[key]}'
        return headers

    @property
    def token_was_fetched(self) -> bool:
        return self._token_fetched
