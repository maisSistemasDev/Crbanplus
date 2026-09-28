/**
 * Utilitários para formatação e exibição de mensagens de erro da API.
 */

import { ApiError } from './client';

/**
 * Extrai a mensagem de erro principal de um erro da API.
 * 
 * Trata diferentes formatos de resposta de erro:
 * - { error: "mensagem" }
 * - { detail: "mensagem" }
 * - { message: "mensagem" }
 * - { errors: { campo: "mensagem" } }
 * 
 * @param error - Erro capturado do try/catch
 * @returns Mensagem de erro formatada para exibição
 */
export function extractErrorMessage(error: unknown): string {
  // Se não é um erro, retornar mensagem genérica
  if (!error) {
    return 'Ocorreu um erro inesperado';
  }

  // Se é uma instância de ApiError
  if (error instanceof ApiError) {
    const { data, status } = error;

    // Tentar extrair mensagem do campo 'error'
    if (typeof data === 'object' && data !== null) {
      // Campo 'error' principal
      if ('error' in data && typeof data.error === 'string') {
        return data.error;
      }

      // Campo 'detail'
      if ('detail' in data && typeof data.detail === 'string') {
        return data.detail;
      }

      // Campo 'message'
      if ('message' in data && typeof data.message === 'string') {
        return data.message;
      }

      // Se há um objeto 'errors' com erros de campo
      if ('errors' in data && typeof data.errors === 'object' && data.errors !== null) {
        const errors = data.errors as Record<string, unknown>;
        
        // Pegar o primeiro erro
        for (const [field, message] of Object.entries(errors)) {
          if (typeof message === 'string') {
            return field === 'non_field_errors' ? message : `${field}: ${message}`;
          }
          if (Array.isArray(message) && message.length > 0) {
            const firstMsg = message[0];
            return field === 'non_field_errors' ? firstMsg : `${field}: ${firstMsg}`;
          }
        }
      }
    }

    // Mensagens específicas por código de status
    switch (status) {
      case 400:
        return 'Dados inválidos fornecidos';
      case 401:
        return 'Sessão expirada. Faça login novamente';
      case 403:
        return 'Você não tem permissão para realizar esta ação';
      case 404:
        return 'Recurso não encontrado';
      case 409:
        return 'Conflito: este registro já existe ou está em uso';
      case 500:
        return 'Erro interno do servidor. Tente novamente mais tarde';
      case 502:
        return 'Erro ao comunicar com serviço externo';
      case 503:
        return 'Serviço temporariamente indisponível';
      default:
        return `Erro ${status}: Ocorreu um problema ao processar sua solicitação`;
    }
  }

  // Se é um objeto Error padrão
  if (error instanceof Error) {
    return error.message;
  }

  // Se é uma string
  if (typeof error === 'string') {
    return error;
  }

  // Tentar converter para string
  try {
    return JSON.stringify(error);
  } catch {
    return 'Ocorreu um erro inesperado';
  }
}

/**
 * Extrai todos os erros de validação de campo da resposta da API.
 * 
 * @param error - Erro capturado do try/catch
 * @returns Objeto com erros por campo, ou objeto vazio se não houver erros de validação
 */
export function extractFieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError)) {
    return {};
  }

  const { data } = error;

  if (typeof data !== 'object' || data === null) {
    return {};
  }

  // Se há um objeto 'errors' específico
  if ('errors' in data && typeof data.errors === 'object' && data.errors !== null) {
    const errors = data.errors as Record<string, unknown>;
    const fieldErrors: Record<string, string> = {};

    for (const [field, message] of Object.entries(errors)) {
      if (typeof message === 'string') {
        fieldErrors[field] = message;
      } else if (Array.isArray(message) && message.length > 0) {
        fieldErrors[field] = message[0];
      } else if (typeof message === 'object' && message !== null) {
        // Erro aninhado
        fieldErrors[field] = JSON.stringify(message);
      }
    }

    return fieldErrors;
  }

  // Se a resposta inteira é um objeto de erros (formato antigo do DRF)
  const fieldErrors: Record<string, string> = {};
  for (const [key, value] of Object.entries(data)) {
    // Pular campos que não são erros de validação
    if (['error', 'detail', 'message', 'type', 'status_code'].includes(key)) {
      continue;
    }

    if (typeof value === 'string') {
      fieldErrors[key] = value;
    } else if (Array.isArray(value) && value.length > 0) {
      fieldErrors[key] = value[0];
    }
  }

  return fieldErrors;
}

/**
 * Verifica se o erro é de autenticação (401).
 * 
 * @param error - Erro capturado
 * @returns true se for erro de autenticação
 */
export function isAuthError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

/**
 * Verifica se o erro é de permissão (403).
 * 
 * @param error - Erro capturado
 * @returns true se for erro de permissão
 */
export function isPermissionError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 403;
}

/**
 * Verifica se o erro é de validação (400).
 * 
 * @param error - Erro capturado
 * @returns true se for erro de validação
 */
export function isValidationError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 400;
}

/**
 * Verifica se o erro é de serviço externo (502, 503).
 * 
 * @param error - Erro capturado
 * @returns true se for erro de serviço externo
 */
export function isExternalServiceError(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 502 || error.status === 503);
}

/**
 * Formata um erro para exibição em um toast ou notificação.
 * Extrai a mensagem principal e, se houver erros de campo, os inclui.
 * 
 * @param error - Erro capturado
 * @returns Mensagem formatada pronta para exibição
 */
export function formatErrorForDisplay(error: unknown): string {
  const mainMessage = extractErrorMessage(error);
  const fieldErrors = extractFieldErrors(error);

  // Se não há erros de campo, retornar apenas a mensagem principal
  if (Object.keys(fieldErrors).length === 0) {
    return mainMessage;
  }

  // Incluir até 3 erros de campo na mensagem
  const fieldMessages = Object.entries(fieldErrors)
    .slice(0, 3)
    .map(([field, msg]) => `• ${field}: ${msg}`)
    .join('\n');

  return `${mainMessage}\n\n${fieldMessages}`;
}
