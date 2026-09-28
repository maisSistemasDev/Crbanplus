"""
Utilitários de chunking de arquivos tabulares (CSV, Excel).

Estratégia:
  - Chunk alvo: MAX_CHUNK_CHARS caracteres OU MAX_ROWS_PER_CHUNK linhas, o que vier primeiro.
  - Cada chunk inclui o cabeçalho para que o LLM entenda o contexto da linha.
  - Arquivos com >= LARGE_FILE_THRESHOLD linhas de dados são considerados "grandes"
    e ativam o fluxo de processamento assíncrono por chunks.
"""
import csv
import io
import logging
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

# ─── Configuração ─────────────────────────────────────────────────────────────

MAX_CHUNK_CHARS    = 2_000   # ~10-20 linhas típicas
MAX_ROWS_PER_CHUNK = 10      # teto fixo de linhas por chunk
LARGE_FILE_THRESHOLD = 50    # a partir daqui entra no fluxo assíncrono

# Campos de Table que podem ser mapeados a partir de colunas de arquivo
TABLE_FIELDS = [
    {"name": "bank_id",         "verbose_name": "banco",              "type": "text",   "required": True},
    {"name": "agreement_id",    "verbose_name": "convenio",           "type": "text",   "required": True},
    {"name": "name_in_bank",    "verbose_name": "nome tabela banco",  "type": "text",   "required": False},
    {"name": "commission_rate", "verbose_name": "taxa comissao",      "type": "number", "required": False},
    {"name": "vigency_date",    "verbose_name": "data vigencia",      "type": "date",   "required": False},
    {"name": "min_value",       "verbose_name": "valor minimo",       "type": "number", "required": False},
    {"name": "max_value",       "verbose_name": "valor maximo",       "type": "number", "required": False},
]

# ─── Leitura de arquivo ───────────────────────────────────────────────────────

def read_tabular_file(file_path: str) -> tuple[list[str], list[list], str]:
    """
    Lê um CSV ou Excel e retorna (header, data_rows, sheet_name).
    Para Excel multi-aba, usa a aba ativa (primeira).
    Raises FileNotFoundError se o arquivo não existir.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        text = path.read_text(encoding="utf-8", errors="replace")
        rows = list(csv.reader(io.StringIO(text)))
        if not rows:
            return [], [], "csv"
        return [str(c) for c in rows[0]], rows[1:], "csv"

    if suffix in (".xlsx", ".xls"):
        try:
            import openpyxl
        except ImportError as exc:
            raise ImportError("openpyxl não instalado: pip install openpyxl") from exc

        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        ws = wb.active
        sheet_name = ws.title or "sheet1"
        all_rows = [
            [(str(v) if v is not None else "") for v in row]
            for row in ws.iter_rows(values_only=True)
        ]
        wb.close()
        if not all_rows:
            return [], [], sheet_name
        return all_rows[0], all_rows[1:], sheet_name

    raise ValueError(f"Tipo de arquivo não suportado para chunking: {suffix}")


def is_large_file(file_path: str, threshold: int = LARGE_FILE_THRESHOLD) -> bool:
    """Retorna True se o arquivo tem >= threshold linhas de dados."""
    try:
        _, rows, _ = read_tabular_file(file_path)
        return len(rows) >= threshold
    except Exception:
        return False


# ─── Chunking ─────────────────────────────────────────────────────────────────

def _row_to_csv_str(row: list) -> str:
    """Converte uma lista de valores para string CSV de uma linha."""
    out = io.StringIO()
    csv.writer(out).writerow(row)
    return out.getvalue().rstrip("\r\n")


def iter_chunks(
    data_rows: list[list],
    header: list[str],
    max_chars: int = MAX_CHUNK_CHARS,
    max_rows: int = MAX_ROWS_PER_CHUNK,
) -> Iterator[tuple[int, int, int, str]]:
    """
    Gera tuples (chunk_index, row_start, row_end, content) para cada chunk.
    row_start e row_end são 1-indexed relativos às linhas de dados (sem header).
    content é uma string CSV com header + linhas do chunk.
    """
    header_str = _row_to_csv_str(header)
    chunk_rows: list[str] = []
    chunk_chars = 0
    chunk_idx = 0
    row_start = 1

    for i, row in enumerate(data_rows, start=1):
        row_str = _row_to_csv_str(row)
        # Fecha chunk atual se atingiu o limite
        if chunk_rows and (len(chunk_rows) >= max_rows or chunk_chars + len(row_str) > max_chars):
            content = header_str + "\n" + "\n".join(chunk_rows)
            yield chunk_idx, row_start, row_start + len(chunk_rows) - 1, content
            chunk_idx += 1
            row_start = i
            chunk_rows = []
            chunk_chars = 0

        chunk_rows.append(row_str)
        chunk_chars += len(row_str)

    # Último chunk
    if chunk_rows:
        content = header_str + "\n" + "\n".join(chunk_rows)
        yield chunk_idx, row_start, row_start + len(chunk_rows) - 1, content


def chunk_file(file_path: str) -> Iterator[tuple[int, int, int, str]]:
    """Atalho: lê o arquivo e delega para iter_chunks."""
    header, rows, _ = read_tabular_file(file_path)
    yield from iter_chunks(rows, header)


# ─── Mapeamento de colunas ────────────────────────────────────────────────────

def detect_column_mapping_llm(
    header: list[str],
    sample_rows: list[list],
    api_key: str,
    provider: str,
    model: str | None,
) -> dict[str, int | None]:
    """
    Chama o LLM UMA VEZ com header + amostra para descobrir o mapeamento
    coluna→campo de Table.
    Retorna dict {"bank_id": col_idx_ou_None, ...}.
    """
    import json as _json

    col_list = "\n".join(f"  [{i}]: {h}" for i, h in enumerate(header))
    sample_text = "\n".join(_row_to_csv_str(r) for r in sample_rows[:5])
    field_list = "\n".join(
        f"  - {f['name']}: {f['verbose_name']} (required={f['required']})"
        for f in TABLE_FIELDS
    )
    prompt = (
        "Você é um assistente que mapeia colunas de planilha para campos de tabela bancária.\n\n"
        f"Colunas disponíveis:\n{col_list}\n\n"
        f"Amostra de dados:\n{sample_text}\n\n"
        f"Campos do sistema:\n{field_list}\n\n"
        "Retorne APENAS um JSON válido no formato:\n"
        '{"bank_id": N_ou_null, "agreement_id": N_ou_null, "name_in_bank": N_ou_null, '
        '"commission_rate": N_ou_null, "vigency_date": N_ou_null, '
        '"min_value": N_ou_null, "max_value": N_ou_null}\n'
        "onde N é o índice (0-based) da coluna correspondente, ou null se não encontrada."
    )

    raw = ""
    try:
        if provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=model or "gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0,
            )
            raw = resp.choices[0].message.content or ""
        else:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            resp = client.messages.create(
                model=model or "claude-3-5-sonnet-20241022",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text if resp.content else ""

        clean = raw.strip()
        if "```" in clean:
            parts = clean.split("```")
            clean = parts[1] if len(parts) > 1 else parts[0]
            if clean.startswith("json"):
                clean = clean[4:]
        mapping = _json.loads(clean.strip())
        # Valida: valores devem ser int ou None
        return {k: (int(v) if v is not None else None) for k, v in mapping.items()}
    except Exception as exc:
        logger.warning("detect_column_mapping_llm falhou: %s | raw=%r", exc, raw)
        return _fallback_column_mapping(header)


def _fallback_column_mapping(header: list[str]) -> dict[str, int | None]:
    """Heurística de fallback: mesmo algoritmo do AiSuggestMappingView."""
    import unicodedata, re

    def normalize(s: str) -> str:
        s = s.lower().strip()
        s = unicodedata.normalize("NFD", s)
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        s = re.sub(r"[^a-z0-9]", "_", s)
        return re.sub(r"_+", "_", s).strip("_")

    cols = [(i, normalize(h)) for i, h in enumerate(header)]
    mapping: dict[str, int | None] = {}
    used: set[int] = set()

    for field in TABLE_FIELDS:
        fn = normalize(field["name"])
        fv = normalize(field["verbose_name"])
        best_idx, best_score = None, 0
        for idx, cn in cols:
            if idx in used:
                continue
            score = 0
            if cn == fn or cn == fv:
                score = 100
            elif cn in fv or fv in cn or cn in fn or fn in cn:
                score = 70
            else:
                fw = set(fv.split("_"))
                cw = set(cn.split("_"))
                overlap = len(fw & cw - {"de", "da", "do"})
                if overlap:
                    score = 30 + overlap * 10
            if score > best_score:
                best_score, best_idx = score, idx
        if best_idx is not None and best_score >= 30:
            used.add(best_idx)
            mapping[field["name"]] = best_idx
        else:
            mapping[field["name"]] = None

    return mapping


def _split_compound_name(value: str) -> tuple[str, str | None, str | None]:
    """
    Detecta e divide nomes compostos no formato 'BANCO - CONVENIO - NOME_TABELA'.
    Ex: 'PRESENCA BANK - INSS - 8376 Pacote ...' → ('PRESENCA BANK', 'INSS', '8376 Pacote ...')
    Retorna (bank_name, agreement_name_or_None, table_name_or_None).
    """
    parts = [p.strip() for p in value.split(" - ", 2)]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1], None
    return value, None, None


def apply_mapping_to_rows(
    rows: list[list],
    mapping: dict[str, int | None],
) -> list[dict]:
    """
    Aplica o mapeamento de colunas a uma lista de linhas e retorna
    lista de dicts prontos para tool_create_tables_batch.

    Se o valor de bank_id contiver o padrão 'BANCO - CONVENIO - NOME',
    os campos são extraídos automaticamente (common em planilhas de comissionamento).
    """
    result = []
    for row in rows:
        entry: dict = {}
        for field_name, col_idx in mapping.items():
            if col_idx is None:
                continue
            try:
                val = row[col_idx]
            except IndexError:
                continue
            if val == "" or val is None:
                continue
            entry[field_name] = str(val).strip()

        # Detecta nome composto no bank_id ("BANCO - CONVENIO - NOME_TABELA").
        # Isso ocorre quando a planilha tem uma única coluna com a descrição completa.
        bank_val = entry.get("bank_id", "")
        if bank_val and " - " in bank_val:
            bank_part, agreement_part, table_part = _split_compound_name(bank_val)
            entry["bank_id"] = bank_part
            if agreement_part and not entry.get("agreement_id"):
                entry["agreement_id"] = agreement_part
            if table_part and not entry.get("name_in_bank"):
                entry["name_in_bank"] = table_part

        # Mesma lógica para agreement_id caso carregue o nome composto também
        agreement_val = entry.get("agreement_id", "")
        if agreement_val and " - " in agreement_val:
            # Provavelmente é o mesmo campo composto; extrai apenas a parte do convênio
            entry["agreement_id"] = agreement_val.split(" - ", 1)[0].strip()

        # Só inclui linhas que tenham pelo menos banco e convênio
        if entry.get("bank_id") and entry.get("agreement_id"):
            result.append(entry)
    return result


def parse_chunk_to_table_dicts(
    chunk_content: str,
    mapping: dict[str, int | None],
) -> list[dict]:
    """
    Lê o conteúdo CSV de um chunk (com header) e aplica o mapping.
    Descarta a primeira linha (header).
    """
    reader = csv.reader(io.StringIO(chunk_content))
    rows = list(reader)
    data_rows = rows[1:]  # skip header
    return apply_mapping_to_rows(data_rows, mapping)
