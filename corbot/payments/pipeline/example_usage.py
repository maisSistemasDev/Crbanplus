"""
Exemplo de uso da pipeline de geração de comissões.

Este arquivo demonstra como usar a pipeline criada de forma standalone,
sem depender da view Django.
"""

from .commission_pipeline import GenerateCommissionsPipeline
from .commission_steps import *


def example_basic_usage():
    """
    Exemplo básico de uso da pipeline.
    """
    print("=== Exemplo Básico de Uso da Pipeline ===")
    
    # Criar e executar a pipeline
    pipeline = GenerateCommissionsPipeline()
    result = pipeline.run()
    
    # Exibir resultados
    print(f"Sucesso: {result['success']}")
    print(f"Total de propostas: {result['total_proposals']}")
    print(f"Propostas processadas: {result['processed_proposals']}")
    print(f"Comissões criadas: {result['created_commissions']}")
    
    if result['errors']:
        print("\nErros encontrados:")
        for error in result['errors']:
            print(f"- {error}")


def example_custom_pipeline():
    """
    Exemplo de como criar uma pipeline customizada.
    """
    print("\n=== Exemplo de Pipeline Customizada ===")
    
    # Criar pipeline com steps específicos
    pipeline = GenerateCommissionsPipeline()
    
    # Adicionar step customizado (exemplo)
    # pipeline.add_step(MeuStepCustomizado())
    
    # Listar todos os steps
    print("Steps da pipeline:")
    for i, step in enumerate(pipeline.get_steps(), 1):
        print(f"{i}. {step}")
    
    # Executar pipeline
    result = pipeline.run()
    print(f"\nResultado: {result['message']}")


def example_individual_steps():
    """
    Exemplo de como usar steps individuais.
    """
    print("\n=== Exemplo de Steps Individuais ===")
    
    # Usar step individual para buscar propostas
    get_proposals_step = GetProposalsStep()
    proposals = get_proposals_step.run(None)
    print(f"Total de propostas encontradas: {len(proposals)}")
    
    # Se houver propostas, processar a primeira
    if proposals:
        proposal = proposals[0]
        print(f"Processando proposta: {proposal.id}")
        
        # Calcular comissão
        calc_step = CalculateCommissionStep()
        commission_data = calc_step.run(proposal)
        
        print(f"Comissão do vendedor: {commission_data['commission_seller']}")
        print(f"Comissão do líder: {commission_data['commission_leader']}")
        print(f"Comissão da empresa: {commission_data['commission_company']}")


if __name__ == "__main__":
    """
    Para executar este exemplo em um ambiente Django:
    
    1. No diretório do projeto, execute:
       python manage.py shell
    
    2. No shell Django, execute:
       from payments.pipeline.example_usage import *
       example_basic_usage()
       example_custom_pipeline()
       example_individual_steps()
    """
    
    # Avisos para execução em contexto Django
    print("Este exemplo deve ser executado em um contexto Django.")
    print("Use 'python manage.py shell' e importe as funções deste módulo.")
    
    # Exemplo de uso alternativo sem contexto Django
    print("\n=== Estrutura da Pipeline ===")
    try:
        pipeline = GenerateCommissionsPipeline()
        print(f"Pipeline criada: {pipeline}")
        print(f"Total de steps: {len(pipeline.get_steps())}")
    except Exception as e:
        print(f"Erro ao criar pipeline (esperado sem contexto Django): {e}") 