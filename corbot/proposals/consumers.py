import json
import logging
from urllib.parse import parse_qs
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model
from celery.result import AsyncResult

from .models import ProposalBatch, Proposal

User = get_user_model()
logger = logging.getLogger(__name__)

class BatchProcessingConsumer(WebsocketConsumer):
    def connect(self):
        try:
            self.user = self.scope.get('user', AnonymousUser())
            
            # Verificar autenticação via token JWT
            if isinstance(self.user, AnonymousUser):
                raw_query = self.scope.get('query_string', b'').decode('utf-8')
                token = parse_qs(raw_query).get('token', [None])[0]

                if token:
                    try:
                        access_token = AccessToken(token)
                        user_id = access_token.payload.get('user_id')
                        self.user = User.objects.get(id=user_id)
                    except (TokenError, User.DoesNotExist):
                        logger.warning(f"Tentativa de conexão com token inválido: {token}")
                        self.close()
                        return
                    except Exception as e:
                        logger.error(e)
                        self.close()
                        return
                else:
                    logger.warning("Tentativa de conexão sem token de autenticação")
                    self.close()
                    return
            
            # Obter o ID do lote dos parâmetros da URL
            self.batch_id = self.scope['url_route']['kwargs']['batch_id']
            self.batch_group_name = f'proposal_batch_{self.batch_id}'
        except Exception as e:
            logger.error(e)
            self.close()
            return
        try:
            # Verificar se o usuário tem acesso ao lote
            batch = ProposalBatch.objects.get(id=self.batch_id)
            
            # Adicionar ao grupo do lote
            async_to_sync(self.channel_layer.group_add)(
                self.batch_group_name,
                self.channel_name
            )
            
            self.accept()
            
            # Enviar estado atual do lote logo após a conexão
            self.send_current_status(batch)
            
        except ProposalBatch.DoesNotExist:
            logger.warning(f"Tentativa de conexão com lote inexistente: {self.batch_id}")
            self.close()
        except Exception as e:
            logger.error(e)
            self.close()
            
    
    def disconnect(self, close_code):
        # Remover do grupo do lote
        async_to_sync(self.channel_layer.group_discard)(
            self.batch_group_name,
            self.channel_name
        )
    
    def receive(self, text_data):
        # Processar comandos do cliente
        try:
            data = json.loads(text_data)
            command = data.get('command')
            
            if command == 'get_status':
                # Recuperar e enviar status atual do lote
                try:
                    batch = ProposalBatch.objects.get(id=self.batch_id)
                    self.send_current_status(batch)
                except ProposalBatch.DoesNotExist:
                    self.send(text_data=json.dumps({
                        'error': 'Lote não encontrado',
                        'code': 'batch_not_found'
                    }))
            
            elif command == 'get_task_status':
                # Recuperar e enviar status da tarefa Celery associada ao lote
                task_id = data.get('task_id')
                if task_id:
                    task_status = self.get_task_status(task_id)
                    self.send(text_data=json.dumps({
                        'type': 'task_status',
                        'task_id': task_id,
                        'status': task_status
                    }))
                else:
                    self.send(text_data=json.dumps({
                        'error': 'ID de tarefa não fornecido',
                        'code': 'missing_task_id'
                    }))
                    
        except json.JSONDecodeError:
            self.send(text_data=json.dumps({
                'error': 'Formato de mensagem inválido',
                'code': 'invalid_format'
            }))
        except Exception as e:
            logger.error(e)
            self.send(text_data=json.dumps({
                'error': str(e),
                'code': 'internal_server_error'
            }))
    
    def batch_update(self, event):
        # Enviar atualização para o cliente
        self.send(text_data=json.dumps(event['message']))
    
    def send_current_status(self, batch: ProposalBatch):
        """
        Envia o status atual do lote para o cliente
        """
        # Usa os totais persistidos no lote para evitar divergencias entre
        # valores da tela e eventos de websocket apos refresh/reconexao.
        total_proposals = max(batch.total_rows or 0, 0)
        processed_proposals = max(batch.processed_rows or 0, 0)
        error_proposals = max(batch.errored_rows or 0, 0)
        success_proposals = max(processed_proposals - error_proposals, 0)
        pending_proposals = max(total_proposals - processed_proposals, 0)
        
        # Calcular progresso
        progress = 0
        if total_proposals > 0:
            progress = round(((processed_proposals + error_proposals) / total_proposals) * 100, 2)
        
        # Verificar status da tarefa Celery usando o task_id real
        task_status = None
        if batch.task_id:
            task_status = self.get_task_status(batch.task_id)
            
            # Se a tarefa estiver em progresso, usar o progresso reportado pela tarefa
            if task_status and task_status.get('status') == 'PROGRESS':
                progress = task_status.get('progress', progress)
        
        # Enviar dados atuais
        self.send(text_data=json.dumps({
            'type': 'batch_status',
            'batch_id': str(batch.id),
            'status': batch.status,
            'created_at': batch.created_at.isoformat() if batch.created_at else None,
            'processing_started_at': batch.created_at.isoformat() if batch.created_at else None,
            'processing_completed_at': batch.processed_at.isoformat() if batch.processed_at else None,
            'file_name': batch.file.file.name if batch.file and batch.file.file else None,
            'row_count': batch.total_rows,
            'total_proposals': total_proposals,
            'processed_proposals': processed_proposals,
            'error_proposals': error_proposals,
            'success_proposals': success_proposals,
            'pending_proposals': pending_proposals,
            'progress': progress,
            'task_id': batch.task_id or str(batch.id)  # Usar task_id real ou fallback para batch.id
        }))
    
    def get_task_status(self, task_id):
        """
        Obtém o status de uma tarefa Celery
        """
        try:
            task = AsyncResult(task_id)
            
            result = {
                'status': task.status,
            }
            
            # Adicionar detalhes da tarefa se disponíveis
            if task.info:
                if isinstance(task.info, dict):
                    result.update({
                        'progress': task.info.get('progress', 0),
                        'current': task.info.get('current', 0),
                        'total': task.info.get('total', 0),
                        'message': task.info.get('message', '')
                    })
                    
                    # Se houver erro, incluir na resposta
                    if 'error' in task.info:
                        result['error'] = task.info['error']
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao obter status da tarefa {task_id}: {str(e)}")
            return {
                'status': 'ERROR',
                'error': str(e)
            } 