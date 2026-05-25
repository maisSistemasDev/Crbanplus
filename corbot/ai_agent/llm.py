"""
Módulo LLM do agente IA — CorbanPlus.

Funcionalidades:
  1. Function calling (tools): bancos, tabelas, convênios
  2. Vision: imagens e arquivos enviados pelo usuário
  3. Janela de contexto deslizante: últimas 10 mensagens diretas +
     N mensagens antigas recuperadas por similaridade de embeddings
  4. Fallback por palavras-chave quando não há chave de API configurada
"""
import base64
import json
import logging
import math
import mimetypes
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CONTEXT_WINDOW = 10
MAX_RETRIEVED   = 3
EMBED_MODEL_OAI = "text-embedding-3-small"

_SYSTEM_PROMPT = """Você é o assistente do CorbanPlus, sistema de gestão de correspondência bancária.

RESPONSABILIDADES:
- Gerenciar bancos, convênios e tabelas de comissionamento usando as ferramentas disponíveis.
- Extrair dados de imagens enviadas pelo usuário (tabelas bancárias, comunicados).
- Orientar usuários sobre como usar o sistema (ofereça tours interativos quando aplicável).

IDIOMA: Sempre responda em português brasileiro.

FERRAMENTAS: Sempre que o usuário solicitar informações ou alterações em bancos/tabelas/convênios,
use as ferramentas disponíveis. Nunca invente dados — consulte o sistema.

IMAGENS: Quando receber uma imagem de tabela bancária, extraia todos os dados estruturados
(taxas, faixas, datas, nome do produto) e pergunte se o usuário deseja aplicar as alterações.

TOUR: Quando a resposta envolver navegação pelo sistema, inclua "tour_name" no JSON.
Tours disponíveis: criar-grupo-comissao, aceitar-sugestao-tabela, importar-csv,
configurar-tabela, criar-vendedor.

FORMATO DE RESPOSTA: Sempre responda com JSON válido:
{"text": "<resposta>", "tour_name": "<tour ou null>"}
"""

_KEYWORD_MAP = [
    (['grupo', 'equipe'],
     ('Para criar uma equipe de comissão, acesse Equipes e clique em Nova Equipe. Posso te guiar!', 'criar-grupo-comissao')),
    (['sugest', 'aceitar'],
     ('As sugestões ficam no topo da página de Equipes. Posso te mostrar!', 'aceitar-sugestao-tabela')),
    (['csv', 'importar'],
     ('Importe tabelas via CSV em Usuários → Importar CSV.', 'importar-csv')),
    (['tabela', 'config tabela'],
     ('Tabelas ficam em Bancos → Tabelas. Posso te guiar!', 'configurar-tabela')),
    (['vendedor', 'criar vendedor'],
     ('Crie vendedores em Usuários → Criar.', 'criar-vendedor')),
]

_FALLBACK = ('Posso ajudar com bancos, tabelas, convênios e gestão de equipes. O que precisa?', None)


def _keyword_reply(text: str) -> tuple[str, Optional[str]]:
    lower = text.lower()
    for keywords, result in _KEYWORD_MAP:
        if any(kw in lower for kw in keywords):
            return result
    return _FALLBACK


def _cosine_similarity(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _embed_openai(api_key: str, text: str) -> list:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.embeddings.create(input=text, model=EMBED_MODEL_OAI)
    return resp.data[0].embedding


def compute_and_store_embedding(message_pk: int, api_key: str) -> None:
    try:
        from ai_agent.models import Message
        msg = Message.objects.get(pk=message_pk)
        if msg.embedding:
            return
        vector = _embed_openai(api_key, msg.content[:2000])
        msg.embedding = vector
        msg.save(update_fields=["embedding"])
    except Exception as exc:
        logger.warning("compute_and_store_embedding failed for msg %s: %s", message_pk, exc)


def _retrieve_relevant_old_messages(conversation_id, query_text, exclude_ids, api_key, top_k=MAX_RETRIEVED):
    try:
        from ai_agent.models import Message
        old_msgs = Message.objects.filter(
            conversation_id=conversation_id,
            embedding__isnull=False,
        ).exclude(pk__in=exclude_ids)
        if not old_msgs.exists():
            return []
        query_vec = _embed_openai(api_key, query_text[:2000])
        scored = []
        for m in old_msgs:
            if not m.embedding:
                continue
            sim = _cosine_similarity(query_vec, m.embedding)
            scored.append((sim, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]
        return [
            {"role": m.role, "content": m.content}
            for _, m in sorted(top, key=lambda x: x[1].created_at)
        ]
    except Exception as exc:
        logger.warning("_retrieve_relevant_old_messages failed: %s", exc)
        return []


def build_context_messages(history, conversation_id=None, query_text="", api_key=""):
    if len(history) <= CONTEXT_WINDOW:
        return list(history)
    recent = history[-CONTEXT_WINDOW:]
    recent_ids = []
    if conversation_id and api_key:
        try:
            from ai_agent.models import Message
            ids = list(
                Message.objects.filter(conversation_id=conversation_id)
                .order_by("-created_at")
                .values_list("pk", flat=True)[:CONTEXT_WINDOW]
            )
            recent_ids = list(ids)
        except Exception:
            pass
    retrieved = []
    if conversation_id and api_key and query_text:
        retrieved = _retrieve_relevant_old_messages(conversation_id, query_text, recent_ids, api_key)
    context_msgs = []
    if retrieved:
        summary = "--- Contexto de mensagens anteriores relevantes ---\n"
        summary += "\n".join(
            f"[{m['role'].upper()}]: {m['content'][:300]}"
            for m in retrieved
        )
        summary += "\n--- Fim do contexto ---"
        context_msgs.append({"role": "user", "content": summary})
        context_msgs.append({"role": "assistant", "content": "Entendido. Tenho esse contexto em mente."})
    return context_msgs + list(recent)


def _file_to_content_parts(file_path: str) -> list:
    path = Path(file_path)
    if not path.exists():
        return []
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    if mime and mime.startswith("image/"):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return [{"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"}}]
    if mime == "application/pdf":
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(str(path)) as pdf:
                for i, page in enumerate(pdf.pages[:10], 1):
                    text = page.extract_text() or ""
                    if text.strip():
                        text_parts.append(f"[Página {i}]\n{text}")
            if text_parts:
                return [{"type": "text", "text": "\n\n".join(text_parts)}]
        except ImportError:
            pass
        return [{"type": "text", "text": f"[Arquivo PDF: {path.name} — instale pdfplumber para extração]"}]
    if mime in ("text/csv", "application/vnd.ms-excel") or path.suffix.lower() == ".csv":
        try:
            content = path.read_text(encoding="utf-8", errors="replace")[:8000]
            return [{"type": "text", "text": f"[Conteúdo CSV — {path.name}]\n{content}"}]
        except Exception:
            pass
    if mime and mime.startswith("text/"):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")[:8000]
            return [{"type": "text", "text": f"[Arquivo: {path.name}]\n{content}"}]
        except Exception:
            pass
    return [{"type": "text", "text": f"[Arquivo não suportado: {path.name} ({mime})]"}]


def _call_openai(api_key, model, context_history, file_path=None, conversation_id=None):
    from openai import OpenAI
    from .tools import TOOL_DEFINITIONS, dispatch_tool
    client = OpenAI(api_key=api_key)
    model = model or "gpt-4o"
    messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
    if file_path:
        file_parts = _file_to_content_parts(file_path)
        if file_parts:
            for m in context_history[:-1]:
                messages.append({"role": m["role"], "content": m["content"]})
            last_msg = context_history[-1]
            messages.append({
                "role": "user",
                "content": [{"type": "text", "text": last_msg["content"]}] + file_parts,
            })
        else:
            messages += [{"role": m["role"], "content": m["content"]} for m in context_history]
    else:
        messages += [{"role": m["role"], "content": m["content"]} for m in context_history]
    for _ in range(5):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            max_tokens=1200,
            temperature=0.4,
        )
        choice = response.choices[0]
        msg = choice.message
        if choice.finish_reason == "tool_calls" and msg.tool_calls:
            messages.append(msg.model_dump(exclude_unset=True))
            for tc in msg.tool_calls:
                result = dispatch_tool(tc.function.name, tc.function.arguments)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            continue
        raw = msg.content or ""
        return _parse_llm_json(raw)
    return "Não foi possível completar a operação.", None


def _anthropic_tools():
    from .tools import TOOL_DEFINITIONS
    result = []
    for t in TOOL_DEFINITIONS:
        fn = t["function"]
        result.append({"name": fn["name"], "description": fn["description"], "input_schema": fn["parameters"]})
    return result


def _call_anthropic(api_key, model, context_history, file_path=None, conversation_id=None):
    import anthropic
    from .tools import dispatch_tool
    client = anthropic.Anthropic(api_key=api_key)
    model = model or "claude-3-5-sonnet-20241022"
    messages = []
    if file_path:
        file_parts = _file_to_content_parts(file_path)
        for m in context_history[:-1]:
            messages.append({"role": m["role"], "content": m["content"]})
        last_msg = context_history[-1]
        content = [{"type": "text", "text": last_msg["content"]}]
        for part in file_parts:
            if part["type"] == "image_url":
                url = part["image_url"]["url"]
                if url.startswith("data:"):
                    meta, b64data = url.split(",", 1)
                    mime = meta.split(";")[0].replace("data:", "")
                    content.append({"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64data}})
            else:
                content.append(part)
        messages.append({"role": "user", "content": content})
    else:
        messages = [{"role": m["role"], "content": m["content"]} for m in context_history]
    tools = _anthropic_tools()
    for _ in range(5):
        response = client.messages.create(
            model=model, max_tokens=1200, system=_SYSTEM_PROMPT, tools=tools, messages=messages,
        )
        if response.stop_reason == "tool_use":
            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})
            tool_results = []
            for block in assistant_content:
                if block.type == "tool_use":
                    result = dispatch_tool(block.name, block.input)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
            messages.append({"role": "user", "content": tool_results})
            continue
        raw = ""
        for block in response.content:
            if hasattr(block, "text"):
                raw = block.text
                break
        return _parse_llm_json(raw)
    return "Não foi possível completar a operação.", None


def _parse_llm_json(raw: str) -> tuple:
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        data = json.loads(clean.strip())
        return data.get("text") or raw, data.get("tour_name") or None
    except Exception:
        return raw, None


def get_ai_reply(
    history: list,
    conversation_id: int = None,
    file_path: str = None,
) -> tuple:
    last_msg = next((m.get("content", "") for m in reversed(history) if m.get("role") == "user"), "")
    try:
        from core.models import SystemSettings
        settings = SystemSettings.get_solo()
        api_key = (settings.ai_api_key or "").strip()
        provider = settings.ai_provider
        model = (settings.ai_model or "").strip()
    except Exception:
        return _keyword_reply(last_msg)
    if not api_key:
        return _keyword_reply(last_msg)
    context = build_context_messages(
        history=history,
        conversation_id=conversation_id,
        query_text=last_msg,
        api_key=api_key if provider == "openai" else "",
    )
    try:
        if provider == "openai":
            return _call_openai(api_key, model, context, file_path, conversation_id)
        elif provider == "anthropic":
            return _call_anthropic(api_key, model, context, file_path, conversation_id)
    except Exception as exc:
        logger.error("Erro ao chamar LLM (%s): %s", provider, exc, exc_info=True)
    return _keyword_reply(last_msg)
