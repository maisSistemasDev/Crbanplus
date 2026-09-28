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
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CONTEXT_WINDOW = 10
MAX_RETRIEVED   = 3
EMBED_MODEL_OAI = "text-embedding-3-small"

_SYSTEM_PROMPT_TEMPLATE = """Você é o assistente do CorbanPlus, sistema de gestão de correspondência bancária.

DATA E HORA ATUAL (Brasília): {now}

RESPONSABILIDADES:
- Gerenciar bancos, convênios e tabelas de comissionamento.
- Gerenciar usuários (vendedores, líderes, gerentes, administradores) e corbans (empresas).
- Gerenciar acessos bancários, equipes (grupos de comissão) e regras de comissão.
- Consultar propostas, lotes e comissões.
- Extrair dados de imagens enviadas pelo usuário (tabelas bancárias, comunicados).
- Orientar usuários sobre como usar o sistema (ofereça tours interativos quando aplicável).

ESCOPO PROIBIDO — PAGAMENTOS:
Você NUNCA executa, aprova, libera ou cria movimentações financeiras: pagamentos manuais,
saques, transações CorbanPay, alteração de release_status de comissões. Se o usuário pedir,
explique que essas operações precisam ser feitas manualmente na tela de Pagamentos por um
responsável autorizado. Você PODE apenas LISTAR comissões e propostas para consulta.

IDIOMA: Sempre responda em português brasileiro.

FERRAMENTAS: Sempre que o usuário solicitar informações ou alterações, use as ferramentas
disponíveis. Nunca invente dados — consulte o sistema. Antes de update/delete em recursos
sensíveis (usuários, corbans), confirme com o usuário caso a intenção esteja ambígua.

IDENTIFICADORES FLEXÍVEIS:
- Usuário: aceita id, CPF (com ou sem formatação) ou email.
- Corban: aceita UUID, CNPJ/CPF ou nome.
- Banco/convênio/tabela: aceita UUID ou nome (case-insensitive).

IMAGENS: Quando receber uma imagem de tabela bancária, extraia todos os dados estruturados
(taxas, faixas, datas, nome do produto) e pergunte se o usuário deseja aplicar as alterações.

ARQUIVOS (CSV/EXCEL): Quando o usuário enviar um arquivo com múltiplas tabelas para importar,
use SEMPRE a ferramenta create_tables_batch (não create_table repetido). Isso permite criar
todas as tabelas em uma única chamada, independentemente da quantidade de linhas.

TOUR: Quando a resposta envolver navegação pelo sistema, inclua "tour_name" no JSON.
Tours disponíveis: criar-grupo-comissao, aceitar-sugestao-tabela, importar-csv,
configurar-tabela, criar-vendedor.

FORMATO DE RESPOSTA: Sempre responda com JSON válido:
{{"text": "<resposta>", "tour_name": "<tour ou null>"}}
"""


def _get_system_prompt() -> str:
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
    return _SYSTEM_PROMPT_TEMPLATE.format(now=now)

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


# Palavras que indicam intenção de "como usar / onde fica / ajuda" — só
# oferecemos tour quando a mensagem é uma dúvida sobre o sistema, nunca quando
# é um comando de ação (ex.: "crie as tabelas").
_TOUR_INTENT_WORDS = (
    "como", "onde", "ajuda", "ajudar", "tutorial", "guia", "guiar",
    "passo a passo", "me mostr", "me ensin", "ensina", "ensinar",
    "não sei", "nao sei", "me guia", "tour", "navegar", "encontr", "achar",
)

# Tópico → nome do tour (deve casar com as chaves de TOURS no frontend).
# Ordem importa: do mais específico para o mais genérico.
_TOUR_TOPICS = [
    (("grupo", "equipe"), "criar-grupo-comissao"),
    (("sugest",), "aceitar-sugestao-tabela"),
    (("csv", "importar", "importação", "importacao"), "importar-csv"),
    (("vendedor",), "criar-vendedor"),
    (("tabela",), "configurar-tabela"),
]


def _detect_tour(text: str) -> Optional[str]:
    """
    Detecta, a partir da mensagem do usuário, se um tour interativo é
    pertinente. Retorna o nome do tour ou None. Exige intenção de dúvida
    ("como/onde/ajuda/...") + um tópico conhecido, para não disparar tours
    em comandos de ação.
    """
    if not text:
        return None
    lower = text.lower()
    if not any(w in lower for w in _TOUR_INTENT_WORDS):
        return None
    for keywords, tour in _TOUR_TOPICS:
        if any(kw in lower for kw in keywords):
            return tour
    return None


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


def _stamp(msg: dict) -> dict:
    """Prefixa o conteúdo da mensagem com o timestamp, se disponível."""
    ts = msg.get("created_at")
    content = msg.get("content", "")
    if ts:
        try:
            from zoneinfo import ZoneInfo
            if isinstance(ts, str):
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            else:
                dt = ts
            dt_br = dt.astimezone(ZoneInfo("America/Sao_Paulo"))
            prefix = dt_br.strftime("[%d/%m/%Y %H:%M] ")
            content = prefix + content
        except Exception:
            pass
    return {"role": msg["role"], "content": content}


def build_context_messages(history, conversation_id=None, query_text="", api_key=""):
    if len(history) <= CONTEXT_WINDOW:
        return [_stamp(m) for m in history]
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
    return context_msgs + [_stamp(m) for m in recent]


def _file_to_content_parts(file_path: str) -> list:
    path = Path(file_path)
    if not path.exists():
        return []
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    suffix = path.suffix.lower()

    # ── Imagens (limite de 4 MB antes de base64) ────────────────────────────
    if mime and mime.startswith("image/"):
        MAX_IMAGE_BYTES = 4 * 1024 * 1024
        raw = path.read_bytes()
        if len(raw) > MAX_IMAGE_BYTES:
            return [{"type": "text", "text": f"[Imagem {path.name} muito grande ({len(raw)//1024} KB) para enviar ao modelo. Redimensione e reenvie.]"}]
        b64 = base64.b64encode(raw).decode()
        return [{"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"}}]

    # ── PDF ─────────────────────────────────────────────────────────────────
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

    # ── Excel (.xlsx / .xls) ─────────────────────────────────────────────────
    if suffix in (".xlsx", ".xls") or mime in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    ):
        return _excel_to_content_parts(path)

    # ── CSV ──────────────────────────────────────────────────────────────────
    if suffix == ".csv" or mime == "text/csv":
        return _csv_to_content_parts(path)

    # ── Texto genérico ───────────────────────────────────────────────────────
    if mime and mime.startswith("text/"):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")[:8000]
            return [{"type": "text", "text": f"[Arquivo: {path.name}]\n{content}"}]
        except Exception:
            pass

    return [{"type": "text", "text": f"[Arquivo não suportado: {path.name} ({mime})]"}]


_MAX_TABLE_CHARS = 40_000  # ~400 linhas típicas dentro do contexto do LLM


def _csv_to_content_parts(path: Path) -> list:
    """Envia header + todas as linhas que caibam em _MAX_TABLE_CHARS."""
    import csv
    import io
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        total = max(len(rows) - 1, 0)  # desconta header
        header = rows[:1]
        data_rows = rows[1:]
        # Adiciona linhas enquanto o buffer não ultrapassar o limite
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(header)
        included = 0
        for row in data_rows:
            writer.writerow(row)
            included += 1
            if output.tell() >= _MAX_TABLE_CHARS:
                break
        truncated = included < total
        note = (
            f"[CSV: {path.name} — {total} linhas no total"
            + (f", exibindo as primeiras {included} (limite de caracteres atingido)" if truncated else "")
            + "]\n"
        )
        return [{"type": "text", "text": note + output.getvalue()}]
    except Exception as exc:
        return [{"type": "text", "text": f"[Erro ao ler CSV {path.name}: {exc}]"}]


def _excel_to_content_parts(path: Path) -> list:
    """Lê cada aba do Excel e envia todas as linhas que caibam em _MAX_TABLE_CHARS."""
    try:
        import openpyxl
    except ImportError:
        return [{"type": "text", "text": f"[Arquivo Excel {path.name} — instale openpyxl para leitura: pip install openpyxl]"}]

    import csv, io
    try:
        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        parts: list[str] = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            all_rows = list(ws.iter_rows(values_only=True))
            if not all_rows:
                continue
            total_data = len(all_rows) - 1  # descontar header
            output = io.StringIO()
            writer = csv.writer(output)
            included = 0
            for i, row in enumerate(all_rows):
                writer.writerow([(v if v is not None else "") for v in row])
                if i > 0:  # não conta header
                    included += 1
                if i > 0 and output.tell() >= _MAX_TABLE_CHARS:
                    break
            truncated = included < total_data
            note = (
                f"[Aba: {sheet_name} — {ws.max_column} colunas, "
                f"{max(total_data, 0)} linhas de dados"
                + (f"; exibindo as primeiras {included} (limite atingido)" if truncated else "")
                + "]\n"
            )
            parts.append(note + output.getvalue())
        wb.close()
        if parts:
            return [{"type": "text", "text": f"[Excel: {path.name}]\n\n" + "\n\n".join(parts)}]
        return [{"type": "text", "text": f"[Excel {path.name} está vazio ou sem dados legíveis]"}]
    except Exception as exc:
        return [{"type": "text", "text": f"[Erro ao ler Excel {path.name}: {exc}]"}]



def _call_openai(api_key, model, context_history, file_path=None, conversation_id=None):
    from openai import OpenAI
    from .tools import TOOL_DEFINITIONS, dispatch_tool
    client = OpenAI(api_key=api_key)
    model = model or "gpt-4o"
    messages = [{"role": "system", "content": _get_system_prompt()}]
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
    tool_results: list = []
    for _ in range(10):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            # 4000 para comportar tool-calls grandes (ex.: create_tables_batch
            # com muitas tabelas). Com 1200, os argumentos eram truncados
            # (finish_reason="length") e nenhuma tabela era criada.
            max_tokens=4000,
            temperature=0.4,
        )
        choice = response.choices[0]
        msg = choice.message
        if choice.finish_reason == "tool_calls" and msg.tool_calls:
            messages.append(msg.model_dump(exclude_unset=True))
            for tc in msg.tool_calls:
                result = dispatch_tool(tc.function.name, tc.function.arguments)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
                tool_results.append(result)
            continue
        raw = msg.content or ""
        # O LLM nunca deve deixar o usuário sem resposta ("parou"): se não
        # retornou texto, resume as ferramentas executadas ou usa um fallback.
        if not raw.strip():
            if tool_results:
                return _summarize_tool_results(tool_results), None, True
            return "Desculpe, não consegui gerar uma resposta. Pode reformular?", None, False
        text, tour = _parse_llm_json(raw)
        return text, tour, bool(tool_results)
    # Estourou o limite de iterações: ainda assim resume o que foi feito.
    if tool_results:
        return _summarize_tool_results(tool_results), None, True
    return "Não foi possível completar a operação.", None, False


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
    executed_results: list = []
    for _ in range(10):
        response = client.messages.create(
            model=model, max_tokens=4000, system=_get_system_prompt(), tools=tools, messages=messages,
        )
        if response.stop_reason == "tool_use":
            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})
            tool_results = []
            for block in assistant_content:
                if block.type == "tool_use":
                    result = dispatch_tool(block.name, block.input)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
                    executed_results.append(result)
            messages.append({"role": "user", "content": tool_results})
            continue
        raw = ""
        for block in response.content:
            if hasattr(block, "text"):
                raw = block.text
                break
        # O LLM nunca deve deixar o usuário sem resposta ("parou"): se não
        # retornou texto, resume as ferramentas executadas ou usa um fallback.
        if not raw.strip():
            if executed_results:
                return _summarize_tool_results(executed_results), None, True
            return "Desculpe, não consegui gerar uma resposta. Pode reformular?", None, False
        text, tour = _parse_llm_json(raw)
        return text, tour, bool(executed_results)
    if executed_results:
        return _summarize_tool_results(executed_results), None, True
    return "Não foi possível completar a operação.", None, False


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


def _summarize_tool_results(tool_results: list) -> str:
    """
    Gera uma mensagem de resumo a partir dos resultados das ferramentas
    executadas, usada quando o LLM não retorna texto após os tool-calls
    (caso contrário o usuário ficaria sem nenhuma resposta).
    """
    created = 0
    errors = 0
    error_msgs: list[str] = []
    for result_str in tool_results:
        try:
            data = json.loads(result_str) if isinstance(result_str, str) else result_str
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if "created_count" in data:
            created += data.get("created_count", 0) or 0
            errors += data.get("error_count", 0) or 0
            for err in (data.get("errors") or [])[:3]:
                error_msgs.append(err.get("error", str(err)) if isinstance(err, dict) else str(err))
        elif data.get("success") and "table" in data:
            created += 1
        elif data.get("error"):
            errors += 1
            error_msgs.append(str(data["error"]))

    if created or errors:
        parts = []
        if created:
            parts.append(f"Pronto! **{created}** tabela(s) criada(s) com sucesso.")
        if errors:
            parts.append(f"**{errors}** não puderam ser criada(s).")
            if error_msgs:
                parts.append("Detalhes: " + "; ".join(error_msgs[:3]))
        return " ".join(parts)
    return "Operação concluída com sucesso."


def get_ai_reply(
    history: list,
    conversation_id: int = None,
    file_path: str = None,
    file_context_text: str = None,
) -> tuple:
    last_msg = next((m.get("content", "") for m in reversed(history) if m.get("role") == "user"), "")
    try:
        from core.models import SystemSettings
        settings = SystemSettings.get_solo()
        api_key = (settings.ai_api_key or "").strip()
        provider = settings.ai_provider
        model = (settings.ai_model or "").strip()
    except Exception:
        text, tour = _keyword_reply(last_msg)
        return text, tour, False
    if not api_key:
        text, tour = _keyword_reply(last_msg)
        return text, tour, False
    context = build_context_messages(
        history=history,
        conversation_id=conversation_id,
        query_text=last_msg,
        api_key=api_key if provider == "openai" else "",
    )
    if file_context_text:
        context = context + [
            {"role": "user", "content": file_context_text},
            {"role": "assistant", "content": "Entendido. Tenho o conteúdo do arquivo anexado disponível para consulta."},
        ]
    try:
        if provider == "openai":
            reply_text, tour_name, file_task_done = _call_openai(api_key, model, context, file_path, conversation_id)
        elif provider == "anthropic":
            reply_text, tour_name, file_task_done = _call_anthropic(api_key, model, context, file_path, conversation_id)
        else:
            text, tour = _keyword_reply(last_msg)
            return text, tour, False
        # Detecção server-side: se o LLM não indicou um tour, inferimos a partir
        # da intenção da pergunta (mais confiável que depender do JSON do LLM).
        if not tour_name:
            tour_name = _detect_tour(last_msg)
        return reply_text, tour_name, file_task_done
    except Exception as exc:
        logger.error("Erro ao chamar LLM (%s): %s", provider, exc, exc_info=True)
    text, tour = _keyword_reply(last_msg)
    return text, tour, False


# ─── Processamento de chunk de arquivo grande ─────────────────────────────────

_CHUNK_SYSTEM_PROMPT = (
    "Você é um processador de tabelas de comissionamento bancário.\n"
    "Sua única tarefa: receber um trecho de planilha CSV e criar TODAS as tabelas "
    "usando a ferramenta create_tables_batch em UMA única chamada.\n\n"
    "REGRA IMPORTANTE: Se o campo que parece ser o nome da tabela estiver no formato "
    "'BANCO - CONVENIO - NOME_TABELA' (numa única coluna), separe corretamente:\n"
    "  • bank_id    = tudo antes do primeiro ' - '\n"
    "  • agreement_id = o segmento entre o primeiro e o segundo ' - '\n"
    "  • name_in_bank = tudo depois do segundo ' - '\n\n"
    "Inclua TODAS as linhas do trecho na chamada. Não responda com texto — use a ferramenta."
)


def process_chunk_with_llm(
    chunk_content: str,
    api_key: str,
    provider: str,
    model: str | None,
) -> dict:
    """
    Envia um chunk CSV ao LLM e força o uso de create_tables_batch.
    Retorna o dict de resultado da ferramenta: {created_count, error_count, ...}.
    """
    import json as _json
    from .tools import TOOL_DEFINITIONS, dispatch_tool

    # Expõe apenas create_tables_batch para economizar tokens e forçar o uso
    chunk_tools = [t for t in TOOL_DEFINITIONS if t["function"]["name"] == "create_tables_batch"]
    if not chunk_tools:
        chunk_tools = TOOL_DEFINITIONS

    user_msg = f"Crie tabelas para este trecho de planilha:\n\n{chunk_content}"

    if provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        messages = [
            {"role": "system", "content": _CHUNK_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
        for _ in range(5):
            response = client.chat.completions.create(
                model=model or "gpt-4o",
                messages=messages,
                tools=chunk_tools,
                tool_choice="required",
                max_tokens=4000,
                temperature=0,
            )
            choice = response.choices[0]
            msg = choice.message
            if choice.finish_reason == "tool_calls" and msg.tool_calls:
                messages.append(msg.model_dump(exclude_unset=True))
                last_result: dict | None = None
                for tc in msg.tool_calls:
                    result_str = dispatch_tool(tc.function.name, tc.function.arguments)
                    last_result = _json.loads(result_str)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_str})
                if last_result is not None:
                    return last_result
                continue
            break
        return {"created_count": 0, "error_count": 0, "error": "LLM não usou a ferramenta"}

    elif provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        ant_tools = [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "input_schema": t["function"]["parameters"],
            }
            for t in chunk_tools
        ]
        messages: list = [{"role": "user", "content": user_msg}]
        for _ in range(5):
            response = client.messages.create(
                model=model or "claude-3-5-sonnet-20241022",
                max_tokens=4000,
                system=_CHUNK_SYSTEM_PROMPT,
                tools=ant_tools,
                tool_choice={"type": "any"},
                messages=messages,
            )
            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                last_result = None
                for block in response.content:
                    if block.type == "tool_use":
                        result_str = dispatch_tool(block.name, block.input)
                        last_result = _json.loads(result_str)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        })
                messages.append({"role": "user", "content": tool_results})
                if last_result is not None:
                    return last_result
                continue
            break
        return {"created_count": 0, "error_count": 0, "error": "LLM não usou a ferramenta"}

    return {"created_count": 0, "error_count": 0, "error": f"Provider desconhecido: {provider}"}
