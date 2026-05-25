# Core - Corbot

O módulo Core contém as abstrações e funcionalidades básicas do sistema Corbot, incluindo:

- Modelo de usuário personalizado com hierarquia (Gerente, Líder, Vendedor)
- Autenticação por CPF
- Armazenamento de dados adicionais (RG, CPF, etc.)
- Permissões baseadas em papéis
- Autenticação JWT
- Modelos abstratos para reutilização

## Hierarquia de Usuários

O sistema possui a seguinte hierarquia de usuários:

1. **Gerente**: Pode criar e editar dados dos vendedores, tabelas e grupos. Tem acesso à produtividade de toda a equipe.
2. **Líder**: Pode ser criado pelo gerente e também pode ter vendedores. Os vendedores podem ser visualizados e movidos de líder pelo gerente. Tem acesso à produtividade de seus vendedores.
3. **Vendedor**: Tem acesso ao sistema, pode visualizar sua produtividade e solicitar acessos aos sistemas das bancarizadoras parceiras.

## Modelos

### User
- Modelo de usuário personalizado que usa CPF como identificador único
- Campos principais: cpf, email, first_name, last_name, role, leader

### ExtraData
- Modelo para armazenar dados adicionais do usuário
- Campos: rg, rg_emission_date, rg_emission_organ, birth_date, phone, address, city, state, zip_code

## Endpoints da API

### Autenticação

- `POST /api/token/`: Obter token JWT
- `POST /api/token/refresh/`: Renovar token JWT

### Usuários

- `GET /api/users/`: Listar usuários (filtrados por hierarquia)
- `POST /api/users/`: Criar novo usuário (apenas Gerente)
- `GET /api/users/{id}/`: Obter detalhes de um usuário
- `PUT/PATCH /api/users/{id}/`: Atualizar usuário (apenas Gerente)
- `DELETE /api/users/{id}/`: Excluir usuário (apenas Gerente)
- `GET /api/users/vendedores/`: Listar vendedores (Gerente vê todos, Líder vê apenas os seus)
- `GET /api/users/lideres/`: Listar líderes (apenas Gerente)
- `POST /api/users/{id}/change_leader/`: Alterar líder de um vendedor (apenas Gerente)
