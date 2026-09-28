import re
import logging
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import locale
from .models import LayoutField, Proposal, Layout, Bank, Agreement, Table
from bank_access.models import BankAccess
from django.db import models

logger = logging.getLogger(__name__)

# Configuração do locale para formatação monetária (Brasil)
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

_BR_DATE_FORMATS = (
    '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
    '%d/%m/%y', '%d-%m-%y', '%d.%m.%y',
    '%Y-%m-%d', '%Y/%m/%d',
    '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M',
    '%d-%m-%Y %H:%M:%S', '%d-%m-%Y %H:%M',
    '%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M',
    '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
    '%Y-%m-%d %H:%M:%S.%f',
    '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f',
)

_FILE_AS_TEXT = dict(dtype=str, keep_default_na=False)


def parse_brazilian_datetime(value) -> datetime | None:
    """Interpreta data/hora no padrão brasileiro (dia/mês/ano). Evita o swap MM/DD do pandas."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.to_pydatetime().replace(tzinfo=None)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    try:
        if pd.isna(value):
            return None
    except (ValueError, TypeError):
        pass
    if hasattr(value, 'dtype') and 'datetime' in str(getattr(value, 'dtype', '')):
        parsed = pd.Timestamp(value)
        if pd.isna(parsed):
            return None
        return parsed.to_pydatetime().replace(tzinfo=None)

    if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool):
        numeric = float(value)
        if 631152000 <= numeric <= 2524608000:
            try:
                return datetime.fromtimestamp(numeric)
            except (ValueError, OSError, OverflowError):
                pass
        if 30000 <= numeric <= 73000:
            try:
                return datetime(1899, 12, 30) + timedelta(days=int(numeric))
            except (ValueError, OverflowError):
                pass

    text = str(value).strip()
    if not text or text.lower() in {'nan', 'none', 'nat', 'null', ''}:
        return None
    if text.endswith('Z'):
        text = text[:-1]
    if len(text) > 10:
        text = re.split(r'[+-]\d{2}:?\d{2}$', text)[0]

    if re.fullmatch(r'\d{4,5}(?:\.0+)?', text):
        numeric = float(text)
        if 30000 <= numeric <= 73000:
            return datetime(1899, 12, 30) + timedelta(days=int(numeric))

    for fmt in _BR_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass

    parsed = pd.to_datetime(text, dayfirst=True, errors='coerce')
    if pd.notna(parsed):
        return parsed.to_pydatetime().replace(tzinfo=None)
    raise ValueError(f"Formato de data não reconhecido: {value!r}")


def parse_brazilian_date(value) -> date | None:
    parsed = parse_brazilian_datetime(value)
    return parsed.date() if parsed else None


def parse_loose_decimal(value: str) -> float:
    """Converte string monetária/decimal PT-BR, US ou '3.062.83' (ponto milhar + decimal)."""
    text = re.sub(r'[^\d,.\-]', '', str(value).strip())
    if not text or text in {'.', ',', '-', '-.', '-,'}:
        raise ValueError(f'Valor numérico vazio: {value!r}')
    negative = text.startswith('-')
    text = text.lstrip('-')
    if ',' in text and '.' in text:
        if text.rfind(',') > text.rfind('.'):
            text = text.replace('.', '').replace(',', '.')
        else:
            text = text.replace(',', '')
    elif text.count('.') > 1:
        parts = text.split('.')
        if len(parts[-1]) in (1, 2):
            text = ''.join(parts[:-1]) + '.' + parts[-1]
        else:
            text = text.replace('.', '')
    elif text.count(',') > 1:
        parts = text.split(',')
        if len(parts[-1]) in (1, 2):
            text = ''.join(parts[:-1]) + '.' + parts[-1]
        else:
            text = text.replace(',', '')
    else:
        text = text.replace(',', '.')
    number = float(text)
    return -number if negative else number


def detect_file_type(file_path):
    """
    Detecta o tipo de arquivo com base na extensão.
    """
    file_path = file_path.lower()
    if file_path.endswith('.csv'):
        return 'csv'
    elif file_path.endswith('.xls'):
        return 'xls'
    elif file_path.endswith('.xlsx'):
        return 'xlsx'
    else:
        raise ValueError(f"Formato de arquivo não suportado: {file_path}")


def read_file_columns(file_path, sheet_name=None, has_header=True, skip_rows=0, sample_rows=5):
    """
    Lê as colunas de um arquivo (CSV, XLS, XLSX).
    Retorna um dicionário com nomes das colunas, seus índices e tipos detectados.
    """
    file_type = detect_file_type(file_path)
    
    try:
        # Leitura do cabeçalho e algumas linhas para amostra
        if file_type == 'csv':
            df = pd.read_csv(
                file_path,
                nrows=sample_rows + skip_rows,
                encoding='utf-8',
                sep=None,
                engine='python',
                **_FILE_AS_TEXT,
            )
            if not has_header:
                df.columns = [f'Coluna {i+1}' for i in range(len(df.columns))]
        else:  # Excel (xls ou xlsx)
            if sheet_name:
                df = pd.read_excel(
                    file_path, sheet_name=sheet_name, nrows=sample_rows + skip_rows, **_FILE_AS_TEXT
                )
            else:
                df = pd.read_excel(file_path, nrows=sample_rows + skip_rows, **_FILE_AS_TEXT)
            
            if not has_header:
                df.columns = [f'Coluna {i+1}' for i in range(len(df.columns))]
        
        if skip_rows > 0:
            df = df.iloc[skip_rows:]
            df = df.reset_index(drop=True)
        
        # Extrair colunas e amostras
        columns = []
        for i, col_name in enumerate(df.columns):
            sample_data = df[col_name].iloc[0] if not df.empty and not df[col_name].isna().all() else None
            detected_type = detect_column_type(df[col_name])
            
            columns.append({
                'column_name': str(col_name),
                'column_index': i,
                'detected_type': detected_type,
                'sample_data': str(sample_data) if sample_data is not None else None
            })
        
        return columns
    
    except Exception as e:
        raise ValueError(f"Erro ao ler o arquivo: {str(e)}")


def detect_column_type(series: pd.Series):
    """
    Detecta o tipo de dados de uma coluna do DataFrame.
    """
    # Remove linhas com valores NaN
    series = series.dropna()
    logger.debug(series)
    if series.empty:
        return LayoutField.DATATYPE_TEXT
    
    # Verifica se a coluna contém apenas números inteiros
    if series.apply(lambda x: is_integer(x)).all():
        return LayoutField.DATATYPE_NUMBER
    
    # Verifica se a coluna contém valores monetários
    if series.apply(lambda x: is_currency(x)).all():
        return LayoutField.DATATYPE_CURRENCY
    
    # Verifica se a coluna contém valores decimais
    if series.apply(lambda x: is_decimal(x)).all():
        return LayoutField.DATATYPE_DECIMAL
    
    # Verifica se a coluna contém datas e horas
    if series.apply(lambda x: is_datetime(x)).all():
        return LayoutField.DATATYPE_DATETIME
    
    # Verifica se a coluna contém apenas datas
    if series.apply(lambda x: is_date(x)).all():
        return LayoutField.DATATYPE_DATE
    
    # Verifica se a coluna contém CPFs
    if series.apply(lambda x: is_cpf(x)).all():
        return LayoutField.DATATYPE_CPF
    
    
    # Se nenhum tipo específico for detectado, retorna texto
    return LayoutField.DATATYPE_TEXT


def is_integer(value):
    """Verifica se o valor é um número inteiro."""
    if isinstance(value, (int, np.integer)):
        return True
    
    if isinstance(value, str):
        value = value.strip()
        if value and re.match(r'^-?\d+$', value):
            return True
    
    return False


def is_decimal(value):
    """Verifica se o valor é um número decimal."""
    if isinstance(value, (float, np.float64)):
        return True
    
    if isinstance(value, str):
        value = value.strip().replace(',', '.')
        try:
            float(value)
            return '.' in value or ',' in value
        except ValueError:
            pass
    
    return False


def is_currency(value):
    """Verifica se o valor é um valor monetário (R$ X,XX)."""
    if isinstance(value, str):
        # Padrões comuns de moeda no Brasil: R$ 1.234,56 ou 1.234,56
        return bool(re.match(r'^(R\$\s*)?(\d{1,3}(\.\d{3})*|\d+)(,\d{2})?$', value.strip()))
    
    return False


def is_date(value):
    """Verifica se o valor é uma data."""
    if isinstance(value, (datetime, pd.Timestamp)):
        return True
    
    if isinstance(value, str):
        # Tenta converter para data nos formatos comuns no Brasil
        date_formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
            '%d/%m/%y', '%d-%m-%y', '%d.%m.%y'
        ]
        
        for date_format in date_formats:
            try:
                datetime.strptime(value.strip(), date_format)
                return True
            except ValueError:
                continue
    
    return False


def is_datetime(value):
    """Verifica se o valor é uma data e hora."""
    if isinstance(value, (datetime, pd.Timestamp)):
        return True
    
    if isinstance(value, str):
        # Tenta converter para data e hora nos formatos comuns no Brasil
        datetime_formats = [
            '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M',
            '%d-%m-%Y %H:%M:%S', '%d-%m-%Y %H:%M',
            '%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M',
            '%d/%m/%Y %H:%M:%S.%f', '%d-%m-%Y %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
            '%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M',
            '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M',
            '%Y%m%d %H:%M:%S', '%Y%m%d %H:%M',
            '%Y%m%dT%H:%M:%S', '%Y%m%dT%H:%M',

        ]
        for datetime_format in datetime_formats:
            try:
                datetime.strptime(value.strip(), datetime_format)
                return True
            except ValueError:
                continue
    
    return False


def is_cpf(value):
    """Verifica se o valor é um CPF válido."""
    if isinstance(value, str):
        # Remove caracteres não numéricos
        cpf = re.sub(r'[^\d]', '', value)
        
        # CPF deve ter 11 dígitos
        if len(cpf) != 11:
            return False
        
        # Verificar se todos os dígitos são iguais (CPF inválido)
        if len(set(cpf)) == 1:
            return False

        # Validação do primeiro dígito verificador:
        sum_of_products = sum(int(a)*b for a, b in zip(cpf[0:9], range(10, 1, -1)))
        expected_digit = (sum_of_products * 10 % 11) % 10
        if int(cpf[9]) != expected_digit:
            return False

        # Validação do segundo dígito verificador:
        sum_of_products = sum(int(a)*b for a, b in zip(cpf[0:10], range(11, 1, -1)))
        expected_digit = (sum_of_products * 10 % 11) % 10
        if int(cpf[10]) != expected_digit:
            return False

        # O padrão básico de CPF é: xxx.xxx.xxx-xx ou xxxxxxxxxxx
        return bool(re.match(r'^\d{3}[\.]?\d{3}[\.]?\d{3}[-]?\d{2}$', value.strip()))
    
        
    return False


def is_boolean(value):
    """Verifica se o valor é booleano."""
    if isinstance(value, (bool, np.bool_)):
        return True
    
    if isinstance(value, (int, np.integer)):
        return value in (0, 1)
    
    if isinstance(value, str):
        value = value.strip().lower()
        return value in ('sim', 'não', 'nao', 's', 'n', 'true', 'false', 't', 'f', 'verdadeiro', 'falso', '1', '0')
    
    return False


def convert_value(value, data_type):
    """
    Converte um valor para o tipo especificado.
    """
    # Verificações iniciais para valores nulos/inválidos
    if value is None:
        return None
    
    if pd.isna(value):
        return None
        
    if isinstance(value, str):
        value_stripped = value.strip()
        if not value_stripped or value_stripped.lower() in ('nan', 'null', 'none', ''):
            return None
        # Usa o valor original para processamento posterior se não for vazio
        value = value_stripped
    
    # Verificação adicional para timestamps que podem ter escapado da limpeza
    if isinstance(value, (pd.Timestamp, datetime)) and data_type not in [LayoutField.DATATYPE_DATE, LayoutField.DATATYPE_DATETIME]:
        # Se não for um campo de data/datetime, converte para string
        try:
            value = value.isoformat()
        except Exception:
            value = str(value)
    elif hasattr(value, 'timestamp') and not isinstance(value, str) and data_type not in [LayoutField.DATATYPE_DATE, LayoutField.DATATYPE_DATETIME]:
        # Verifica se tem método timestamp (objetos datetime-like)
        try:
            value = value.isoformat()
        except Exception:
            value = str(value)
    
    try:
        if data_type == LayoutField.DATATYPE_TEXT:
            return str(value).strip()
        
        elif data_type == LayoutField.DATATYPE_NUMBER:
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return None
                return int(value)
            return int(value)
        
        elif data_type == LayoutField.DATATYPE_DECIMAL:
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return None
                return parse_loose_decimal(value)
            return float(value)
        
        elif data_type == LayoutField.DATATYPE_CURRENCY:
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return None
                return parse_loose_decimal(value)
            return float(value)
        
        elif data_type == LayoutField.DATATYPE_DATE:
            return parse_brazilian_date(value)

        elif data_type == LayoutField.DATATYPE_DATETIME:
            return parse_brazilian_datetime(value)

        elif data_type == LayoutField.DATATYPE_CPF:
            cpf = re.sub(r'[^\d]', '', str(value).strip())
            if len(cpf) > 11:
                raise ValueError(f"CPF inválido: {value}")
            
            if len(cpf) < 11:
                left_zeros = '0' * (11 - len(cpf))
                cpf = left_zeros + cpf
            
            return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
            
           
        elif data_type == LayoutField.DATATYPE_BOOLEAN:
            if isinstance(value, (bool, np.bool_)):
                return value
            
            if isinstance(value, (int, np.integer)):
                return bool(value)
            
            if isinstance(value, str):
                value = value.strip().lower()
                return value in ('sim', 's', 'true', 't', 'verdadeiro', '1')
        
        elif data_type == LayoutField.DATATYPE_EMAIL:
            if isinstance(value, str):
                return extract_first_email(value)
            
            return None
        
        elif data_type == LayoutField.DATATYPE_PHONE:
            if isinstance(value, str):
                phone = re.sub(r'[^\d]', '', value.strip())
                if len(phone) == 11:
                    return f"({phone[:2]}) {phone[2:7]}-{phone[7:]}"
                elif len(phone) == 10:
                    return f"({phone[:2]}) {phone[2:6]}-{phone[6:]}"
                else:
                    raise ValueError(f"Telefone inválido: {value}")
            
            return None
        
        # Se nenhuma conversão for aplicada, retorna o valor original
        return value
    
    except Exception as e:
        # Debug: adicionar informações sobre o tipo do valor que causou erro
        error_msg = f"Erro ao converter valor '{value}' (tipo: {type(value)}) para o tipo {data_type}: {str(e)}"
        logger.debug(f"DEBUG convert_value: {error_msg}")
        raise ValueError(error_msg)


def get_required_fields(exclude_fields=[]):
    """
    Obtém os campos obrigatórios do modelo Proposal diretamente da classe.
    Retorna uma lista com os nomes dos campos obrigatórios.
    """
    required_fields = []
    
    for field in Proposal._meta.get_fields():
        # Ignora campos como ManyToOneRel, ManyToManyRel, etc.
        if not hasattr(field, 'blank'):
            continue
            
        # Verifica se o campo é obrigatório - se não for blank e não for null
        if not field.blank and not field.null:
            # Ignora campos com valores default ou auto-gerados
            if not field.primary_key and field.name not in exclude_fields:
                required_fields.append(field.name)
    
    return required_fields


# Campos exibidos na criação de layout (CSV / ETL), na ordem da UI.
# Acessos fica no topo para mapear login do arquivo (username / CPF / e-mail).
LAYOUT_MAPPING_FIELDS = [
    ('bank_access', 'Acessos'),
    ('digitador', 'Digitador'),
    ('contract_number', None),
    ('agreement', None),
    ('table', None),
    ('status', None),
    ('disbursement_date', None),
    ('amount', None),
    ('client_document', None),
    ('client_name', None),
]


def _field_info(field, verbose_name=None):
    label = verbose_name or getattr(field, 'verbose_name', field.name)
    info = {
        'name': field.name,
        'verbose_name': str(label),
        'type': field.__class__.__name__,
        'required': False,
        'has_default': field.has_default() if hasattr(field, 'has_default') else False,
    }
    if hasattr(field, 'blank'):
        info['blank'] = field.blank
        info['null'] = field.null
        info['required'] = not field.blank and not field.null and not field.has_default()
    return info


def get_model_fields(exclude_fields=[]):
    """
    Obtém todos os campos do modelo Proposal com suas propriedades.
    Retorna uma lista com informações sobre cada campo.
    """
    req_fields = []
    for field in Proposal._meta.get_fields():
        if field.is_relation and field.auto_created and not field.concrete:
            continue
        if field.name in exclude_fields:
            continue
        label_overrides = {
            'bank_access': 'Acessos',
            'digitador': 'Digitador',
        }
        req_fields.append(_field_info(field, label_overrides.get(field.name)))
    return req_fields


def get_layout_mapping_fields():
    """
    Campos disponíveis para relacionar colunas do arquivo na criação de layout.
    Lista explícita: garante Acessos (bank_access) visível e na ordem certa.
    """
    fields_by_name = {}
    for field in Proposal._meta.get_fields():
        if getattr(field, 'name', None):
            fields_by_name[field.name] = field

    result = []
    for name, label in LAYOUT_MAPPING_FIELDS:
        field = fields_by_name.get(name)
        if field is None:
            continue
        result.append(_field_info(field, label))
    return result

def get_file_type(file_path):
    """
    Obtém o tipo de arquivo.
    """
    file_type = detect_file_type(file_path)
    
    return file_type

def get_file_data(file_path):
    """
    Obtém os dados do arquivo.
    """
    file_type = get_file_type(file_path)
    if file_type == 'csv':
        try:
            # Texto puro: pandas não pode inferir 10/09/2026 como 9 de outubro (MM/DD).
            return pd.read_csv(
                file_path, sep=None, engine='python', encoding='utf-8', **_FILE_AS_TEXT
            )
        except (UnicodeDecodeError, pd.errors.ParserError):
            try:
                return pd.read_csv(
                    file_path,
                    sep=None,
                    engine='python',
                    encoding='latin-1',
                    on_bad_lines='skip',
                    **_FILE_AS_TEXT,
                )
            except Exception:
                return pd.read_csv(
                    file_path,
                    sep=None,
                    engine='python',
                    encoding='utf-8',
                    on_bad_lines='skip',
                    quoting=1,
                    skipinitialspace=True,
                    **_FILE_AS_TEXT,
                )
    elif file_type in ('xls', 'xlsx'):
        return pd.read_excel(file_path, **_FILE_AS_TEXT)
    return None

def file_to_dict(file_path):
    """
    Converte os dados do arquivo para dicionário.
    """
    data = get_file_data(file_path)
    return data.to_dict(orient='records')


def extract_emails(text):
    """
    Extrai todos os emails válidos de uma string usando regex.
    
    Args:
        text (str): Texto para buscar emails
        
    Returns:
        list: Lista de emails encontrados
    """
    if not isinstance(text, str):
        return []
    
    # Padrão regex para emails
    # [a-zA-Z0-9._%+-]+ : parte do usuário (antes do @)
    # @ : símbolo obrigatório
    # [a-zA-Z0-9.-]+ : nome do domínio
    # \. : ponto literal obrigatório
    # [a-zA-Z]{2,} : TLD com pelo menos 2 caracteres
    email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    
    emails = re.findall(email_pattern, text)
    return emails


def extract_first_email(text):
    """
    Extrai o primeiro email encontrado em uma string.
    
    Args:
        text (str): Texto para buscar email
        
    Returns:
        str or None: Primeiro email encontrado ou None se não houver
    """
    emails = extract_emails(text)
    return emails[0] if emails else None


def is_email(value):
    """
    Verifica se o valor é um email válido.
    
    Args:
        value: Valor a ser verificado
        
    Returns:
        bool: True se for um email válido
    """
    if not isinstance(value, str):
        return False
    
    emails = extract_emails(value.strip())
    # Verifica se há exatamente um email e ele corresponde ao valor inteiro (tirando espaços)
    return len(emails) == 1 and emails[0] == value.strip()


