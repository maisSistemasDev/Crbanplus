"""
Exemplo de uso da pipeline de processamento de lotes de propostas.

Este arquivo demonstra como usar a pipeline criada de forma standalone,
sem depender da task do Celery.
"""

from .proposal_batch_pipeline import ProposalBatchPipeline, ProposalProcessingPipeline
from .proposal_batch_steps import *
from ..models import ProposalBatch


def example_basic_usage():
    """
    Exemplo básico de uso da pipeline de lotes de propostas.
    """
    print("=== Exemplo Básico de Uso da Pipeline de Propostas ===")
    
    # Buscar um batch existente (substitua pelo ID real)
    try:
        batch = ProposalBatch.objects.filter(status='pending').first()
        if not batch:
            print("Nenhum batch pendente encontrado. Crie um batch primeiro.")
            return
        
        # Criar contexto inicial
        batch_context = {
            'batch': batch,
            'task_id': 'manual_execution'
        }
        
        # Criar e executar a pipeline
        pipeline = ProposalBatchPipeline()
        result = pipeline.run(batch_context)
        
        # Exibir resultados
        print(f"Sucesso: {result['success']}")
        print(f"Batch ID: {result.get('batch_id')}")
        print(f"Total de propostas: {result.get('total_proposals', 0)}")
        print(f"Propostas processadas: {result.get('processed_proposals', 0)}")
        print(f"Sucessos: {result.get('success_count', 0)}")
        print(f"Erros: {result.get('error_count', 0)}")
        
        if not result['success']:
            print(f"Erro: {result.get('error')}")
            
    except Exception as e:
        print(f"Erro na execução: {e}")


def example_individual_proposal_processing():
    """
    Exemplo de como usar a sub-pipeline para processar uma proposta individual.
    """
    print("\n=== Exemplo de Processamento de Proposta Individual ===")
    
    try:
        # Buscar um batch para usar como contexto
        batch = ProposalBatch.objects.first()
        if not batch:
            print("Nenhum batch encontrado. Crie um batch primeiro.")
            return
        
        # Dados de exemplo de uma proposta (substitua pelos dados reais)
        proposal_data = {
            'client_name': 'João Silva',
            'client_document': '12345678901',
            'amount': 5000.00,
            'contract_number': 'TEST123',
            # Adicione outros campos necessários baseado no layout
        }
        
        # Criar contexto para a proposta
        proposal_context = {
            'proposal_data': proposal_data,
            'batch': batch,
            'index': 0
        }
        
        # Usar sub-pipeline para processar proposta individual
        pipeline = ProposalProcessingPipeline()
        result = pipeline.run(proposal_context)
        
        print(f"Proposta válida: {result.get('is_valid', False)}")
        print(f"Proposta criada: {result.get('created', False)}")
        
        if result.get('error_message'):
            print(f"Erro: {result['error_message']}")
            
    except Exception as e:
        print(f"Erro na execução: {e}")


def example_custom_pipeline():
    """
    Exemplo de como criar uma pipeline customizada.
    """
    print("\n=== Exemplo de Pipeline Customizada ===")
    
    # Criar pipeline customizada
    pipeline = ProposalBatchPipeline()
    
    # Listar todos os steps
    print("Steps da pipeline:")
    for i, step in enumerate(pipeline.get_steps(), 1):
        print(f"{i}. {step}")
    
    # Exemplo de como adicionar um step customizado
    # custom_step = MeuStepCustomizado()
    # pipeline.add_step(custom_step, category='initial')
    
    print(f"\nPipeline criada: {pipeline}")


def example_individual_steps():
    """
    Exemplo de como usar steps individuais.
    """
    print("\n=== Exemplo de Steps Individuais ===")
    
    try:
        # Buscar um batch para testar
        batch = ProposalBatch.objects.first()
        if not batch:
            print("Nenhum batch encontrado. Crie um batch primeiro.")
            return
        
        # Criar contexto
        batch_context = {
            'batch': batch,
            'task_id': 'manual_test'
        }
        
        # Usar step individual para ler arquivo
        read_step = ReadFileStep()
        result = read_step.run(batch_context)
        
        print(f"Arquivo lido com sucesso!")
        print(f"Total de linhas: {result.get('total_rows', 0)}")
        
        # Usar step para limpar dados
        clean_step = CleanDataStep()
        result = clean_step.run(result)
        
        print(f"Dados limpos com sucesso!")
        
        # Mostrar algumas propostas de exemplo
        data = result.get('data', [])
        if data:
            print(f"Primeira proposta: {data[0]}")
            
    except Exception as e:
        print(f"Erro na execução: {e}")


def example_error_handling():
    """
    Exemplo de como a pipeline lida com erros.
    """
    print("\n=== Exemplo de Tratamento de Erros ===")
    
    try:
        # Criar contexto com batch inválido para testar tratamento de erro
        batch_context = {
            'batch': None,  # Propositalmente inválido
            'task_id': 'error_test'
        }
        
        pipeline = ProposalBatchPipeline()
        result = pipeline.run(batch_context)
        
        print(f"Resultado (esperado erro): {result}")
        
    except Exception as e:
        print(f"Erro capturado corretamente: {e}")


if __name__ == "__main__":
    """
    Para executar este exemplo em um ambiente Django:
    
    1. No diretório do projeto, execute:
       python manage.py shell
    
    2. No shell Django, execute:
       from proposals.pipeline.example_usage import *
       example_basic_usage()
       example_individual_proposal_processing()
       example_custom_pipeline()
       example_individual_steps()
       example_error_handling()
    """
    
    # Avisos para execução em contexto Django
    print("Este exemplo deve ser executado em um contexto Django.")
    print("Use 'python manage.py shell' e importe as funções deste módulo.")
    
    # Exemplo de uso alternativo sem contexto Django
    print("\n=== Estrutura da Pipeline ===")
    try:
        pipeline = ProposalBatchPipeline()
        print(f"Pipeline criada: {pipeline}")
        print(f"Total de steps: {len(pipeline.get_steps())}")
        
        # Mostrar estrutura dos steps
        print("\nCategorias de steps:")
        print(f"- Steps iniciais: {len(pipeline.initial_steps)}")
        print(f"- Steps de proposta: {len(pipeline.proposal_pipeline.get_steps())}")
        print(f"- Steps de progresso: {len(pipeline.progress_steps)}")
        print(f"- Steps finais: {len(pipeline.final_steps)}")
        
    except Exception as e:
        print(f"Erro ao criar pipeline (esperado sem contexto Django): {e}") 