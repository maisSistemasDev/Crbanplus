# Plan: Refatorar Nomenclatura Promotora/Corban e Adicionar Campos

## Status: Design - Plano Detalhado

### Contexto Atual

**Estrutura Identificada**:
- Company model: name, trading_name, cnpj (único), logo, cores, settings, contatos, endereço
- User model: cpf (USERNAME_FIELD), email, first_name, last_name, role, company (FK nullable), leader
- Roles: admin (promotora, company=None), empresa_admin, gerente, lider, vendedor
- Setup: Cria 1 Company + 1 Admin (role=admin, company=None, is_superuser=True)
- NO automatic user creation ao criar Company

**Terminologia Atual**: "Empresa" usado em:
- Frontend: 50+ ocorrências (labels, títulos, mensagens, filtros)
- Backend: role EMPRESA_ADMIN, serializers, permissions
- Menu: "Empresas", "Minha Empresa", "Por Empresa"

### Requisitos do Usuário

1. ✅ Renomear "Empresa" → "Corban" (exceto promotora principal)
2. ✅ Corban pode ser PF ou PJ (campo person_type com validação)
3. ✅ Ao criar corban, criar automaticamente usuário EMPRESA_ADMIN usando documento do corban
4. ✅ Login pode ser CPF ou CNPJ (buscar usuário por documento no backend)
5. ✅ Adicionar campos: certificado (string alfanumérica, opcional) e matrícula (única por empresa, opcional e editável; se não informada, usa CPF do usuário)
6. ✅ Nomenclatura clara: Promotora (principal) vs Corban (subordinadas)

### Decisões Tomadas

**Q1: Tipo PF/PJ** → Adicionar campo `person_type` ('PF'/'PJ') e validar documento conforme tipo
**Q2: Criação Automática** → Criar automaticamente usando documento do corban como CPF/CNPJ do usuário
**Q3: Dados Usuário** → CPF/CNPJ=documento corban, Email=email corban, Nome=nome corban, Senha=gerada (forçar reset)
**Q4: Login** → Permitir login com CPF ou CNPJ (backend busca pelo documento)
**Q5: Certificado/Matrícula** → Todos os usuários, opcional e editável
**Q6: Certificado** → Texto livre alfanumérico
**Q7: Matrícula** → Única dentro da empresa; se não informada, usa CPF do usuário como default

---

## Plano Detalhado

### Fase 1: Modelo e Database (Backend)

**Step 1.1: Atualizar Company Model**
- Adicionar campo `person_type` com choices ('PF', 'PJ')
- Renomear label `cnpj` → `document`
- Adicionar validação: se PF, validar CPF (11 dígitos); se PJ, validar CNPJ (14 dígitos)
- Atualizar `unique_together` ou constraint de unicidade
- Migration: adicionar person_type, renomear cnpj → document

**Step 1.2: Atualizar User Model**
- Adicionar campo `certificado` (CharField, max_length=100, blank=True, null=True)
- Adicionar campo `matricula` (CharField, max_length=50, blank=True, null=True, unique por empresa)
- **Default de matrícula**: Se não informada, usar o CPF do usuário como matrícula
- Implementar lógica no `save()` ou `clean()`: if not self.matricula: self.matricula = self.cpf
- Adicionar constraint de unicidade: `unique_together = [['company', 'matricula']]`
- Migration: adicionar certificado e matricula

**Step 1.3: Autenticação com CPF/CNPJ**
- Criar backend de autenticação customizado (inherit de ModelBackend)
- Override `authenticate()` para aceitar CPF ou CNPJ no campo username
- Normalizar documento (remover pontos, traços) antes de buscar
- Registrar backend em settings.py (`AUTHENTICATION_BACKENDS`)

**Step 1.4: Criação Automática de User ao Criar Company**
- Atualizar `CompanySerializer.create()` para criar empresa_admin automaticamente
- Lógica:
  1. Criar Company
  2. Gerar senha aleatória (12 caracteres: letras + números + símbolos)
  3. Criar User com: cpf/cnpj=document, email=company.email, first_name=company.name, role=empresa_admin, company=company_instance, is_active=False (forçar reset)
  4. Enviar email com senha temporária (opcional) ou registrar no log
- Adicionar flag `send_welcome_email` (default=False) no serializer para controlar envio

*Depende: Step 1.1, 1.2*

**Step 1.5: Atualizar Serializers**
- `CompanySerializer`: adicionar person_type, renomear cnpj → document, validação condicional
- `UserCreateSerializer`: adicionar certificado, matricula
- `UserSerializer`: adicionar certificado, matricula (read-only)
- Atualizar form_fields endpoints para incluir novos campos

*Depende: Step 1.1, 1.2*

### Fase 2: Nomenclatura Backend

**Step 2.1: Atualizar Labels e Mensagens (Backend)**
- Company model: verbose_name de "Empresa" → "Corban" (exceto setup)
- User model: role choice label "Administrador da Empresa" → "Administrador do Corban"
- Atualizar docstrings e comentários
- Não alterar nomes de variáveis/campos (apenas labels user-facing)

**Step 2.2: Atualizar Permissões e Messages**
- `IsEmpresaAdmin`: renomear docstring
- Error messages: substituir "empresa" → "corban" onde apropriado
- Toast/success messages nos serializers

*Pode ser feito em paralelo com Step 1*

### Fase 3: Frontend - Nomenclatura

**Step 3.1: Substituir "Empresa" → "Corban" (50+ ocorrências)**
- Arquivos principais:
  1. SidebarContent.tsx: "Empresas" → "Corbans", "Minha Empresa" → "Meu Corban", "Por Empresa" → "Por Corban"
  2. CompanyList.tsx: "Empresas" → "Corbans", "Nova Empresa" → "Novo Corban", "empresa encontrada" → "corban encontrado"
  3. CompanyForm.tsx: "Empresa" → "Corban" em títulos e toasts
  4. UserList.tsx: coluna "Empresa" → "Corban"
  5. CommissionList.tsx: filtro "Empresa" → "Corban", "Todas as Empresas" → "Todos os Corbans"
  6. ProposalListPage.tsx: coluna/filtro "Empresa" → "Corban"
  7. roles.ts: label "Admin. Empresa" → "Admin. Corban"
  8. CompanySelector.tsx: "empresas" → "corbans"
  9. Pages (*.astro): títulos com "Empresa" → "Corban"

**Step 3.2: Manter "Promotora" Onde Apropriado**
- SetupPage.tsx: manter "Dados da Promotora", "Administrador da Promotora"
- Adicionar distinção visual/texto: "Corban (subordinado à promotora)"

*Pode ser feito em paralelo com Fase 2*

### Fase 4: Frontend - Novos Campos

**Step 4.1: Formulário de Company**
- Adicionar campo `person_type` (radio buttons: PF / PJ)
- Alterar label CNPJ → "CPF/CNPJ" ou "Documento"
- Máscara condicional: se PF → 999.999.999-99, se PJ → 99.999.999/9999-99
- Validação no frontend (formato correto)

**Step 4.2: Formulário de User**
- Adicionar campo `certificado` (input text, opcional)
- Adicionar campo `matricula` (input text, opcional, editável)
- **Placeholder/hint**: "Deixe em branco para usar o CPF como matrícula"
- Validação: matrícula única dentro da empresa (backend valida, frontend mostra erro)

**Step 4.3: Atualizar Listas e Displays**
- UserList.tsx: adicionar colunas opcionais para certificado e matrícula (hidden por default, toggle)
- CompanyList.tsx: mostrar badge com tipo (PF/PJ) ao lado do nome

*Depende: Fase 1 concluída (migrations aplicadas)*

### Fase 5: Testes e Validação

**Step 5.1: Testes Backend**
1. Criar Company PF → verifica user criado automaticamente com CPF
2. Criar Company PJ → verifica user criado automaticamente com CNPJ
3. Login com CPF de user existente → sucesso
4. Login com CNPJ de user existente → sucesso
5. Login com documento inválido → erro apropriado
6. Criar users com mesma matrícula em empresas diferentes → sucesso
7. Criar users com mesma matrícula na mesma empresa → erro de validação

**Step 5.2: Testes Frontend**
1. Formulário Company: alternar PF/PJ → máscara atualiza
2. Formulário Company: criar PF → sucesso, admin criado
3. Formulário Company: criar PJ → sucesso, admin criado
4. Formulário User: preencher certificado e matrícula → salva corretamente
5. Lista Users: exibir novos campos
6. Verificar todas as substituições "Empresa" → "Corban"

*Depende: Todas as fases anteriores*

---

## Arquivos Relevantes

### Backend (Django)
- `corbot/core/models.py` - Company e User models (Step 1.1, 1.2)
- `corbot/core/serializers.py` - CompanySerializer, UserSerializer (Step 1.4, 1.5)
- `corbot/core/backends.py` - Novo arquivo para autenticação customizada (Step 1.3)
- `corbot/corbot/settings.py` - AUTHENTICATION_BACKENDS (Step 1.3)
- `corbot/core/admin.py` - Admin labels (Step 2.1)
- `corbot/core/permissions.py` - Docstrings (Step 2.2)

### Frontend (Astro + React)
- `corbot-frontend/src/components/react/layout/SidebarContent.tsx` (Step 3.1)
- `corbot-frontend/src/components/react/domain/companies/CompanyList.tsx` (Step 3.1, 4.3)
- `corbot-frontend/src/components/react/domain/companies/CompanyForm.tsx` (Step 3.1, 4.1)
- `corbot-frontend/src/components/react/domain/users/UserList.tsx` (Step 3.1, 4.3)
- `corbot-frontend/src/components/react/domain/users/UserForm.tsx` (Step 4.2)
- `corbot-frontend/src/components/react/domain/commissions/CommissionList.tsx` (Step 3.1)
- `corbot-frontend/src/components/react/domain/proposals/ProposalListPage.tsx` (Step 3.1)
- `corbot-frontend/src/components/react/domain/setup/SetupPage.tsx` (Step 3.2)
- `corbot-frontend/src/lib/utils/roles.ts` (Step 3.1)
- `corbot-frontend/src/pages/**/*.astro` - 10+ arquivos com títulos (Step 3.1)

---

## Verificação

**Backend**:
1. Migrations criadas e aplicadas sem erros
2. Testes de criação de Company (PF/PJ) com user automático
3. Testes de login com CPF e CNPJ
4. Validação de matrícula única por empresa

**Frontend**:
1. Grep "Empresa" deve retornar apenas "Promotora" em contextos apropriados
2. Formulários mostram person_type, certificado, matricula
3. Máscaras funcionam corretamente
4. Sem erros TypeScript

**Database**:
1. Migration 0004 (ou similar): person_type, document rename em Company
2. Migration 0005 (ou similar): certificado, matricula em User

---

## Decisões Importantes

1. **Campo document**: Renomear cnpj → document (aceita CPF ou CNPJ dependendo de person_type)
2. **Autenticação**: Backend customizado permite login com ambos documentos
3. **Senha inicial**: Gerada automaticamente, user deve resetar (is_active=False ou flag específico)
4. **Matrícula**: Unique constraint composto (company, matricula) no database; **se não informada, usa CPF do usuário como matrícula automaticamente**; é editável a qualquer momento
5. **Nomenclatura**: "Corban" para empresas subordinadas, "Promotora" para principal
6. **Role label**: Não alterar "empresa_admin" (código), apenas labels ("Admin. Corban")

---

## Escopo Excluído

- Envio de email com senha temporária (pode ser adicionado depois)
- Interface para reset de senha pelo admin
- Migração de dados existentes (sistema novo, sem dados legados)
- Auditoria de criação de users automáticos

---

## Próximos Passos

1. Aguardando aprovação do plano
2. Iniciar implementação pela Fase 1 (Backend)
3. Aplicar migrations e testar
4. Prosseguir para nomenclatura (Fases 2-3)
5. Adicionar campos de UI (Fase 4)
6. Validação final (Fase 5)
