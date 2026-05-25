# Git Commit Summary

## Branch: feature/csv-tables-import

### Arquivos Novos
1. `corbot/payments/views/commission_group_csv.py` - Views para import/export CSV de grupos
2. `FEATURE_CSV_TABLES_IMPORT.md` - Documentação completa da feature
3. `exemplo_import_tabelas.csv` - Exemplo de CSV para importar tabelas
4. `exemplo_import_comissoes.csv` - Exemplo de CSV para importar comissões

### Arquivos Modificados

#### Models
- `corbot/bank/models.py`
  - Adicionado: `normalize_name()` - função para normalizar nomes
  - Adicionado: `TableHistory` - modelo para histórico de alterações

#### Views
- `corbot/bank/views.py`
  - Modificado: `TableCreateBatchView` - agora cria OU atualiza tabelas
  - Adicionado: `TableExportCSVView` - exportar tabelas para CSV
  - Adicionado: `TablesByBankView` - listar tabelas por banco
  - Adicionado: `TableHistoryView` - visualizar histórico de tabela

#### Admin
- `corbot/bank/admin.py`
  - Adicionado: `TableHistoryAdmin` - admin para histórico (read-only)

#### URLs
- `corbot/bank/urls.py`
  - Adicionadas rotas para novas views
- `corbot/payments/urls.py`
  - Adicionadas rotas para import/export CSV de comissões

### Comandos para Commit

```bash
# Verificar status
git status

# Adicionar arquivos
git add corbot/bank/models.py
git add corbot/bank/views.py
git add corbot/bank/admin.py
git add corbot/bank/urls.py
git add corbot/payments/views/commission_group_csv.py
git add corbot/payments/urls.py
git add FEATURE_CSV_TABLES_IMPORT.md
git add exemplo_import_tabelas.csv
git add exemplo_import_comissoes.csv

# Commit
git commit -m "feat: Adiciona importação CSV de tabelas e grupos de comissionamento

- Adiciona modelo TableHistory para rastrear alterações
- Implementa importação CSV inteligente (cria ou atualiza)
- Adiciona normalização de nomes (remove acentos, padroniza)
- Implementa exportação de templates CSV
- Adiciona importação de grupos de comissionamento via CSV
- Adiciona endpoint para listar tabelas por banco
- Adiciona endpoint para visualizar histórico de tabelas
- Adiciona validação cascata de limites de comissão

Closes #<issue-number>"

# Push para remote
git push origin feature/csv-tables-import
```

### Migrations

Após merge para main/develop, executar:

```bash
docker exec corbot_web python3 manage.py makemigrations bank
docker exec corbot_web python3 manage.py migrate
```

### Mensagem de Commit Detalhada

```
feat: Adiciona importação CSV de tabelas e grupos de comissionamento

BREAKING CHANGES:
- Novo modelo TableHistory requer migration

FEATURES:
- Importação CSV de tabelas (cria ou atualiza por nome normalizado)
- Histórico completo de alterações em tabelas
- Exportação de CSV com templates editáveis
- Importação CSV para grupos de comissionamento
- Normalização automática de nomes (remove acentos)
- Validação cascata de limites de comissão

ENDPOINTS NOVOS:
- POST /api/bank/tables/create-batch/         (melhorado)
- GET  /api/bank/tables/export-csv/<bank_id>/
- GET  /api/bank/tables/by-bank/<bank_id>/
- GET  /api/bank/tables/<table_id>/history/
- GET  /api/payments/commission-groups/export-csv-template/
- POST /api/payments/commission-groups/<group_id>/import-csv/

DOCUMENTATION:
- Documentação completa em FEATURE_CSV_TABLES_IMPORT.md
- Exemplos de CSV incluídos

TECHNICAL:
- Função normalize_name() para padronização
- Queries otimizadas com select_related()
- Validação de limites em cascata
- Histórico imutável (apenas leitura no admin)
```

### Pull Request Template

```markdown
## Descrição
Implementa funcionalidade completa de importação/exportação CSV para tabelas e grupos de comissionamento, incluindo:
- Histórico de alterações
- Normalização de nomes
- Validação cascata de limites

## Tipo de Mudança
- [x] Nova feature
- [ ] Bug fix
- [ ] Breaking change
- [x] Requer migration

## Checklist
- [x] Código segue padrões do projeto
- [x] Adicionada documentação
- [x] Exemplos de CSV incluídos
- [ ] Testes executados
- [ ] Migrations testadas

## Como Testar
1. Executar migrations: `docker exec corbot_web python3 manage.py migrate`
2. Baixar template CSV: `GET /api/bank/tables/download-example/`
3. Preencher CSV e fazer upload via POST
4. Verificar histórico: `GET /api/bank/tables/<id>/history/`

## Screenshots/GIFs
(Adicionar prints do admin e dos CSVs)

## Documentação
Ver `FEATURE_CSV_TABLES_IMPORT.md` para documentação completa

## Relacionado
Closes #<issue-number>
```
