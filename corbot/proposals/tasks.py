from celery import shared_task
import logging
from .models import ProposalBatch, ErroredProposal, Proposal, BatchLogFile
from .utils import file_to_dict
from bank.models import Bank, Agreement, Table
from bank_access.models import BankAccess
from core.models import User, Company
from .utils import extract_emails
import json
import math
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from pandas import DataFrame
from io import BytesIO
from django.db import IntegrityError
from .validations import ProposalValidation
from django.utils import timezone
from datetime import datetime
import pandas as pd
from .pipeline import ProposalBatchPipeline

logger = logging.getLogger(__name__)

def clean_nan_values(data):
    """
    Remove valores NaN de um dicionário para que seja válido JSON
    """
    if isinstance(data, dict):
        try:
            cleaned = {}
            for key, value in data.items():
                cleaned[key] = clean_nan_values(value)
            return cleaned
        except Exception as e:
            logger.error(f"Erro ao limpar valores NaN no dicionário: {e}")
            return data
    elif isinstance(data, list):
        try:
            return [clean_nan_values(item) for item in data]
        except Exception as e:
            logger.error(f"Erro ao limpar valores NaN na lista: {e}")
            return data
    elif isinstance(data, float) and math.isnan(data):
        return None
    elif isinstance(data, (pd.Timestamp, datetime)):
        try:
            return data.isoformat()
        except Exception:
            return str(data)
    elif isinstance(data, str) and data.lower() == 'nan':
        return None
    elif hasattr(data, 'dtype') and 'datetime' in str(data.dtype):
        # Trata objetos numpy datetime
        try:
            return pd.to_datetime(data, dayfirst=True).isoformat()
        except Exception:
            return str(data)
    elif hasattr(data, 'timestamp'):
        # Trata objetos que têm método timestamp (como datetime)
        try:
            return data.isoformat()
        except Exception:
            return str(data)
    elif str(type(data)) in ['<class \'pandas._libs.tslibs.timestamps.Timestamp\'>', '<class \'datetime.datetime\'>']:
        # Verificação adicional por string do tipo
        try:
            return data.isoformat()
        except Exception:
            return str(data)
    elif pd.isna(data):
        return None
    else:
        return data

def get_table(name_in_bank, value):
    table = Table.objects.filter(name_in_bank=name_in_bank)
    if table.count() == 0:
        for tb in Table.objects.all():
            for alias in tb.alias or []:
                if alias.lower().strip() == name_in_bank.lower().strip():
                    if tb.covers_amount(value):
                        return tb
        raise Exception(f'Tabela não encontrada: {name_in_bank}')
    else:
        for t in table:
            if t.covers_amount(value):
                return t
        raise Exception(f'Tabela não encontrada: {name_in_bank}')

def get_bank(name):
    try:
        return Bank.objects.get(name=name)
    except Bank.DoesNotExist:
        return None

def get_agreement(name):
    try:    
        agreement = Agreement.objects.filter(name=name).first()
        if agreement:
            return agreement
        else:
            agreement = Agreement.objects.all()
            for a in agreement:
                for alias in a.alias:
                    if alias.lower().strip() == name.lower().strip():
                        return a
            raise Exception(f'Convênio não encontrado: {name}')
    except Exception as e:
        raise Exception(f'Erro ao buscar convênio: {e}')

def get_user(login):
    if not login or login == 'nan':
        raise Exception(f'Vendedor não encontrado: {login}')

    from bank_access.services import login_values_match

    value = str(login).strip()
    for access in BankAccess.objects.select_related('user').all():
        if login_values_match(value, access.username):
            return access.user
        for alias_value in access.alias or []:
            if login_values_match(value, alias_value):
                return access.user
    raise Exception(f'Vendedor não encontrado: {login}')
            

def save_errored_proposal(proposal, error_message, batch):
    # Limpar valores NaN e timestamps antes de salvar
    try:
        # Usar clean_nan_values para garantir que todos os dados sejam JSON serializáveis
        cleaned_proposal = clean_nan_values(proposal)
        
        errored_proposal = ErroredProposal.objects.create(
            original_data=cleaned_proposal,
            error_message=error_message,
            batch=batch
        )
        batch.errored_rows += 1
        batch.save()
        return errored_proposal
    except Exception as e:
        logger.error(f"Erro ao salvar proposta com erro: {e}")
        # Tentar salvar novamente com dados mais simples em caso de erro
        try:
            # Como último recurso, converte tudo para string
            simple_proposal = {}
            for key, value in proposal.items():
                if isinstance(value, (pd.Timestamp, datetime)):
                    simple_proposal[key] = str(value)
                elif isinstance(value, float) and math.isnan(value):
                    simple_proposal[key] = None
                else:
                    simple_proposal[key] = str(value) if value is not None else None
            
            errored_proposal = ErroredProposal.objects.create(
                original_data=simple_proposal,
                error_message=f"{error_message} [Nota: dados simplificados devido a erro de serialização]",
                batch=batch
            )
            batch.errored_rows += 1
            batch.save()
            return errored_proposal
        except Exception as fallback_error:
            logger.error(f"Erro crítico ao salvar proposta com erro (fallback): {fallback_error}")
            return None

def update_batch(batch):
    batch.processed_rows += 1
    batch.save()

def send_websocket_update(batch_id, data):
    """
    Envia atualização via WebSocket para o grupo do batch
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'proposal_batch_{batch_id}',
                {
                    'type': 'batch_update',
                    'message': data
                }
            )
    except Exception as e:
        logger.error(f"Erro ao enviar atualização WebSocket: {e}")

def extract_emails(email_str):
    """
    Extrai uma lista de emails a partir de uma string
    """
    import re
    if isinstance(email_str, str):
        # Remove quebras de linha e espaços extras
        email_str = re.sub(r'\s+', ' ', email_str.strip())
        # Regex para capturar emails
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email_str)
        return emails
    return []

@shared_task(bind=True)
def process_proposal_batch_with_pipeline(self, batch_id):
    """
    Processa um lote de propostas usando a pipeline modular.
    
    Args:
        batch_id: ID do batch a ser processado
        
    Returns:
        dict: Resultado do processamento
    """
    try:
        # Buscar o batch
        batch = ProposalBatch.objects.get(id=batch_id)
        
        # Criar contexto inicial
        batch_context = {
            'batch': batch,
            'task_id': self.request.id,
            'celery_task': self
        }
        
        # Criar e executar a pipeline
        pipeline = ProposalBatchPipeline()
        result = pipeline.run(batch_context)
        
        # Retornar resultado da pipeline
        return result
        
    except ProposalBatch.DoesNotExist:
        error_msg = f"Batch {batch_id} não encontrado"
        logger.error(f"ERRO: {error_msg}")
        return {
            'success': False,
            'error': error_msg
        }
    except Exception as e:
        error_msg = f"Erro crítico no processamento: {str(e)}"
        logger.error(f"ERRO: {error_msg}")
        return {
            'success': False,
            'error': error_msg
        }

@shared_task(bind=True)
def process_proposal_batch(self, batch_id):
    """
    Processa um lote de propostas usando a pipeline modular.
    
    Esta task foi atualizada para usar a arquitetura de pipeline, mantendo
    a mesma interface mas com implementação modular e mais robusta.
    
    Args:
        batch_id: ID do batch a ser processado
        
    Returns:
        dict: Resultado do processamento com estatísticas
    """
    try:
        # Buscar o batch
        batch = ProposalBatch.objects.get(id=batch_id)
        
        # Criar contexto inicial para a pipeline
        batch_context = {
            'batch': batch,
            'task_id': self.request.id,
            'celery_task': self
        }
        
        # Criar e executar a pipeline
        pipeline = ProposalBatchPipeline(callback=send_websocket_update)
        result = pipeline.run(batch_context)
        
        # Converter resultado da pipeline para o formato esperado pela task original
        if result['success']:
            return {
                'success': True,
                'processed': result.get('processed_proposals', 0),
                'success_count': result.get('success_count', 0),
                'error_count': result.get('error_count', 0),
                'message': result.get('message', 'Processamento concluído com sucesso')
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Erro desconhecido'),
                'message': result.get('message', 'Erro no processamento')
            }
        
    except ProposalBatch.DoesNotExist:
        error_msg = f"Batch {batch_id} não encontrado"
        logger.error(f"ERRO: {error_msg}")
        return {
            'success': False,
            'error': error_msg
        }
    except Exception as e:
        error_msg = f"Erro crítico no processamento: {str(e)}"
        logger.error(f"ERRO: {error_msg}")
        return {
            'success': False,
            'error': error_msg
        }