"""
Steps especificos para pipeline de processamento de lotes de propostas.
"""
import logging
import math
import json
from typing import Any, Dict, List
from decimal import Decimal
from datetime import datetime
from io import BytesIO
from pandas import DataFrame
import pandas as pd
from django.utils import timezone

from core.base.pipeline import Step
from ..models import ProposalBatch, ErroredProposal, Proposal, BatchLogFile
from ..utils import file_to_dict
from ..validations import ProposalValidation
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

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
            return pd.to_datetime(data).isoformat()
        except Exception:
            return str(data)
    else:
        return data


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


class ReadFileStep(Step):
    """Step para ler arquivo e extrair dados."""
    
    def __init__(self):
        self.name = "ReadFile"
        self.description = "Lê o arquivo de propostas e extrai os dados"
        self.function = self._read_file
    
    def _read_file(self, batch_context: Dict[str, Any]) -> Dict[str, Any]:
        """Lê o arquivo e extrai os dados."""
        batch = batch_context['batch']
        
        if not batch.file or not batch.file.file:
            raise Exception("Arquivo não encontrado no batch")
        
        file_path = batch.file.file.path
        data = file_to_dict(file_path)
        
        # Atualizar total de linhas
        total_rows = len(data)
        batch.total_rows = total_rows
        batch.status = 'processing'
        batch.save()
        
        batch_context.update({
            'data': data,
            'total_rows': total_rows,
            'current_index': 0,
            'success_count': 0,
            'error_count': 0,
            'errors': [],
            'batch': batch
        })
        
        return batch_context


class CleanDataStep(Step):
    """Step para limpar dados NaN."""
    
    def __init__(self):
        self.name = "CleanData"
        self.description = "Limpa valores NaN dos dados extraídos"
        self.function = self._clean_data
    
    def _clean_data(self, batch_context: Dict[str, Any]) -> Dict[str, Any]:
        """Limpa valores NaN dos dados."""
        data = batch_context['data']
        
        cleaned_data = []
        for item in data:
            cleaned_item = clean_nan_values(item)
            cleaned_data.append(cleaned_item)
        
        batch_context['data'] = cleaned_data
        return batch_context


class ValidateProposalStep(Step):
    """Step para validar uma proposta individual."""
    
    def __init__(self):
        self.name = "ValidateProposal"
        self.description = "Valida uma proposta individual"
        self.function = self._validate_proposal
    
    def _validate_proposal(self, proposal_context: Dict[str, Any]) -> Dict[str, Any]:
        """Valida uma proposta individual."""
        proposal_data = proposal_context['proposal_data']
        batch = proposal_context['batch']
        
        try:
            proposal_validation = ProposalValidation(proposal_data, batch.layout)
            is_valid = proposal_validation.validate_proposal()
            
            proposal_context.update({
                'is_valid': is_valid,
                'validation': proposal_validation,
                'error_message': proposal_validation.last_error if not is_valid else None
            })
            
        except Exception as e:
            proposal_context.update({
                'is_valid': False,
                'validation': None,
                'error_message': f"Erro na validação: {str(e)}"
            })
        
        return proposal_context


class CreateProposalStep(Step):
    """Step para criar proposta válida."""
    
    def __init__(self):
        self.name = "CreateProposal"
        self.description = "Cria uma proposta válida no banco de dados"
        self.function = self._create_proposal
    
    def _create_proposal(self, proposal_context: Dict[str, Any]) -> Dict[str, Any]:
        """Cria uma proposta válida."""
        if proposal_context['is_valid']:
            try:
                validation = proposal_context['validation']
                validation.proposal.batch = proposal_context['batch']
                validation.proposal.save()
                
                proposal_context['created'] = True
                proposal_context['proposal_instance'] = validation.proposal
            except Exception as e:
                proposal_context.update({
                    'created': False,
                    'is_valid': False,
                    'error_message': f"Erro ao salvar proposta: {str(e)}"
                })
        else:
            proposal_context['created'] = False
        
        return proposal_context


class HandleErrorStep(Step):
    """Step para tratar propostas com erro."""
    
    def __init__(self):
        self.name = "HandleError"
        self.description = "Registra propostas com erro"
        self.function = self._handle_error
    
    def _handle_error(self, proposal_context: Dict[str, Any]) -> Dict[str, Any]:
        """Registra propostas com erro."""
        if not proposal_context['is_valid'] or not proposal_context.get('created', False):
            try:
                ErroredProposal.objects.create(
                    batch=proposal_context['batch'],
                    original_data=proposal_context['proposal_data'],
                    error_message=proposal_context.get('error_message', 'Erro desconhecido')
                )
                proposal_context['error_saved'] = True
            except Exception as e:
                proposal_context['error_saved'] = False
                logger.error(f"Erro ao salvar proposta com erro: {e}")
        
        return proposal_context


class UpdateProgressStep(Step):
    """Step para atualizar progresso do batch."""
    
    def __init__(self):
        self.name = "UpdateProgress"
        self.description = "Atualiza o progresso do processamento"
        self.function = self._update_progress
    
    def _update_progress(self, batch_context: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza o progresso do batch."""
        batch = batch_context['batch']
        batch.processed_rows += 1

        # Incrementar errored_rows se a proposta não foi válida ou não foi criada
        if not (batch_context.get('is_valid') and batch_context.get('created')):
            batch.errored_rows += 1

        batch.save()

        return batch_context


class SendWebSocketUpdateStep(Step):
    """Step para enviar atualizações via WebSocket."""
    
    def __init__(self):
        self.name = "SendWebSocketUpdate"
        self.description = "Envia atualizações de progresso via WebSocket"
        self.function = self._send_websocket_update
    
    def _send_websocket_update(self, batch_context: Dict[str, Any]) -> Dict[str, Any]:
        """Envia atualização via WebSocket."""
        batch = batch_context['batch']
        total_rows = batch_context['total_rows']
        success_count = batch_context['success_count']
        error_count = batch_context['error_count']
        processed = success_count + error_count
        
        # Calcular progresso
        progress_percentage = round((processed / total_rows) * 100, 2) if total_rows > 0 else 0
        
        # Dados para WebSocket
        progress_data = {
            'type': 'batch_status',
            'batch_id': str(batch.id),
            'status': 'processing',
            'total_proposals': total_rows,
            'processed_proposals': processed,
            'success_proposals': success_count,
            'error_proposals': error_count,
            'progress': progress_percentage,
            'message': f'Processando linha {processed} de {total_rows}',
            'task_id': batch_context.get('task_id', str(batch.id))
        }
        
        send_websocket_update(batch.id, progress_data)
        
        return batch_context


class GenerateLogStep(Step):
    """Step para gerar arquivo de log com erros."""
    
    def __init__(self):
        self.name = "GenerateLog"
        self.description = "Gera arquivo de log com propostas com erro"
        self.function = self._generate_log
    
    def _generate_log(self, batch_context: Dict[str, Any]) -> Dict[str, Any]:
        """Gera arquivo de log com erros."""
        batch = batch_context['batch']
        
        try:
            # Buscar propostas com erro
            error_instances = ErroredProposal.objects.filter(batch=batch)
            
            if error_instances.exists():
                log_data = []
                for error in error_instances:
                    # Garantir que os dados originais estejam limpos
                    cleaned_data = clean_nan_values(error.original_data)
                    cleaned_data['error_message'] = error.error_message
                    log_data.append(cleaned_data)
                
                # Criar DataFrame com dados limpos
                df = DataFrame(log_data)
                content = BytesIO()
                df.to_excel(content, index=False)
                content.seek(0)
                
                # Salvar arquivo de log
                log_file = BatchLogFile(batch=batch)
                log_file.log_file.save(f'batch_{batch.id}_log.xlsx', content)
                log_file.save()
                
                batch_context['log_generated'] = True
                batch_context['log_file'] = log_file
            else:
                batch_context['log_generated'] = False
                batch_context['log_file'] = None
                
        except Exception as e:
            logger.error(f"Erro ao gerar log: {e}")
            batch_context['log_generated'] = False
            batch_context['log_file'] = None
        
        return batch_context


class SendFinalUpdateStep(Step):
    """Step para enviar atualização final via WebSocket."""
    
    def __init__(self):
        self.name = "SendFinalUpdate"
        self.description = "Envia atualização final de conclusão"
        self.function = self._send_final_update
    
    def _send_final_update(self, batch_context: Dict[str, Any]) -> Dict[str, Any]:
        """Envia atualização final."""
        batch = batch_context['batch']
        success_count = batch_context['success_count']
        error_count = batch_context['error_count']
        total_rows = batch_context['total_rows']

        # Atualizar status final do batch com todos os totais
        batch.status = 'completed'
        batch.processed_rows = success_count + error_count
        batch.errored_rows = error_count
        batch.processed_at = timezone.now()
        batch.save()

        # Enviar atualização final
        final_data = {
            'type': 'batch_status',
            'batch_id': str(batch.id),
            'status': 'completed',
            'total_proposals': total_rows,
            'processed_proposals': success_count + error_count,
            'success_proposals': success_count,
            'error_proposals': error_count,
            'progress': 100,
            'message': f'Processamento concluído! {success_count} sucessos, {error_count} erros',
            'task_id': batch_context.get('task_id', str(batch.id))
        }

        send_websocket_update(batch.id, final_data)

        return batch_context 