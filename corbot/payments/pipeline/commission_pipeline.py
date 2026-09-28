"""
Pipeline específica para geração de comissões.
"""
import logging
from typing import Any, List, Dict
from core.base.pipeline import Pipeline
from django.db import transaction

logger = logging.getLogger(__name__)
from .commission_steps import (
    GetProposalsStep,
    CalculateCommissionStep,
    ConvertUUIdsStep,
    CreateCommissionConfigStep,
    CreateSellerCommissionStep,
    CreateLeaderCommissionStep,
    CreateCompanyCommissionStep
)
from datetime import datetime
from payments.models import Commission
from proposals.models import Proposal


def generate_commissions_for_proposal(proposal: Proposal) -> int:
    """Gera as comissões de uma proposta. Idempotente: se já existir, não recria."""
    if Commission.objects.filter(proposal=proposal).exists():
        return 0

    proposal = (
        Proposal.objects.select_related(
            'seller',
            'seller__company',
            'seller__leader',
            'table',
            'bank_access',
            'company',
        ).get(pk=proposal.pk)
    )

    with transaction.atomic():
        calculate_step = CalculateCommissionStep(proposal)
        convert_step = ConvertUUIdsStep(proposal)
        config_step = CreateCommissionConfigStep(proposal)
        seller_step = CreateSellerCommissionStep(proposal)
        leader_step = CreateLeaderCommissionStep(proposal)
        company_step = CreateCompanyCommissionStep(proposal)

        convert_step.data = calculate_step.run()
        config_step.data = convert_step.run()
        seller_step.data = config_step.run()
        leader_step.data = seller_step.run()
        company_step.data = leader_step.run()
        company_data = company_step.run()

        created = 0
        if 'seller_commission' in company_data:
            created += 1
        if 'leader_commission' in company_data:
            created += 1
        if 'company_commission' in company_data:
            created += 1

        if created > 0:
            proposal.release_date = datetime.now().date()
            proposal.save(update_fields=['release_date'])
        else:
            logger.warning(
                "Proposta %s processada sem comissão (regras/taxas zeradas ou ausentes)",
                proposal.id,
            )
        return created


class GenerateCommissionsPipeline(Pipeline):
    """
    Pipeline para geração de comissões.
    
    Esta pipeline processa todas as propostas do sistema e gera as comissões
    correspondentes para vendedores, líderes e empresas de acordo com as regras
    configuradas.
    
    Steps executados:
    1. Buscar todas as propostas
    2. Para cada proposta:
       - Calcular comissões
       - Converter UUIDs para strings
       - Criar configuração de comissão
       - Criar comissão do vendedor
       - Criar comissão do líder (se existir)
       - Criar comissão da empresa
    """
    
    def __init__(self, batch_id: str | None = None):
        # Step inicial para buscar propostas
        self.get_proposals_step = GetProposalsStep(batch_id=batch_id)
        
        # Chama o construtor da classe pai com uma lista vazia
        # pois vamos customizar o comportamento do run()
        super().__init__([])
    
    def get_steps(self) -> List:
        """
        Retorna todos os steps da pipeline.
        
        Returns:
            List: Lista com todos os steps
        """
        return [self.get_proposals_step]
    
    def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Executa a pipeline de geração de comissões.
        
        Returns:
            dict: Resultado da execução
        """
        try:
            # Buscar todas as propostas
            proposals = self.get_proposals_step.run()
            
            total_proposals = len(proposals)
            processed_proposals = 0
            created_commissions = 0
            errors = []
            
            for proposal in proposals:
                try:
                    logger.info(f"Calculando comissão para a proposta {proposal.id}")
                    with transaction.atomic():
                        created_for_proposal = generate_commissions_for_proposal(proposal)
                        created_commissions += created_for_proposal
                        processed_proposals += 1
                except Exception as e:
                    error_msg = f"Erro ao processar proposta {proposal.id}: {str(e)}"
                    logger.error(f"ERRO: {error_msg}")
                    errors.append(error_msg)
                    processed_proposals += 1
            
            success = len(errors) == 0
            
            return {
                'success': success,
                'total_proposals': total_proposals,
                'processed_proposals': processed_proposals,
                'created_commissions': created_commissions,
                'errors': errors,
                'message': f'Processadas {processed_proposals} propostas, {created_commissions} comissões criadas' + (f', {len(errors)} erros' if errors else '')
            }
            
        except Exception as e:
            error_msg = f"Erro crítico na pipeline: {str(e)}"
            logger.critical(f"ERRO CRÍTICO: {error_msg}")
            return {
                'success': False,
                'total_proposals': 0,
                'processed_proposals': 0,
                'created_commissions': 0,
                'errors': [error_msg],
                'message': f'Erro crítico: {error_msg}'
            }
    
    def __str__(self):
        return f"GenerateCommissionsPipeline"
    
    def __repr__(self):
        return self.__str__() 