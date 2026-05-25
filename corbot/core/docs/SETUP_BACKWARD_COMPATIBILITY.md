# Exemplo: Setup com `cnpj` (formato legado)

O endpoint de setup agora suporta tanto `cnpj` quanto `document` para retrocompatibilidade.

## Payload com `cnpj` (formato antigo)

```json
{
  "company": {
    "name": "50.592.390 Daniel",
    "cnpj": "50.592.390/0001-04",
    "email": "maissitemasdev@gmail.com"
  },
  "user": {
    "cpf": "130.074.817-67",
    "email": "maissitemasdev@gmail.com",
    "first_name": "Daniel",
    "last_name": "Proença",
    "password": "rosacruz89D!"
  }
}
```

## Payload com `document` (formato atual)

```json
{
  "company": {
    "name": "Auto Promotora Ltda",
    "document": "50592390000104",
    "person_type": "PJ",
    "email": "contato@autopromotor.com.br"
  },
  "user": {
    "cpf": "13007481767",
    "email": "admin@autopromotor.com.br",
    "first_name": "Administrador",
    "last_name": "Sistema",
    "password": "SenhaSegura123!"
  }
}
```

## O que o sistema faz automaticamente

1. **Conversão de `cnpj` para `document`**: Se você enviar `cnpj`, o sistema automaticamente converte para `document`
2. **Remoção de formatação**: Pontos, traços e barras são removidos automaticamente de `document` e `cpf`
3. **Default de `person_type`**: Se não fornecido, assume `PJ` (Pessoa Jurídica)

## Exemplos de conversão

| Entrada | Processamento | Resultado |
|---------|---------------|-----------|
| `"cnpj": "50.592.390/0001-04"` | Remove formatação + converte para `document` | `"document": "50592390000104"` |
| `"document": "50.592.390/0001-04"` | Remove formatação | `"document": "50592390000104"` |
| `"cpf": "130.074.817-67"` | Remove formatação | `"cpf": "13007481767"` |

## Resposta de sucesso

```json
{
  "detail": "Sistema inicializado com sucesso.",
  "company_id": "uuid-da-company",
  "user_id": 1
}
```

## Dica

Embora o sistema aceite formatação e o campo `cnpj`, recomendamos usar o formato atual:
- Use `document` em vez de `cnpj`
- Envie apenas números (sem formatação)
- Especifique `person_type` explicitamente

Isso torna seu código mais claro e evita dependência de conversões automáticas.
