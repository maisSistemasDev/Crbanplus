# Pipeline de Geração de Comissões

## Visão Geral

Esta pipeline foi criada para substituir o código monolítico da view `GenerateComissionsView`, seguindo a abstração de pipeline definida em `core/base/pipeline.py`. A pipeline modulariza o processo de geração de comissões em steps individuais e reutilizáveis.

## Arquitetura

### Classe Base: `Step`
- **Localização**: `core/base/pipeline.py`
- **Responsabilidade**: Define a interface básica para um step de processamento
- **Métodos principais**:
  - `run(data)`: Executa a lógica do step
  - `__str__()`: Representação textual do step

### Classe Base: `Pipeline`
- **Localização**: `core/base/pipeline.py`
- **Responsabilidade**: Orquestra a execução sequencial de steps
- **Métodos principais**:
  - `run(data)`: Executa todos os steps em sequência
  - `add_step(step)`: Adiciona um step à pipeline
  - `remove_step(step)`: Remove um step da pipeline

## Steps Implementados

### 1. `GetProposalsStep`
- **Função**: Busca todas as propostas do sistema
- **Input**: Qualquer (ignorado)
- **Output**: Lista de objetos `Proposal`

### 2. `CalculateCommissionStep`
- **Função**: Calcula comissões para uma proposta específica
- **Input**: Objeto `Proposal`
- **Output**: Dicionário com dados de comissão calculados

### 3. `ConvertUUIdsStep`
- **Função**: Converte UUIDs para strings nos dados de configuração
- **Input**: Dicionário com dados de comissão
- **Output**: Dicionário com UUIDs convertidos

### 4. `CreateCommissionConfigStep`
- **Função**: Cria e salva a configuração de comissão
- **Input**: Dicionário com dados de comissão
- **Output**: Dicionário com `CommissionConfig` criado

### 5. `CreateSellerCommissionStep`
- **Função**: Cria comissão do vendedor
- **Input**: Dicionário com dados de comissão
- **Output**: Dicionário com comissão do vendedor criada

### 6. `CreateLeaderCommissionStep`
- **Função**: Cria comissão do líder (se existir)
- **Input**: Dicionário com dados de comissão
- **Output**: Dicionário com comissão do líder criada (se aplicável)

### 7. `CreateCompanyCommissionStep`
- **Função**: Cria comissão da empresa
- **Input**: Dicionário com dados de comissão
- **Output**: Dicionário com comissão da empresa criada

## Pipeline Principal: `GenerateCommissionsPipeline`

### Fluxo de Execução

1. **Buscar Propostas**: Obtém todas as propostas do sistema
2. **Para cada proposta**:
   - Calcular comissões baseadas nas regras
   - Converter UUIDs para strings
   - Criar configuração de comissão
   - Criar comissão do vendedor
   - Criar comissão do líder (se existir)
   - Criar comissão da empresa

### Saída da Pipeline

```python
{
    'success': bool,                    # True se executou sem erros
    'total_proposals': int,             # Total de propostas encontradas
    'processed_proposals': int,         # Propostas processadas com sucesso
    'created_commissions': int,         # Total de comissões criadas
    'errors': List[str],               # Lista de erros encontrados
    'message': str                     # Mensagem resumo da execução
}
```

## Como Usar

### 1. Via View Django (Recomendado)

```python
# A view já foi atualizada para usar a pipeline
# Faça uma requisição POST para o endpoint
POST /api/generate-commissions/
```

### 2. Uso Programático

```python
from payments.pipeline import GenerateCommissionsPipeline

# Criar e executar pipeline
pipeline = GenerateCommissionsPipeline()
result = pipeline.run()

# Verificar resultado
if result['success']:
    print(f"Comissões criadas: {result['created_commissions']}")
else:
    print(f"Erros: {result['errors']}")
```

### 3. Steps Individuais

```python
from payments.pipeline.commission_steps import CalculateCommissionStep
from proposals.models import Proposal

# Usar step individual
calc_step = CalculateCommissionStep()
proposal = Proposal.objects.first()
commission_data = calc_step.run(proposal)
```

### 4. Pipeline Customizada

```python
from payments.pipeline import GenerateCommissionsPipeline
from payments.pipeline.commission_steps import *

# Criar pipeline customizada
pipeline = GenerateCommissionsPipeline()

# Adicionar step customizado
# pipeline.add_step(MeuStepCustomizado())

# Remover step se necessário
# pipeline.remove_step(algum_step)

# Executar
result = pipeline.run()
```

## Benefícios da Arquitetura

### 1. **Modularidade**
- Cada step tem uma responsabilidade específica
- Fácil de testar individualmente
- Reutilização de steps em outras pipelines

### 2. **Manutenibilidade**
- Código mais limpo e organizado
- Fácil identificação de problemas
- Modificações isoladas por funcionalidade

### 3. **Extensibilidade**
- Adição de novos steps sem modificar código existente
- Criação de pipelines alternativas
- Customização fácil do fluxo

### 4. **Testabilidade**
- Testes unitários para cada step
- Testes de integração para a pipeline completa
- Mocking facilitado entre steps

### 5. **Rastreabilidade**
- Logs detalhados por step
- Estatísticas de execução
- Tratamento de erros granular

## Exemplos de Uso

Consulte `payments/pipeline/example_usage.py` para exemplos práticos de como usar a pipeline.

## Executando Exemplos

```bash
# No diretório do projeto
python manage.py shell

# No shell Django
from payments.pipeline.example_usage import *
example_basic_usage()
example_custom_pipeline()
example_individual_steps()
```

## Comparação: Antes vs Depois

### Antes (View Monolítica)
```python
def post(self, request, format=None):
    proposals = Proposal.objects.all()
    for proposal in proposals:
        # 50+ linhas de código misturado
        # Lógica de cálculo, conversão, criação tudo junto
        # Difícil de testar e manter
```

### Depois (Pipeline Modular)
```python
def post(self, request, format=None):
    pipeline = GenerateCommissionsPipeline()
    result = pipeline.run()
    # Lógica separada em steps específicos
    # Fácil de testar, manter e estender
```

## Próximos Passos

1. **Testes Unitários**: Criar testes para cada step
2. **Logging**: Adicionar logs detalhados
3. **Performance**: Otimizar processamento em lote
4. **Métricas**: Adicionar métricas de execução
5. **Documentação**: Expandir documentação técnica 