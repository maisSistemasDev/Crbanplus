# Campo Document da Company

## Visão Geral

O modelo `Company` (Corban) suporta tanto **Pessoa Física (PF)** quanto **Pessoa Jurídica (PJ)**. Por isso, o campo que antes era `cnpj` foi substituído por `document` para ser mais genérico.

## Campos Relacionados

### `person_type` (obrigatório)
- **Tipo**: String com 2 caracteres
- **Opções**: 
  - `'PF'` - Pessoa Física
  - `'PJ'` - Pessoa Jurídica
- **Default**: `'PJ'`

### `document` (obrigatório, único)
- **Tipo**: String com até 18 caracteres
- **Conteúdo**: CPF (11 dígitos) ou CNPJ (14 dígitos)
- **Formato**: Apenas números, sem pontuação
- **Restrição**: Valor único no banco de dados

## Validação

O modelo valida automaticamente o tamanho do documento baseado no tipo de pessoa:

- **PF**: O documento deve ter exatamente 11 dígitos (CPF)
- **PJ**: O documento deve ter exatamente 14 dígitos (CNPJ)

### Exemplo de Validação

```python
# Pessoa Jurídica - OK
company = Company(
    name="Auto Promotora Ltda",
    person_type="PJ",
    document="51057418000176"  # 14 dígitos
)
company.save()  # ✓ Sucesso

# Pessoa Física - OK
company = Company(
    name="João Silva",
    person_type="PF",
    document="12345678901"  # 11 dígitos
)
company.save()  # ✓ Sucesso

# Pessoa Jurídica com CPF - ERRO
company = Company(
    name="Empresa XYZ",
    person_type="PJ",
    document="12345678901"  # 11 dígitos
)
company.save()  # ✗ ValidationError: CNPJ deve ter 14 dígitos

# Pessoa Física com CNPJ - ERRO
company = Company(
    name="Maria Santos",
    person_type="PF",
    document="51057418000176"  # 14 dígitos
)
company.save()  # ✗ ValidationError: CPF deve ter 11 dígitos
```

## API REST

### Criar Company via API

```json
POST /api/companies/

{
  "name": "Auto Promotora Ltda",
  "trading_name": "Auto Promotora",
  "person_type": "PJ",
  "document": "51057418000176",
  "email": "contato@autopromotor.com.br"
}
```

### Respostas de Erro

#### Documento não fornecido
```json
{
  "document": ["Este campo é obrigatório."]
}
```

#### Documento duplicado
```json
{
  "document": ["Corban com este CPF/CNPJ já existe."]
}
```

#### Tamanho inválido
```json
{
  "document": ["CPF deve ter 11 dígitos"]
}
```

ou

```json
{
  "document": ["CNPJ deve ter 14 dígitos"]
}
```

## Migração de Dados

Se você tinha dados anteriores com o campo `cnpj`, a migração `0004` automaticamente:
1. Remove o campo `cnpj`
2. Adiciona o campo `document`
3. Adiciona o campo `person_type` (default: 'PJ')

**IMPORTANTE**: Esta migração requer que o banco de dados esteja limpo (sem Companies existentes) ou que você forneça um valor único para cada documento durante a migração.

## Scripts de Criação

### create_superuser.py
```python
company, created = Company.objects.get_or_create(
    document='51057418000176',  # CNPJ sem formatação
    defaults={
        'name': 'Auto Promotora',
        'trading_name': 'Auto Promotora',
        'person_type': 'PJ',
        'email': email,
        'is_active': True
    }
)
```

### add_superuser.py
```bash
python add_superuser.py \
  --cpf 12345678901 \
  --email admin@corban.com \
  --password senha123 \
  --document 51057418000176 \
  --person-type PJ
```

## Django Admin

No Django Admin, o campo `document` aparece como **"CPF/CNPJ"** e aceita entrada manual. O sistema:
- Remove automaticamente caracteres não numéricos antes de salvar
- Valida o tamanho com base no `person_type`
- Garante unicidade

## Dicas

1. **Sempre remova a formatação**: Envie apenas números
   - ✓ `"51057418000176"`
   - ✗ `"51.057.418/0001-76"`

2. **Escolha o person_type correto**: Isso afeta a validação do documento
   - PJ: 14 dígitos (CNPJ)
   - PF: 11 dígitos (CPF)

3. **Documents devem ser únicos**: Não é possível ter duas Companies com o mesmo documento

4. **User.cpf é diferente**: O campo `cpf` do model `User` sempre espera um CPF (11 dígitos), independente do tipo da Company
