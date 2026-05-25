"""
Módulo de integração LLM para o agente IA do CorbanPlus.

Fase 1: respostas por palavras-chave (nenhuma dependência externa).
Fase 2: chamadas reais ao OpenAI ou Anthropic usando a chave configurada
        em SystemSettings pela promotora.

Interface pública:
    get_ai_reply(history) -> (reply_text: str, tour_name: str | None)
"""
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Mapa de palavras-chave → (resposta, tour_name) ───────────────────────────

_KEYWORD_MAP = [
    (
        ['grupo', 'equipe', 'team'],
        (
            'Para criar uma equipe de comissão, acesse o menu lateral **Equipes** '
            'e clique em **Nova Equipe**. Posso te guiar até lá!',
            'criar-grupo-comissao',
        ),
    ),
    (
        ['sugest', 'aceitar sugest', 'tabela atualiz'],
        (
            'As sugestões de atualização aparecem no topo da página de Equipes quando '
            'uma tabela bancária é atualizada. Posso te mostrar como aceitar!',
            'aceitar-sugestao-tabela',
        ),
    ),
    (
        ['csv', 'importar', 'import'],
        (
            'Você pode importar tabelas por CSV no menu **Tabelas**. '
            'Vou te mostrar o processo!',
            'importar-csv',
        ),
    ),
    (
        ['tabela', 'configurar tabela', 'config tabela'],
        (
            'As tabelas bancárias ficam em **Bancos → Tabelas**. '
            'Posso te guiar até a configuração!',
            'configurar-tabela',
        ),
    ),
    (
        ['vendedor', 'criar vendedor', 'novo vendedor'],
        (
            'Para criar um vendedor, acesse **Usuários → Criar**. '
            'Posso te mostrar o passo a passo!',
            'criar-vendedor',
        ),
    ),
]

_FALLBACK_TEXT = (
    'Posso te ajudar com: **criar equipes**, **sugestões de tabela**, '
    '**importar CSV**, **configurar tabelas** e **criar vendedores**. '
    'Sobre o que você gostaria de saber mais?'
)

# ─── System prompt para o LLM ─────────────────────────────────────────────────

_SYSTEM_PROMPT = """Você é o assistente do CorbanPlus, um sistema de gestão de comissões para correspondentes bancários.

Responda sempre em português brasileiro, de forma clara e direta.

Quando a mensagem do usuário se relacionar com uma das funcionalidades abaixo, inclua o campo "tour_name" na sua resposta JSON:
- Criar equipe/grupo de comissão → "criar-grupo-comissao"
- Aceitar sugestão de tabela → "aceitar-sugestao-tabela"
- Importar CSV de tabelas → "importar-csv"
- Configurar tabela bancária → "configurar-tabela"
- Criar vendedor → "criar-vendedor"

SEMPRE responda SOMENTE com JSON válido neste formato:
{"text": "<sua resposta em texto>", "tour_name": "<nome do tour ou null>"}

Exemplo:
{"text": "Para criar uma equipe, acesse o menu Equipes e clique em Nova Equipe.", "tour_name": "criar-grupo-comissao"}
"""

# ─── Implementação Fase 1: palavras-chave ─────────────────────────────────────


def _keyword_reply(last_message: str) -> tuple[str, Optional[str]]:
    lower = last_message.lower()
    for keywords, (text, tour) in _KEYWORD_MAP:
        if any(kw in lower for kw in keywords):
            return text, tour
    return _FALLBACK_TEXT, None


# ─── Implementação Fase 2: LLM real ──────────────────────────────────────────


def _call_openai(api_key: str, model: str, history: list[dict]) -> tuple[str, Optional[str]]:
    try:
        from openai import OpenAI  # type: ignore[import]
    except ImportError:
        logger.warning('openai package not installed. Falling back to keywords.')
        return _keyword_reply(history[-1]['content'] if history else '')

    client = OpenAI(api_key=api_key)
    messages = [{'role': 'system', 'content': _SYSTEM_PROMPT}]
    messages += [{'role': m['role'], 'content': m['content']} for m in history]

    response = client.chat.completions.create(
        model=model or 'gpt-4o-mini',
        messages=messages,
        max_tokens=400,
        temperature=0.4,
    )
    raw = response.choices[0].message.content or ''
    return _parse_llm_json(raw)


def _call_anthropic(api_key: str, model: str, history: list[dict]) -> tuple[str, Optional[str]]:
    try:
        import anthropic  # type: ignore[import]
    except ImportError:
        logger.warning('anthropic package not installed. Falling back to keywords.')
        return _keyword_reply(history[-1]['content'] if history else '')

    client = anthropic.Anthropic(api_key=api_key)

    # Anthropic usa system separado dos messages
    messages = [{'role': m['role'], 'content': m['content']} for m in history]

    response = client.messages.create(
        model=model or 'claude-3-haiku-20240307',
        max_tokens=400,
        system=_SYSTEM_PROMPT,
        messages=messages,
    )
    raw = response.content[0].text if response.content else ''
    return _parse_llm_json(raw)


def _parse_llm_json(raw: str) -> tuple[str, Optional[str]]:
    """Extrai {"text": ..., "tour_name": ...} da resposta do LLM."""
    try:
        # Remove marcadores de código se presentes
        clean = raw.strip()
        if clean.startswith('```'):
            clean = clean.split('```')[1]
            if clean.startswith('json'):
                clean = clean[4:]
        data = json.loads(clean)
        text = data.get('text') or raw
        tour_name = data.get('tour_name') or None
        return text, tour_name
    except Exception:
        return raw, None


# ─── Ponto de entrada público ─────────────────────────────────────────────────


def get_ai_reply(history: list[dict]) -> tuple[str, Optional[str]]:
    """
    Retorna (texto_resposta, tour_name_ou_None).

    Se a promotora tiver uma chave AI configurada, chama o LLM real.
    Caso contrário usa respostas por palavras-chave.
    """
    last_msg = history[-1]['content'] if history else ''

    try:
        from core.models import SystemSettings
        settings = SystemSettings.get_solo()
        api_key = (settings.ai_api_key or '').strip()
        provider = settings.ai_provider
        model = (settings.ai_model or '').strip()
    except Exception:
        return _keyword_reply(last_msg)

    if not api_key:
        return _keyword_reply(last_msg)

    try:
        if provider == SystemSettings.PROVIDER_OPENAI:
            return _call_openai(api_key, model, history)
        elif provider == SystemSettings.PROVIDER_ANTHROPIC:
            return _call_anthropic(api_key, model, history)
    except Exception as exc:
        logger.error('Erro ao chamar LLM (%s): %s', provider, exc)

    # Fallback caso a chamada falhe
    return _keyword_reply(last_msg)
