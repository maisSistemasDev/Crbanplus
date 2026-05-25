# Feature: Importação de Tabelas e Grupos de Comissionamento via CSV

Branch: `feature/csv-tables-import`

## Resumo das Alterações

Esta feature adiciona funcionalidades completas para importação e gestão de tabelas e grupos de comissionamento via arquivos CSV, incluindo:

1. **Histórico de atualizações de tabelas**
2. **Importação CSV inteligente** (criar ou atualizar)
3. **Normalização de nomes** (remove acentos, padroniza)
4. **Exportação de templates CSV**
5. **Importação de grupos de comissionamento via CSV**

---

## Arquivos Modificados

### 1. Models (`corbot/bank/models.py`)

#### Novo Modelo: `TableHistory`
Armazena histórico completo de alterações em tabelas:
- Ação realizada (CREATE, UPDATE, CSV_IMPORT, CSV_UPDATE)
- Usuário responsável
- Valores anteriores e novos
- Campos alterados
- Observações

#### Nova Função: `normalize_name()`
Normaliza nomes removendo acentos, convertendo para maiúsculas e removendo caracteres especiais.

### 2. Views (`corbot/bank/views.py`)

#### `TableCreateBatchView` (Melhorada)
**Endpoint:** `POST /api/bank/tables/create-batch/`

**Funcionalidades:**
- Importa CSV com tabelas
- **Cria novas tabelas** ou **atualiza existentes** (por nome normalizado + banco + convênio)
- Registra histórico de todas as operações
- Normaliza nomes automaticamente
- Suporta múltiplos formatos de data

**Formato CSV:**
```csv
nome_no_banco;convenio;valor_minimo;valor_maximo;taxa_de_comissionamento;data_de_vigencia
Tabela Exemplo 1;INSS;1000.00;50000.00;2.5;2025-01-01
Tabela Exemplo 2;FGTS;5000.00;100000.00;3.0;2025-01-01
```

**Resposta:**
```json
{
  "created_count": 1,
  "updated_count": 1,
  "created_tables": [...],
  "updated_tables": [...],
  "errors_count": 0,
  "errors": []
}
```

#### `TableExportCSVView` (Nova)
**Endpoint:** `GET /api/bank/tables/export-csv/<bank_id>/`

Exporta tabelas de um banco específico para CSV, permitindo download, edição e re-upload.

#### `TablesByBankView` (Nova)
**Endpoint:** `GET /api/bank/tables/by-bank/<bank_id>/`

Lista tabelas filtradas por banco, útil para interface de seleção.

#### `TableHistoryView` (Nova)
**Endpoint:** `GET /api/bank/tables/<table_id>/history/`

Retorna histórico completo de alterações de uma tabela específica.

### 3. Views de Commission Group (`corbot/payments/views/commission_group_csv.py` - Novo Arquivo)

#### `CommissionGroupExportCSVView`
**Endpoint:** `GET /api/payments/commission-groups/export-csv-template/`

Exporta template CSV com todas as tabelas disponíveis para configurar comissões.

**Lógica de Permissões:**
- **Admin:** Vê todas as tabelas
- **Gerente/Líder:** Vê apenas tabelas do CommissionGroupByCompany da empresa

**Formato CSV:**
```csv
banco;convenio;tabela;comissao_lider;comissao_vendedor
Banco ABC;INSS;Tabela 1;;
Banco XYZ;FGTS;Tabela 2;;
```

#### `CommissionGroupImportCSVView`
**Endpoint:** `POST /api/payments/commission-groups/<group_id>/import-csv/`

Importa regras de comissionamento via CSV para um grupo específico.

**Funcionalidades:**
- Cria ou atualiza regras de comissão
- Valida limites (soma líder + vendedor não pode exceder limite da promotora)
- Normaliza nomes para busca
- Registra histórico completo

**Formato CSV:**
```csv
banco;convenio;tabela;comissao_lider;comissao_vendedor
Banco ABC;INSS;Tabela 1;1.5;1.0
Banco XYZ;FGTS;Tabela 2;2.0;0.5
```

### 4. URLs

#### Bank URLs (`corbot/bank/urls.py`)
```python
path('tables/<uuid:table_id>/history/', TableHistoryView.as_view()),
path('tables/create-batch/', TableCreateBatchView.as_view()),
path('tables/export-csv/', TableExportCSVView.as_view()),
path('tables/export-csv/<uuid:bank_id>/', TableExportCSVView.as_view()),
path('tables/by-bank/<uuid:bank_id>/', TablesByBankView.as_view()),
```

#### Payments URLs (`corbot/payments/urls.py`)
```python
path('commission-groups/<int:group_id>/import-csv/', CommissionGroupImportCSVView.as_view()),
path('commission-groups/export-csv-template/', CommissionGroupExportCSVView.as_view()),
```

### 5. Admin (`corbot/bank/admin.py`)

Novo admin para `TableHistory`:
- Visualização somente leitura
- Filtros por ação e data
- Busca por tabela, usuário e observações

---

## Migrations Necessárias

Após merge da branch, executar:

```bash
# Via Docker
docker exec corbot_web python3 manage.py makemigrations bank
docker exec corbot_web python3 manage.py migrate

# Ou localmente (com virtualenv ativado)
python3 manage.py makemigrations bank
python3 manage.py migrate
```

---

## Fluxo de Uso

### 1. Criar/Atualizar Tabelas via CSV

**Passo 1:** Baixar template CSV
```bash
GET /api/bank/tables/download-example/
```

Ou exportar tabelas existentes de um banco:
```bash
GET /api/bank/tables/export-csv/<bank_id>/
```

**Passo 2:** Editar CSV
```csv
nome_no_banco;convenio;valor_minimo;valor_maximo;taxa_de_comissionamento;data_de_vigencia
Nova Tabela;INSS;1000;50000;2.5;2025-01-01
Tabela Existente;FGTS;5000;100000;3.0;2025-02-01
```

**Passo 3:** Upload
```bash
POST /api/bank/tables/create-batch/
Content-Type: multipart/form-data

file: arquivo.csv
bank_id: <uuid-do-banco>
```

**Resultado:**
- Se tabela **não existe** (por nome normalizado): **cria nova**
- Se tabela **existe**: **atualiza** porcentagem e vigência
- Registra histórico completo em `TableHistory`

### 2. Criar Grupo de Comissionamento via CSV

**Passo 1:** Criar o grupo via API normal
```bash
POST /api/payments/commission-groups/
{
  "name": "Grupo Vendedores A",
  "description": "...",
  "company": "<company-id>"
}
```

**Passo 2:** Baixar template CSV com tabelas disponíveis
```bash
GET /api/payments/commission-groups/export-csv-template/
```

**Passo 3:** Editar CSV com comissões
```csv
banco;convenio;tabela;comissao_lider;comissao_vendedor
Banco ABC;INSS;Tabela 1;1.5;1.0
Banco XYZ;FGTS;Tabela 2;2.0;0.5
```

**Passo 4:** Upload
```bash
POST /api/payments/commission-groups/<group-id>/import-csv/
Content-Type: multipart/form-data

file: comissoes.csv
```

**Validações:**
- Banco, convênio e tabela devem existir
- Soma (líder + vendedor) não pode exceder limite da promotora
- Nomes são normalizados para busca

### 3. Visualizar Histórico de Tabela

```bash
GET /api/bank/tables/<table-id>/history/
```

**Resposta:**
```json
{
  "table": {...},
  "history": [
    {
      "id": "uuid",
      "action": "CSV_UPDATE",
      "user": {"id": "uuid", "name": "João Silva"},
      "field_changes": {"commission_rate": true, "vigency_date": true},
      "previous_values": {"commission_rate": "2.0", "vigency_date": "2024-01-01"},
      "new_values": {"commission_rate": "2.5", "vigency_date": "2025-01-01"},
      "notes": "Atualização via CSV - Linha 5",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

---

## Testes Recomendados

### 1. Importação de Tabelas
- [ ] CSV com tabelas novas (deve criar)
- [ ] CSV com tabelas existentes (deve atualizar)
- [ ] CSV com mix de novas e existentes
- [ ] CSV com nomes acentuados (deve normalizar)
- [ ] CSV com dados inválidos (deve reportar erros)
- [ ] CSV com diferentes formatos de data

### 2. Importação de Comissões
- [ ] CSV válido (deve criar/atualizar regras)
- [ ] CSV excedendo limite da promotora (deve rejeitar)
- [ ] CSV com banco/tabela inexistente (deve reportar erro)
- [ ] Gerente tentando importar para grupo de outra empresa (deve rejeitar)

### 3. Histórico
- [ ] Verificar registro de criação
- [ ] Verificar registro de atualização
- [ ] Verificar registro de importação CSV
- [ ] Verificar campos alterados corretamente

### 4. Exportação
- [ ] Exportar tabelas de um banco
- [ ] Exportar template de comissões (admin)
- [ ] Exportar template de comissões (gerente - deve ver apenas tabelas da empresa)

---

## Estrutura de Dados

### TableHistory
```python
{
    "id": "uuid",
    "table": "ForeignKey(Table)",
    "action": "CSV_UPDATE",  # CREATE, UPDATE, CSV_IMPORT, CSV_UPDATE
    "user": "ForeignKey(User, nullable)",
    "field_changes": {"commission_rate": true, ...},
    "previous_values": {"commission_rate": "2.0", ...},
    "new_values": {"commission_rate": "2.5", ...},
    "notes": "string",
    "created_at": "datetime"
}
```

---

## Próximos Passos

1. **Executar migrations** após merge
2. **Testar endpoints** em desenvolvimento
3. **Atualizar frontend** para:
   - Adicionar botão de upload CSV na criação de tabelas
   - Adicionar botão de download template
   - Adicionar interface de importação de comissões ao criar grupo
   - Exibir histórico de alterações de tabelas
4. **Documentar na API docs** (Swagger/Redoc)

---

## Notas Técnicas

### Normalização de Nomes
A função `normalize_name()` garante que tabelas/convênios com nomes similares sejam identificadas como iguais:
- `"Tabela INSS"` → `"TABELA INSS"`
- `"Tábela INSS"` → `"TABELA INSS"` (remove acento)
- `"Tabela  INSS"` → `"TABELA INSS"` (remove espaços extras)

### Validação Cascata
- **Promotora → Empresa:** `CommissionGroupByCompany.commission_rate` define limite máximo
- **Empresa → Vendedores:** Soma de `leader_rate + seller_rate` não pode exceder limite da promotora
- Validação automática no import CSV

### Performance
- Queries otimizadas com `select_related()` e `prefetch_related()`
- Busca por nome normalizado usa `__iexact` (case-insensitive)
- Histórico indexado por `created_at` para buscas rápidas

---

## Autor
**Branch:** `feature/csv-tables-import`
**Data:** 28/04/2026
