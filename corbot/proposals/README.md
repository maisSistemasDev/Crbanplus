# Módulo de Propostas - Corbot

Este módulo é responsável pelo gerenciamento de propostas de empréstimo, incluindo importação dinâmica de arquivos, mapeamento de colunas e processamento em lote.

## Funcionalidades

### 1. Importação Dinâmica de Arquivos

O sistema permite importar propostas a partir de arquivos CSV, XLS ou XLSX, com as seguintes capacidades:

- **Detecção automática de tipos de dados**: Reconhece automaticamente se uma coluna contém texto, números, datas, valores monetários ou CPFs.
- **Mapeamento flexível**: Permite associar colunas do arquivo a campos específicos do modelo de proposta.
- **Layouts reutilizáveis**: Layouts de importação podem ser salvos e reutilizados para arquivos com a mesma estrutura.
- **Processamento em background**: Importações são processadas de forma assíncrona com Celery.

### 2. Layouts de Arquivo

Os layouts de arquivo definem como os dados serão extraídos de um arquivo de importação:

- **Configurações básicas**: Nome da planilha, pular linhas, identificar cabeçalho, etc.
- **Mapeamento de colunas**: Cada coluna do arquivo pode ser mapeada para um campo específico da proposta.
- **Conversão de tipos**: Define como converter os valores encontrados no arquivo para os tipos corretos.
- **Validação de dados**: Identifica campos obrigatórios e garante que os dados importados sejam válidos.

### 3. Gerenciamento de Lotes

Cada importação gera um lote de propostas, permitindo:

- **Rastreamento de origem**: Saber quais propostas vieram de qual arquivo.
- **Logs detalhados**: Registro de erros e sucessos durante o processamento.
- **Status de processamento**: Acompanhamento em tempo real do progresso da importação.

## Arquitetura

### Modelos

- **FileLayout**: Define configurações gerais do layout de importação.
- **FileLayoutColumn**: Define o mapeamento de uma coluna específica.
- **ProposalBatch**: Representa um lote de importação de propostas.
- **Proposal**: Representa uma proposta individual.
- **CommissionGroup**: Define percentuais de comissão para gerentes e vendedores.

### Utilitários

- **Detecção de tipos**: Funções para identificar o tipo de dados em uma coluna.
- **Conversão de valores**: Funções para converter valores entre diferentes tipos de dados.
- **Processamento de arquivos**: Funções para ler e processar diferentes formatos de arquivo.

### API REST

- **Mapeamento de arquivos**: Endpoints para analisar arquivos e identificar suas colunas.
- **Gerenciamento de layouts**: Endpoints para criar, editar e excluir layouts de importação.
- **Importação de propostas**: Endpoints para importar propostas usando layouts existentes.

## Fluxo de Importação

1. **Upload de arquivo**: O usuário envia um arquivo para análise.
2. **Mapeamento**: O sistema detecta as colunas e seus tipos, e o usuário realiza o mapeamento para os campos da proposta.
3. **Criação de layout**: O mapeamento é salvo como um layout reutilizável (opcional).
4. **Importação**: O arquivo é processado usando o layout definido, gerando um lote de propostas.
5. **Processamento assíncrono**: As propostas são criadas em background, com registro de progresso e erros.
6. **Resultados**: O usuário recebe o resultado da importação, incluindo quantas propostas foram importadas com sucesso e quantas falharam.

## Tipos de Dados Suportados

- **Texto**: Strings normais.
- **Número inteiro**: Valores numéricos sem casas decimais.
- **Decimal**: Valores numéricos com casas decimais.
- **Data**: Datas em formatos brasileiros (DD/MM/AAAA).
- **Data e hora**: Datas com hora em formatos brasileiros.
- **Moeda**: Valores monetários (R$ X,XX).
- **CPF**: Números de CPF com ou sem formatação.
- **Booleano**: Valores verdadeiro/falso, sim/não, 0/1.

## Exemplos de Uso

### Detecção de Colunas

```json
POST /api/proposals/file-mapping/
```

Resposta:

```json
{
  "columns": [
    {
      "column_name": "Número Proposta",
      "column_index": 0,
      "detected_type": "text",
      "sample_data": "12345-6"
    },
    {
      "column_name": "Valor",
      "column_index": 1,
      "detected_type": "currency",
      "sample_data": "R$ 1.500,00"
    }
  ],
  "layouts": [...],
  "required_fields": [...]
}
```

### Criação de Layout

```json
POST /api/proposals/file-mapping/create_layout/
```

### Importação com Layout

```json
POST /api/proposals/file-mapping/import_with_layout/
```

## Customização e Extensão

O sistema foi projetado para ser facilmente extensível:

- **Novos tipos de dados**: É possível adicionar funções para detectar e converter novos tipos de dados.
- **Transformações personalizadas**: O campo `transform_function` permite definir funções Python para processamento personalizado.
- **Campos adicionais**: O sistema suporta salvar dados extras no campo `additional_data` do modelo de proposta.

## Exemplo do Arquivo Postman

Para testar a API, importe o arquivo `corbot_api_collection.json` no Postman. Esta coleção contém todas as requisições necessárias para interagir com o sistema de importação dinâmica de propostas.
