# Exemplo: Criar Corban + Acesso Bancário

Base URL: `https://corbanplus.maisistemasdev.com`

Todos os endpoints abaixo exigem autenticação (JWT `Bearer` de um usuário `admin` da promotora, ou Api-Key com escopo correspondente).

## 1. Login (obter token)

```
POST https://corbanplus.maisistemasdev.com/api/token/
Content-Type: application/json
```

```json
{
  "cpf": "00000000000",
  "password": "senha_do_admin"
}
```

Resposta `200`:
```json
{
  "access": "eyJhbGciOiJIUzI1...",
  "refresh": "eyJhbGciOiJIUzI1..."
}
```

Use o `access` em todas as chamadas seguintes:
```
Authorization: Bearer <access>
```

---

## 2. Criar Corban (empresa) + usuário admin

O endpoint cria a empresa **e** o usuário `empresa_admin` na mesma chamada. O CPF/CNPJ de login do admin é sempre o `document` da empresa.

```
POST https://corbanplus.maisistemasdev.com/api/companies/
Authorization: Bearer <access>
Content-Type: application/json
```

```json
{
  "company": {
    "name": "Corban Exemplo Ltda",
    "trading_name": "Corban Exemplo",
    "person_type": "PJ",
    "document": "12345678000195",
    "email": "contato@corbanexemplo.com.br",
    "phone": "11999990000",
    "primary_color": "#1a56db",
    "city": "São Paulo",
    "state": "SP",
    "is_active": true
  },
  "admin_user": {
    "password": "SenhaForte@123",
    "email": "maria@corbanexemplo.com.br",
    "matricula": "MAT001"
  }
}
```

Resposta `201`:
```json
{
  "company": {
    "id": "uuid-do-corban",
    "name": "Corban Exemplo Ltda",
    "document": "12345678000195",
    "is_active": true
  },
  "admin_user": {
    "id": 42,
    "cpf": "12345678000195",
    "role": "empresa_admin",
    "company": "uuid-do-corban",
    "is_active": true
  }
}
```

> Guarde o `admin_user.id` (usado no passo 3) e o `company.id`.

> `admin_user` nesta chamada só aceita `password`, `email`, `matricula` e `certificado`. **Não aceita `extra_data`/`pix_key`** — para isso, use o passo 2.1 abaixo.

---

## 2.1. Adicionar chave PIX ao usuário (opcional)

A chave PIX não é um campo direto do usuário — ela fica em `extra_data`, e precisa ser enviada em uma chamada separada (na criação avulsa via `POST /api/users/` ou por `PATCH` no usuário já existente):

```
PATCH https://corbanplus.maisistemasdev.com/api/users/42/
Authorization: Bearer <access>
Content-Type: application/json
```

```json
{
  "extra_data": {
    "pix_key": "12345678901",
    "pix_type": "CPF",
    "phone": "11999999999"
  }
}
```

`pix_type` aceita: `CHAVE_ALEATORIA`, `EMAIL`, `CELULAR`, `CPF`, `CNPJ`.

---

## 3. Criar Acesso Bancário vinculado ao usuário do Corban

```
POST https://corbanplus.maisistemasdev.com/api/bank-accesses/
Authorization: Bearer <access>
Content-Type: application/json
```

```json
{
  "bank": "uuid-do-banco",
  "user": 42,
  "username": "maria.silva@bancoexemplo.com.br",
  "password": "SenhaDoBanco@123",
  "is_master": true,
  "is_active": true,
  "notes": "Acesso principal ao portal do banco parceiro",
  "link": "https://portal.bancoexemplo.com.br"
}
```

Resposta `201`:
```json
{
  "id": "uuid-do-acesso",
  "bank": "uuid-do-banco",
  "bank_name": "Banco Exemplo",
  "user": 42,
  "user_name": "Maria Silva",
  "username": "maria.silva@bancoexemplo.com.br",
  "is_master": true,
  "is_active": true
}
```

### Observações

- `user` é o **id numérico** do usuário (não o UUID da empresa).
- `bank` é o **UUID** do banco — liste com `GET /api/banks/`.
- Se `user.role == empresa_admin`, o backend força `is_master: true` mesmo que você envie `false`.
- Não é possível repetir o mesmo `username` no mesmo `bank` (constraint única).

---

## Resumo da cadeia

```
POST /api/token/            → access token (autenticação)
POST /api/companies/        → cria Corban + admin_user (id, company.id)
PATCH /api/users/{id}/      → (opcional) adiciona extra_data (pix_key, phone, etc.)
POST /api/bank-accesses/    → acesso vinculado ao admin_user.id
```
