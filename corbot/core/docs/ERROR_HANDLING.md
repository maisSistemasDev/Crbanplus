# Sistema de Tratamento de Erros

Este documento descreve o sistema aprimorado de tratamento de erros da API.

## Backend (Django)

### Exception Handler Customizado

O sistema agora usa um exception handler customizado que fornece mensagens de erro mais específicas e padronizadas.

#### Configuração

O handler está configurado em `settings.py`:

```python
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
    # ... outras configurações
}
```

#### Exceções Customizadas

##### APIException

Exceção base para erros da API com mensagens customizadas:

```python
from core.exceptions import APIException

# Uso básico
raise APIException("Mensagem de erro", status_code=400)

# Com erros de campo
raise APIException(
    "Dados inválidos",
    status_code=400,
    errors={'email': 'Email já cadastrado', 'cpf': 'CPF inválido'}
)
```

##### ExternalAPIError

Exceção específica para erros de APIs externas (bancos, pagamentos, etc.):

```python
from core.exceptions import ExternalAPIError

try:
    response = connector.authenticate()
except Exception as e:
    raise ExternalAPIError(
        service_name="Transfeera",
        message="Falha na autenticação",
        original_error=e
    )
```

#### Formatação de Erros de Serializer

Para formatar erros de validação de serializer de forma consistente:

```python
from core.exceptions import format_serializer_errors
from rest_framework.response import Response
from rest_framework import status

def post(self, request):
    serializer = MySerializer(data=request.data)
    if not serializer.is_valid():
        errors = format_serializer_errors(serializer.errors)
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    # ... continuar com lógica
```

### Conectores (BaseConnector)

O `BaseConnector` agora extrai mensagens de erro específicas das APIs:

```python
from core.base.base_connectors import BaseConnector

class MyConnector(BaseConnector):
    def some_method(self):
        response = self.get('/some/endpoint')
        
        # Método 1: Verificar status manualmente
        if not response.ok:
            # self.last_error contém a mensagem específica extraída
            raise Exception(self.last_error)
        
        # Método 2: Usar raise_for_status (recomendado)
        self.raise_for_status(response, "Nome do Serviço")
        
        return response.json()
```

O método `raise_for_status` automaticamente:
- Verifica se há erro na resposta
- Extrai a mensagem de erro específica
- Levanta `ExternalAPIError` com contexto completo

### Exemplo Completo de View

```python
from rest_framework.response import Response
from rest_framework import status
from core.base_views import BaseApiView
from core.exceptions import APIException, format_serializer_errors

class MyView(BaseApiView):
    def post(self, request):
        # Validação de entrada
        serializer = MySerializer(data=request.data)
        if not serializer.is_valid():
            errors = format_serializer_errors(serializer.errors)
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Lógica de negócio
            result = self.process_data(serializer.validated_data)
            
            # Log de sucesso
            self.log_info(
                request=request,
                action='create_item',
                message=f'Item criado com sucesso'
            )
            
            return Response(result, status=status.HTTP_201_CREATED)
            
        except IntegrityError:
            # O exception handler automaticamente trata e formata
            raise
            
        except Exception as e:
            # Erro customizado
            raise APIException(
                "Erro ao processar dados",
                status_code=status.HTTP_400_BAD_REQUEST
            )
```

## Frontend (TypeScript/React)

### Utilitários de Erro

Criado arquivo `src/lib/api/errors.ts` com funções utilitárias:

#### extractErrorMessage

Extrai a mensagem de erro principal:

```typescript
import { extractErrorMessage } from '@/lib/api/errors';

try {
  await api.post('/endpoint', data);
} catch (error) {
  const message = extractErrorMessage(error);
  toast.error(message);
}
```

#### extractFieldErrors

Extrai erros de validação por campo:

```typescript
import { extractFieldErrors } from '@/lib/api/errors';

try {
  await api.post('/users/', userData);
} catch (error) {
  const fieldErrors = extractFieldErrors(error);
  // { email: 'Email já cadastrado', cpf: 'CPF inválido' }
  
  // Atualizar estado do formulário com erros
  setErrors(fieldErrors);
}
```

#### Verificadores de Tipo de Erro

```typescript
import { 
  isAuthError, 
  isPermissionError, 
  isValidationError,
  isExternalServiceError 
} from '@/lib/api/errors';

try {
  await api.delete('/resource/123');
} catch (error) {
  if (isAuthError(error)) {
    // Redirecionar para login
    window.location.href = '/login';
  } else if (isPermissionError(error)) {
    toast.error('Você não tem permissão para esta ação');
  } else if (isExternalServiceError(error)) {
    toast.error('Serviço temporariamente indisponível. Tente novamente.');
  } else {
    toast.error(extractErrorMessage(error));
  }
}
```

#### formatErrorForDisplay

Formata erro completo para exibição:

```typescript
import { formatErrorForDisplay } from '@/lib/api/errors';

try {
  await api.post('/endpoint', data);
} catch (error) {
  // Retorna mensagem principal + até 3 erros de campo
  const fullMessage = formatErrorForDisplay(error);
  toast.error(fullMessage);
}
```

### Exemplo Completo de Componente

```typescript
import { useState } from 'react';
import { api } from '@/lib/api/client';
import { extractErrorMessage, extractFieldErrors } from '@/lib/api/errors';
import toast from 'react-hot-toast';

export function MyForm() {
  const [loading, setLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  async function handleSubmit(data: FormData) {
    setLoading(true);
    setFieldErrors({});

    try {
      await api.post('/endpoint/', data);
      toast.success('Salvo com sucesso!');
    } catch (error) {
      // Extrair erros de campo para mostrar no formulário
      const errors = extractFieldErrors(error);
      setFieldErrors(errors);
      
      // Mostrar mensagem geral
      const message = extractErrorMessage(error);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <input name="email" />
      {fieldErrors.email && (
        <span className="error">{fieldErrors.email}</span>
      )}
      
      <button type="submit" disabled={loading}>
        Salvar
      </button>
    </form>
  );
}
```

## Formato de Resposta de Erro

### Backend Response

Todas as respostas de erro seguem este formato padronizado:

```json
{
  "error": "Mensagem principal do erro",
  "errors": {
    "campo1": "Mensagem de erro do campo1",
    "campo2": "Mensagem de erro do campo2"
  },
  "type": "ValidationError",
  "status_code": 400
}
```

### Tipos de Erro

- `ValidationError`: Erro de validação de dados (400)
- `IntegrityError`: Erro de integridade no banco de dados (400)
- `ExternalAPIError`: Erro ao comunicar com API externa (502)
- `PermissionDenied`: Sem permissão para a ação (403)
- `NotFound`: Recurso não encontrado (404)

## Mensagens por Código de Status

| Código | Mensagem Padrão |
|--------|----------------|
| 400 | Dados inválidos fornecidos |
| 401 | Sessão expirada. Faça login novamente |
| 403 | Você não tem permissão para realizar esta ação |
| 404 | Recurso não encontrado |
| 409 | Conflito: este registro já existe ou está em uso |
| 500 | Erro interno do servidor. Tente novamente mais tarde |
| 502 | Erro ao comunicar com serviço externo |
| 503 | Serviço temporariamente indisponível |

## Boas Práticas

### Backend

1. **Use exceções customizadas** para erros de negócio específicos
2. **Use `format_serializer_errors`** ao retornar erros de validação
3. **Use `raise_for_status`** em conectores para tratamento automático
4. **Forneça contexto** nas mensagens de erro (o que falhou, por que falhou)

### Frontend

1. **Sempre use os utilitários** de `errors.ts` para extrair mensagens
2. **Mostre erros de campo** nos formulários quando disponíveis
3. **Use toast** para mensagens gerais de erro
4. **Trate erros de autenticação** redirecionando para login
5. **Forneça feedback visual** durante operações assíncronas

## Migration Guide

### Para Views Existentes

Antes:
```python
if not serializer.is_valid():
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

Depois:
```python
from core.exceptions import format_serializer_errors

if not serializer.is_valid():
    errors = format_serializer_errors(serializer.errors)
    return Response(errors, status=status.HTTP_400_BAD_REQUEST)
```

### Para Componentes Existentes

Antes:
```typescript
} catch (err) {
  toast.error('Erro ao salvar');
}
```

Depois:
```typescript
import { extractErrorMessage } from '@/lib/api/errors';

} catch (error) {
  toast.error(extractErrorMessage(error));
}
```
