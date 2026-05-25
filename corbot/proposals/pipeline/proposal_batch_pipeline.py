"""
Pipeline especifica para processamento de lotes de propostas.
"""
import logging
from typing import Any, Dict, Callable
from core.base.pipeline import Pipeline
from .proposal_batch_steps import (
    ReadFileStep,
    CleanDataStep,
    ValidateProposalStep,
    CreateProposalStep,
    HandleErrorStep,
    UpdateProgressStep,
    SendWebSocketUpdateStep,
    GenerateLogStep,
    SendFinalUpdateStep,
    send_websocket_update
)

logger = logging.getLogger(__name__)


class ProposalProcessingPipeline(Pipeline):
    """
    Sub-pipeline para processar uma proposta individual.
    
    Esta pipeline processa uma única proposta através dos steps:
    1. Validar proposta
    2. Criar proposta (se válida)
    3. Tratar erro (se inválida)
    """
    
    def __init__(self):
        # Steps para processar uma proposta individual
        steps = [
            ValidateProposalStep(),
            CreateProposalStep(),
            HandleErrorStep()
        ]
        super().__init__(steps)
    
    def run(self, proposal_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa o processamento de uma proposta individual.
        
        Args:
            proposal_context: Contexto da proposta individual
            
        Returns:
            dict: Resultado do processamento
        """
        try:
            # Executar todos os steps da sub-pipeline
            result_context = proposal_context
            for step in self.steps:
                result_context = step.run(result_context)
            
            return result_context
            
        except Exception as e:
            logger.error(f"Erro na sub-pipeline de proposta: {str(e)}")
            return {
                'is_valid': False,
                'created': False,
                'error': str(e),
                **proposal_context
            }


class ProposalBatchPipeline(Pipeline):
    """
    Pipeline principal para processamento de lotes de propostas.
    
    Esta pipeline processa um lote completo de propostas executando:
    1. Ler arquivo e extrair dados
    2. Limpar dados NaN
    3. Para cada proposta:
       - Executar sub-pipeline de processamento
       - Atualizar progresso
       - Enviar updates via WebSocket
    4. Gerar log de erros
    5. Enviar atualização final
    """
    
    def __init__(self, callback: Callable = None):
        # Steps iniciais da pipeline
        self.initial_steps = [
            ReadFileStep(),
            CleanDataStep()
        ]
        
        # Sub-pipeline para processar propostas individuais
        self.proposal_pipeline = ProposalProcessingPipeline()
        
        # Steps de progresso e comunicação
        self.progress_steps = [
            UpdateProgressStep(),
            SendWebSocketUpdateStep()
        ]
        
        # Steps finais
        self.final_steps = [
            GenerateLogStep(),
            SendFinalUpdateStep()
        ]
        
        # Configurar callback com fallback seguro
        self.callback = self._setup_callback(callback)
        
        # Pipeline principal vazia - customizamos o comportamento do run()
        super().__init__([])
    
    def _setup_callback(self, callback):
        """
        Configura o callback com fallback seguro.
        
        Args:
            callback: Callback fornecido ou None
            
        Returns:
            callable: Callback válido
        """
        if callback and callable(callback):
            return callback
        elif send_websocket_update and callable(send_websocket_update):
            return send_websocket_update
        else:
            # Fallback final - função dummy que não faz nada
            def dummy_callback(batch_id, data):
                logger.debug(f"Callback dummy - Batch {batch_id}: {data.get('message', 'update')}")
            return dummy_callback
    
    def run(self, batch_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa a pipeline de processamento de lotes de propostas.
        
        Args:
            batch_context: Contexto com informações do batch
            
        Returns:
            dict: Resultado do processamento com estatísticas
        """
        try:
            # Inicializar contadores se não existirem
            batch_context.setdefault('success_count', 0)
            batch_context.setdefault('error_count', 0)
            batch_context.setdefault('current_index', 0)
            
            # Enviar estado inicial
            self._send_initial_update(batch_context)
            
            # Step 1: Executar steps iniciais
            for step in self.initial_steps:
                batch_context = step.run(batch_context)
            
            # Step 2: Processar cada proposta individualmente
            data = batch_context['data']
            total_rows = batch_context['total_rows']
            
            for index, proposal_data in enumerate(data):
                try:
                    # Criar contexto para a proposta individual
                    proposal_context = {
                        'proposal_data': proposal_data,
                        'batch': batch_context['batch'],
                        'index': index
                    }
                    
                    # Executar sub-pipeline para a proposta
                    proposal_result = self.proposal_pipeline.run(proposal_context)
                    
                    # Atualizar contadores baseado no resultado
                    if proposal_result.get('is_valid') and proposal_result.get('created'):
                        batch_context['success_count'] += 1
                    else:
                        batch_context['error_count'] += 1
                    
                    # Atualizar índice atual
                    batch_context['current_index'] = index + 1
                    
                    # Executar steps de progresso
                    for step in self.progress_steps:
                        batch_context = step.run(batch_context)
                        
                except Exception as e:
                    # Tratar erro na proposta individual
                    batch_context['error_count'] += 1
                    error_msg = f"Erro ao processar linha {index}: {str(e)}"
                    logger.error(f"ERRO: {error_msg}")
                    
                    # Continuar processamento mesmo com erro
                    batch_context['current_index'] = index + 1
            
            # Step 3: Executar steps finais
            for step in self.final_steps:
                batch_context = step.run(batch_context)
            
            # Retornar resultado de sucesso
            return {
                'success': True,
                'batch_id': str(batch_context['batch'].id),
                'total_proposals': batch_context['total_rows'],
                'processed_proposals': batch_context['success_count'] + batch_context['error_count'],
                'success_count': batch_context['success_count'],
                'error_count': batch_context['error_count'],
                'log_generated': batch_context.get('log_generated', False),
                'message': f"Processamento concluído com sucesso: {batch_context['success_count']} sucessos, {batch_context['error_count']} erros"
            }
            
        except Exception as e:
            # Tratar erro crítico
            error_message = str(e)
            logger.error(f"Erro crítico no processamento: {error_message}")
            
            # Atualizar status do batch para erro
            batch = batch_context['batch']
            batch.status = 'failed'
            batch.error_message = error_message
            batch.save()
            
            # Enviar erro via WebSocket
            self._send_error_update(batch_context, error_message)
            
            return {
                'success': False,
                'batch_id': str(batch.id),
                'error': error_message,
                'message': f"Erro no processamento: {error_message}"
            }
    
    def _send_initial_update(self, batch_context: Dict[str, Any]):
        """Envia atualização inicial via WebSocket."""
        try:
            batch = batch_context['batch']
            
            initial_progress = {
                'type': 'batch_status',
                'batch_id': str(batch.id),
                'status': 'processing',
                'total_proposals': 0,
                'processed_proposals': 0,
                'success_proposals': 0,
                'error_proposals': 0,
                'progress': 0,
                'message': 'Iniciando processamento...',
                'task_id': batch_context.get('task_id', str(batch.id))
            }
            
            if self.callback and callable(self.callback):
                self.callback(batch.id, initial_progress)
            else:
                logger.warning("Callback não disponível para envio de atualização inicial")

        except Exception as e:
            logger.error(f"Erro ao enviar atualização inicial: {e}")
    
    def _send_error_update(self, batch_context: Dict[str, Any], error_message: str):
        """Envia atualização de erro via WebSocket."""
        try:
            batch = batch_context['batch']
            
            error_data = {
                'type': 'batch_status',
                'batch_id': str(batch.id),
                'status': 'failed',
                'error_message': error_message,
                'task_id': batch_context.get('task_id', str(batch.id))
            }
            
            if self.callback and callable(self.callback):
                self.callback(batch.id, error_data)
            else:
                logger.warning(f"Callback não disponível para envio de erro: {error_message}")

        except Exception as e:
            logger.error(f"Erro ao enviar atualização de erro: {e}")
    
    def get_steps(self):
        """
        Retorna todos os steps da pipeline.
        
        Returns:
            List: Lista com todos os steps
        """
        all_steps = []
        all_steps.extend(self.initial_steps)
        all_steps.extend(self.proposal_pipeline.get_steps())
        all_steps.extend(self.progress_steps)
        all_steps.extend(self.final_steps)
        return all_steps
    
    def add_step(self, step, category='final'):
        """
        Adiciona um step à pipeline.
        
        Args:
            step: Step a ser adicionado
            category: Categoria do step ('initial', 'proposal', 'progress', 'final')
        """
        if category == 'initial':
            self.initial_steps.append(step)
        elif category == 'proposal':
            self.proposal_pipeline.add_step(step)
        elif category == 'progress':
            self.progress_steps.append(step)
        elif category == 'final':
            self.final_steps.append(step)
        else:
            raise ValueError(f"Categoria inválida: {category}")
    
    def remove_step(self, step):
        """
        Remove um step da pipeline.
        
        Args:
            step: Step a ser removido
        """
        if step in self.initial_steps:
            self.initial_steps.remove(step)
        elif step in self.proposal_pipeline.get_steps():
            self.proposal_pipeline.remove_step(step)
        elif step in self.progress_steps:
            self.progress_steps.remove(step)
        elif step in self.final_steps:
            self.final_steps.remove(step)
    
    def __str__(self):
        total_steps = len(self.get_steps())
        return f"ProposalBatchPipeline com {total_steps} steps"
    
    def __repr__(self):
        return self.__str__() 