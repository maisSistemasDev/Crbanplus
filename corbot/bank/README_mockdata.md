# Mockdata dos Bancos Nacionais do Brasil

Este diretório contém dados mockados dos principais bancos nacionais do Brasil com seus respectivos códigos FEBRABAN.

## Arquivos

### `mockdata_bancos.py`
Contém a lista completa dos bancos nacionais com:
- **Nome**: Nome oficial do banco
- **Código**: Código FEBRABAN (identificação única)
- **Ativo**: Status do banco (ativo/inativo)

### `populate_banks.py`
Script para popular o banco de dados com os bancos nacionais.

## Como usar

### 1. Importar os dados diretamente

```python
from bank.mockdata_bancos import BANCOS_NACIONAIS, get_banco_por_codigo, get_bancos_ativos

# Obter todos os bancos
todos_bancos = BANCOS_NACIONAIS

# Obter banco por código
banco_bb = get_banco_por_codigo("001")  # Banco do Brasil

# Obter apenas bancos ativos
bancos_ativos = get_bancos_ativos()
```

### 2. Popular o banco de dados

```bash
# Executar o script interativo
python bank/populate_banks.py

# Ou usar o Django shell
python manage.py shell
```

```python
# No Django shell
from bank.populate_banks import populate_banks
populate_banks()
```

### 3. Usar em views ou serializers

```python
from bank.mockdata_bancos import get_banco_por_codigo, get_nomes_bancos

# Em uma view
def get_bank_info(request, code):
    banco = get_banco_por_codigo(code)
    if banco:
        return JsonResponse(banco)
    return JsonResponse({"error": "Banco não encontrado"})

# Lista de todos os nomes
nomes_bancos = get_nomes_bancos()
```

## Principais Bancos Incluídos

- **Banco do Brasil** (001)
- **Caixa Econômica Federal** (104)
- **Banco Bradesco** (237)
- **Banco Itaú** (341)
- **Banco Santander** (033)
- **Banco BTG Pactual** (208)
- **Banco Nubank** (260)
- **Banco Inter** (077)
- **Banco C6** (336)
- **Banco PicPay** (380)
- E muitos outros...

## Funções Utilitárias

### `get_banco_por_codigo(codigo)`
Retorna o banco correspondente ao código informado.

### `get_banco_por_nome(nome)`
Retorna o banco correspondente ao nome informado (busca parcial).

### `get_bancos_ativos()`
Retorna apenas os bancos marcados como ativos.

### `get_codigos_bancos()`
Retorna apenas os códigos dos bancos.

### `get_nomes_bancos()`
Retorna apenas os nomes dos bancos.

## Exemplo de Uso Completo

```python
from bank.mockdata_bancos import (
    BANCOS_NACIONAIS,
    get_banco_por_codigo,
    get_banco_por_nome,
    get_bancos_ativos
)

# Buscar banco específico
banco_itau = get_banco_por_codigo("341")
print(f"Banco encontrado: {banco_itau['nome']}")

# Buscar por nome
banco_nubank = get_banco_por_nome("Nubank")
print(f"Código do Nubank: {banco_nubank['codigo']}")

# Listar todos os bancos ativos
bancos_ativos = get_bancos_ativos()
print(f"Total de bancos ativos: {len(bancos_ativos)}")

# Criar choices para formulários Django
BANK_CHOICES = [(banco["codigo"], banco["nome"]) for banco in BANCOS_NACIONAIS]
```

## Observações

- Os códigos são baseados no padrão FEBRABAN
- Alguns bancos podem ter códigos similares (ex: grupos bancários)
- O arquivo pode ser atualizado conforme novos bancos surgem no mercado
- Todos os bancos estão marcados como ativos por padrão 