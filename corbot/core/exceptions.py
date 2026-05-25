"""
Sistema customizado de tratamento de exceções para a API.
Fornece mensagens de erro mais específicas e padronizadas.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)


class APIException(Exception):
    """Exceção base para erros da API com mensagens customizadas."""
    
    def __init__(self, message, status_code=status.HTTP_400_BAD_REQUEST, errors=None):
        self.message = message
        self.status_code = status_code
        self.errors = errors or {}
        super().__init__(message)


class ExternalAPIError(APIException):
    """Exceção para erros de APIs externas (bancos, pagamentos, etc.)."""
    
    def __init__(self, service_name, message, status_code=None, original_error=None):
        self.service_name = service_name
        self.original_error = original_error
        
        # Formatar mensagem com contexto
        formatted_message = f"Erro ao comunicar com {service_name}: {message}"
        
        super().__init__(
            message=formatted_message,
            status_code=status_code or status.HTTP_502_BAD_GATEWAY,
            errors={'service': service_name, 'original_error': str(original_error) if original_error else None}
        )


def format_validation_errors(errors):
    """
    Formata erros de validação do DRF de forma mais legível.
    
    Converte:
        {'field': ['Error message']}
    Em:
        {'field': 'Error message'}
    
    E agrupa múltiplos erros por campo.
    """
    formatted = {}
    
    for field, messages in errors.items():
        if isinstance(messages, list):
            # Se há múltiplas mensagens, juntá-las
            if len(messages) == 1:
                formatted[field] = messages[0]
            else:
                formatted[field] = '; '.join(str(msg) for msg in messages)
        elif isinstance(messages, dict):
            # Erros aninhados (ex: relacionamentos)
            formatted[field] = format_validation_errors(messages)
        else:
            formatted[field] = str(messages)
    
    return formatted


def get_error_message(errors):
    """
    Extrai uma mensagem de erro principal dos erros de validação.
    """
    if isinstance(errors, dict):
        # Se há um campo 'non_field_errors', usar como mensagem principal
        if 'non_field_errors' in errors:
            return errors['non_field_errors']
        
        # Caso contrário, pegar o primeiro erro
        for field, message in errors.items():
            if isinstance(message, (list, tuple)) and message:
                return f"{field}: {message[0]}"
            return f"{field}: {message}"
    
    return "Erro de validação"


def custom_exception_handler(exc, context):
    """
    Handler customizado de exceções para a API.
    
    Fornece respostas de erro padronizadas e mais informativas.
    """
    # Chamar o handler padrão do DRF primeiro
    response = exception_handler(exc, context)
    
    # Se o DRF não tratou a exceção, tratar manualmente
    if response is None:
        # Erros de integridade do banco de dados
        if isinstance(exc, IntegrityError):
            logger.error(f"IntegrityError: {str(exc)}", exc_info=True)
            
            error_message = "Erro de integridade no banco de dados"
            
            # Tentar extrair informações mais específicas
            exc_str = str(exc).lower()
            if 'unique' in exc_str or 'duplicate' in exc_str:
                error_message = "Este registro já existe no sistema"
            elif 'foreign key' in exc_str:
                error_message = "Referência inválida: registro relacionado não encontrado"
            elif 'not null' in exc_str:
                error_message = "Campo obrigatório não foi fornecido"
            
            return Response({
                'error': error_message,
                'detail': str(exc),
                'type': 'IntegrityError'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Erros de validação do Django
        if isinstance(exc, ValidationError):
            logger.warning(f"ValidationError: {str(exc)}")
            return Response({
                'error': 'Erro de validação',
                'detail': exc.messages if hasattr(exc, 'messages') else str(exc),
                'type': 'ValidationError'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Exceções customizadas da API
        if isinstance(exc, APIException):
            logger.warning(f"APIException: {exc.message}")
            return Response({
                'error': exc.message,
                'errors': exc.errors,
                'type': exc.__class__.__name__
            }, status=exc.status_code)
        
        # Outras exceções não tratadas
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return Response({
            'error': 'Erro interno do servidor',
            'detail': str(exc) if logger.level == logging.DEBUG else 'Ocorreu um erro inesperado',
            'type': exc.__class__.__name__
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Se o DRF tratou, melhorar a resposta
    if response is not None:
        # Adicionar informações extras às respostas de erro do DRF
        error_data = response.data.copy()
        
        # Se há erros de validação, formatá-los
        if isinstance(error_data, dict):
            # Formatar erros de validação
            formatted_errors = format_validation_errors(error_data)
            
            # Se não há uma mensagem 'error' principal, criar uma
            if 'error' not in formatted_errors and 'detail' not in formatted_errors:
                main_message = get_error_message(formatted_errors)
                response.data = {
                    'error': main_message,
                    'errors': formatted_errors,
                    'type': 'ValidationError'
                }
            else:
                response.data = {
                    'error': formatted_errors.get('detail') or formatted_errors.get('error') or 'Erro de validação',
                    'errors': formatted_errors,
                    'type': 'ValidationError'
                }
        elif isinstance(error_data, list):
            response.data = {
                'error': error_data[0] if error_data else 'Erro de validação',
                'errors': {'detail': error_data},
                'type': 'ValidationError'
            }
        else:
            response.data = {
                'error': str(error_data),
                'type': 'Error'
            }
        
        # Adicionar código de status na resposta
        response.data['status_code'] = response.status_code
    
    return response


def format_serializer_errors(serializer_errors):
    """
    Formata erros de serializer para um formato mais amigável.
    
    Uso:
        if not serializer.is_valid():
            errors = format_serializer_errors(serializer.errors)
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    """
    formatted = format_validation_errors(serializer_errors)
    main_message = get_error_message(formatted)
    
    return {
        'error': main_message,
        'errors': formatted,
        'type': 'ValidationError'
    }
