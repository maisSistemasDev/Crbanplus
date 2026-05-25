# 🧪 Guia Rápido de Testes - Feature CSV Import

## Pré-requisitos
- [ ] Branch `feature/csv-tables-import` checked out
- [ ] Migrations executadas
- [ ] Servidor rodando (Docker ou local)
- [ ] Ferramenta de API (Postman, Insomnia, curl, ou similar)

## 1️⃣ Teste: Importar Tabelas (Create)

### Setup
1. Criar banco via admin ou API (anotar bank_id)
2. Preparar CSV com tabelas novas

### Arquivo: `test_tabelas_novas.csv`
```csv
nome_no_banco;convenio;valor_minimo;valor_maximo;taxa_de_comissionamento;data_de_vigencia
Tabela Teste 1;INSS;5000;50000;3.5;2025-01-01
Tabela Teste 2;FGTS;10000;100000;4.0;2025-02-01
```

### Request
```bash
POST http://localhost:8000/api/bank/tables/create-batch/
Content-Type: multipart/form-data
Authorization: Token <your-admin-token>

Form Data:
- file: test_tabelas_novas.csv
- bank_id: <bank-uuid>
```

### ✅ Resultado Esperado
```json
{
  "created_count": 2,
  "updated_count": 0,
  "created_tables": [
    {"name": "TABELA TESTE 1", "bank": "...", "agreement": "INSS", "action": "created"},
    {"name": "TABELA TESTE 2", "bank": "...", "agreement": "FGTS", "action": "created"}
  ],
  "updated_tables": [],
  "errors_count": 0,
  "errors": []
}
```

### 🔍 Verificar
- [ ] Status 201 Created
- [ ] created_count = 2
- [ ] Tabelas criadas no banco de dados
- [ ] Convênios INSS e FGTS criados (se não existiam)
- [ ] Nomes normalizados (maiúsculas)

---

## 2️⃣ Teste: Atualizar Tabelas Existentes (Update)

### Arquivo: `test_tabelas_update.csv`
(Mesmo nome, novos valores)
```csv
nome_no_banco;convenio;valor_minimo;valor_maximo;taxa_de_comissionamento;data_de_vigencia
Tabela Teste 1;INSS;5000;50000;5.0;2025-03-01
```

### Request
(Mesmo endpoint do teste anterior)

### ✅ Resultado Esperado
```json
{
  "created_count": 0,
  "updated_count": 1,
  "created_tables": [],
  "updated_tables": [
    {"name": "TABELA TESTE 1", "bank": "...", "agreement": "INSS", "action": "updated"}
  ],
  "errors_count": 0,
  "errors": []
}
```

### 🔍 Verificar
- [ ] Status 201 Created (mesmo em update)
- [ ] updated_count = 1
- [ ] Taxa mudou de 3.5 para 5.0
- [ ] Data mudou para 2025-03-01
- [ ] Histórico registrado

---

## 3️⃣ Teste: Visualizar Histórico

### Request
```bash
GET http://localhost:8000/api/bank/tables/<table-id>/history/
Authorization: Token <your-token>
```

### ✅ Resultado Esperado
```json
{
  "table": {...},
  "history": [
    {
      "action": "CSV_UPDATE",
      "user": {"name": "Admin User"},
      "field_changes": {
        "commission_rate": true,
        "vigency_date": true
      },
      "previous_values": {
        "commission_rate": "3.5",
        "vigency_date": "2025-01-01"
      },
      "new_values": {
        "commission_rate": "5.0",
        "vigency_date": "2025-03-01"
      },
      "created_at": "2025-04-28T..."
    },
    {
      "action": "CSV_IMPORT",
      "user": {"name": "Admin User"},
      "new_values": {
        "commission_rate": "3.5",
        ...
      },
      "created_at": "2025-04-28T..."
    }
  ],
  "count": 2
}
```

### 🔍 Verificar
- [ ] Dois registros: CSV_IMPORT (criação) e CSV_UPDATE (atualização)
- [ ] Valores anteriores e novos corretos
- [ ] Usuário registrado
- [ ] Timestamps corretos

---

## 4️⃣ Teste: Exportar Tabelas

### Request
```bash
GET http://localhost:8000/api/bank/tables/export-csv/<bank-id>/
Authorization: Token <your-token>
```

### ✅ Resultado Esperado
- Arquivo CSV baixado
- Nome: `tabelas_<nome_banco>.csv`
- Conteúdo:
```csv
nome_no_banco;convenio;valor_minimo;valor_maximo;taxa_de_comissionamento;data_de_vigencia
TABELA TESTE 1;INSS;5000.0;50000.0;5.0;2025-03-01
TABELA TESTE 2;FGTS;10000.0;100000.0;4.0;2025-02-01
```

### 🔍 Verificar
- [ ] Download funcionou
- [ ] Encoding UTF-8 (acentos funcionam)
- [ ] Dados corretos
- [ ] Formato igual ao template

---

## 5️⃣ Teste: Importar Comissões (Criar Grupo)

### Setup
1. Criar CommissionGroup via API
2. Certificar que tabelas existem
3. Certificar que CommissionGroupByCompany existe (para gerente/líder)

### Arquivo: `test_comissoes.csv`
```csv
banco;convenio;tabela;comissao_lider;comissao_vendedor
<Nome Banco>;INSS;TABELA TESTE 1;1.5;2.0
<Nome Banco>;FGTS;TABELA TESTE 2;1.0;1.5
```

### Request
```bash
POST http://localhost:8000/api/payments/commission-groups/<group-id>/import-csv/
Content-Type: multipart/form-data
Authorization: Token <your-gerente-token>

Form Data:
- file: test_comissoes.csv
```

### ✅ Resultado Esperado
```json
{
  "created_count": 2,
  "updated_count": 0,
  "created_rules": [
    {"bank": "...", "table": "TABELA TESTE 1", "leader_rate": 1.5, "seller_rate": 2.0},
    {"bank": "...", "table": "TABELA TESTE 2", "leader_rate": 1.0, "seller_rate": 1.5}
  ],
  "updated_rules": [],
  "errors_count": 0,
  "errors": []
}
```

### 🔍 Verificar
- [ ] Status 201 Created
- [ ] created_count = 2
- [ ] CommissionRulesByUser criadas
- [ ] Associadas ao grupo correto
- [ ] Taxas corretas

---

## 6️⃣ Teste: Validação de Limites

### Setup
CommissionGroupByCompany com limite de 3.0% para uma tabela

### Arquivo: `test_comissoes_invalido.csv`
```csv
banco;convenio;tabela;comissao_lider;comissao_vendedor
<Nome Banco>;INSS;TABELA TESTE 1;2.0;2.0
```
(Soma = 4.0%, excede limite de 3.0%)

### Request
(Mesmo endpoint do teste anterior)

### ✅ Resultado Esperado
```json
{
  "created_count": 0,
  "updated_count": 0,
  "created_rules": [],
  "updated_rules": [],
  "errors_count": 1,
  "errors": [
    "Linha 2: Soma das comissões (4.0%) excede o limite da promotora (3.0%) para tabela 'TABELA TESTE 1'"
  ],
  "detail": "Nenhuma regra foi criada/atualizada devido aos erros encontrados."
}
```

### 🔍 Verificar
- [ ] Status 400 Bad Request
- [ ] Erro detalhado com linha específica
- [ ] Nenhuma regra criada
- [ ] Mensagem clara sobre o limite

---

## 7️⃣ Teste: Normalização de Nomes

### Arquivo: `test_normalizacao.csv`
```csv
nome_no_banco;convenio;valor_minimo;valor_maximo;taxa_de_comissionamento;data_de_vigencia
Tábela com Açento;ÍÑSS;5000;50000;3.5;2025-01-01
  Tabela   Espaços  ;INSS  ;10000;100000;4.0;2025-02-01
```

### ✅ Resultado Esperado
- Tabela 1: nome normalizado para `TABELA COM ACENTO`, convênio `INSS`
- Tabela 2: nome normalizado para `TABELA ESPACOS`, convênio `INSS`

### 🔍 Verificar
- [ ] Acentos removidos corretamente
- [ ] Espaços extras removidos
- [ ] Tudo em maiúsculas
- [ ] Caracteres especiais removidos

---

## 8️⃣ Teste: Exportar Template de Comissões

### Request (como Admin)
```bash
GET http://localhost:8000/api/payments/commission-groups/export-csv-template/
Authorization: Token <your-admin-token>
```

### ✅ Resultado Esperado (Admin)
- CSV com **todas** as tabelas ativas
- Colunas de comissão vazias (para preencher)

### Request (como Gerente)
```bash
GET http://localhost:8000/api/payments/commission-groups/export-csv-template/
Authorization: Token <your-gerente-token>
```

### ✅ Resultado Esperado (Gerente)
- CSV com apenas tabelas do CommissionGroupByCompany da empresa
- Filtragem correta por empresa

### 🔍 Verificar
- [ ] Admin vê todas as tabelas
- [ ] Gerente vê apenas tabelas da empresa
- [ ] Formato correto
- [ ] Pronto para preencher comissões

---

## 9️⃣ Teste: Listar Tabelas por Banco

### Request
```bash
GET http://localhost:8000/api/bank/tables/by-bank/<bank-id>/
Authorization: Token <your-token>
```

### ✅ Resultado Esperado
```json
{
  "bank": {
    "id": "...",
    "name": "Banco Teste"
  },
  "tables": [
    {"id": "...", "name_in_bank": "TABELA TESTE 1", ...},
    {"id": "...", "name_in_bank": "TABELA TESTE 2", ...}
  ],
  "count": 2
}
```

### 🔍 Verificar
- [ ] Apenas tabelas do banco especificado
- [ ] Ordenadas por convênio e nome
- [ ] Informações completas de cada tabela
- [ ] Count correto

---

## 🔟 Teste: Erros e Validações

### 10.1 CSV com Formato Inválido
```csv
nome;convenio;valor
Tabela;INSS;5000
```
(Faltam campos)

### ✅ Esperado
```json
{
  "errors": ["Linha 2: Dados insuficientes (esperado 6 campos, encontrado 3)"]
}
```

### 10.2 CSV com Data Inválida
```csv
nome_no_banco;convenio;valor_minimo;valor_maximo;taxa_de_comissionamento;data_de_vigencia
Tabela;INSS;5000;50000;3.5;32/13/2025
```

### ✅ Esperado
```json
{
  "errors": ["Linha 2: Formato de data inválido '32/13/2025'"]
}
```

### 10.3 CSV com Valor Numérico Inválido
```csv
nome_no_banco;convenio;valor_minimo;valor_maximo;taxa_de_comissionamento;data_de_vigencia
Tabela;INSS;abc;50000;3.5;2025-01-01
```

### ✅ Esperado
```json
{
  "errors": ["Linha 2: Erro nos valores numéricos - ..."]
}
```

---

## 📋 Checklist Final

### Funcionalidades Básicas
- [ ] Criar tabelas via CSV
- [ ] Atualizar tabelas via CSV
- [ ] Exportar tabelas para CSV
- [ ] Visualizar histórico de tabelas
- [ ] Listar tabelas por banco
- [ ] Exportar template de comissões
- [ ] Importar comissões via CSV

### Validações
- [ ] Normalização de nomes funciona
- [ ] Validação de limites funciona
- [ ] Erros são reportados corretamente
- [ ] Encoding UTF-8 funciona

### Permissões
- [ ] Admin pode fazer tudo
- [ ] Gerente vê apenas sua empresa
- [ ] Líder tem restrições corretas
- [ ] Validações de empresa funcionam

### Edge Cases
- [ ] CSV vazio
- [ ] CSV com apenas cabeçalho
- [ ] CSV com linhas duplicadas
- [ ] CSV com nomes muito longos
- [ ] CSV com caracteres especiais
- [ ] Banco inexistente
- [ ] Grupo inexistente

---

## 🐛 Problemas Comuns

### "Banco não encontrado"
→ Verificar UUID do banco correto no request

### "Encoding error"
→ Arquivo CSV deve ser UTF-8 com BOM

### "Limite excedido"
→ Verificar CommissionGroupByCompany da empresa

### "Tabela não encontrada" (ao importar comissões)
→ Tabela deve existir antes de configurar comissões

### "Permission denied"
→ Verificar role do usuário e token de autenticação

---

## 📊 Relatório de Teste

### Template
```markdown
## Teste Executado: [Nome do Teste]
**Data:** [Data]
**Executor:** [Nome]
**Ambiente:** [Dev/Staging/Prod]

### Resultado
- [ ] ✅ Passou
- [ ] ❌ Falhou
- [ ] ⚠️ Com ressalvas

### Detalhes
[Descrever o que aconteceu]

### Evidências
[Screenshots, logs, etc]

### Observações
[Notas adicionais]
```

---

## 🎯 Critérios de Aceitação

Para aprovar esta feature, **TODOS** os testes 1-9 devem passar sem erros.

**Feature está pronta quando:**
- ✅ Todos os endpoints respondem corretamente
- ✅ Validações funcionam como esperado
- ✅ Histórico é registrado corretamente
- ✅ Permissões são respeitadas
- ✅ Erros são tratados adequadamente
- ✅ Normalização funciona
- ✅ Exportação/importação sem perda de dados

---

**Branch:** `feature/csv-tables-import`
**Data:** 28/04/2026
