import logging
from abc import ABC, abstractmethod
from requests import Session
from django.utils import timezone
from django.db import models

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30  # seconds


class ConnectorException(Exception):
    """Exceção para erros de conectores externos."""
    
    def __init__(self, message, status_code=None, response_data=None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


class BaseConnector(ABC):
    base_url: str | None = None
    token: str | None = None
    headers: dict | None = None
    last_status: int | None = None
    last_response: dict | None = None
    last_error: str | None = None
    log_model: models.Model | None = None

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = Session()  # Instance-level session (thread-safe)

    @abstractmethod
    def authenticate(self, *args, **kwargs) -> str:
        pass

    @abstractmethod
    def save_log(self, *args, **kwargs):
        pass

    def _update_headers(self):
        if self.headers is not None:
            self.session.headers.update(self.headers)

    def _extract_error_message(self, response):
        """
        Extrai mensagem de erro específica da resposta da API.
        Tenta diferentes formatos comuns de erro.
        """
        try:
            data = response.json()
            
            # Tentar diferentes campos comuns de mensagem de erro
            if isinstance(data, dict):
                # Padrões comuns de erro
                for key in ['message', 'error', 'detail', 'error_description', 'msg']:
                    if key in data:
                        return data[key]
                
                # Se há um campo 'errors' com detalhes
                if 'errors' in data:
                    errors = data['errors']
                    if isinstance(errors, list) and errors:
                        return errors[0]
                    elif isinstance(errors, dict):
                        # Pegar o primeiro erro
                        for field, messages in errors.items():
                            if isinstance(messages, list) and messages:
                                return f"{field}: {messages[0]}"
                            return f"{field}: {messages}"
                
                # Retornar o JSON completo se não encontrar padrão conhecido
                return str(data)
            
            elif isinstance(data, list) and data:
                return data[0]
            
            return response.text
            
        except (ValueError, Exception):
            # Se não conseguir parsear JSON, retornar texto bruto
            return response.text[:200] if response.text else f"Erro {response.status_code}"

    def _parse_response(self, response):
        self.last_status = response.status_code
        
        # Extrair mensagem de erro específica
        if not response.ok:
            self.last_error = self._extract_error_message(response)
        else:
            self.last_error = None
        
        try:
            self.last_response = response.json()
        except (ValueError, Exception):
            self.last_response = None
            if not response.ok:
                logger.warning(
                    "Non-JSON error response from %s (status %s): %s",
                    response.url, response.status_code, response.text[:200]
                )
        
        self.save_log()
        return response
    
    def _handle_request_error(self, error, url):
        """Trata erros de requisição (timeout, conexão, etc.)."""
        logger.error(f"Request error to {url}: {str(error)}")
        self.last_status = None
        self.last_error = str(error)
        self.last_response = None
        self.save_log()
        
        raise ConnectorException(
            message=f"Erro de conexão: {str(error)}",
            status_code=None,
            response_data=None
        )

    def get(self, url: str, params=None):
        self._update_headers()
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            return self._parse_response(response)
        except Exception as e:
            self._handle_request_error(e, url)

    def post(self, url: str, data=None):
        self._update_headers()
        try:
            response = self.session.post(url, json=data, timeout=REQUEST_TIMEOUT)
            return self._parse_response(response)
        except Exception as e:
            self._handle_request_error(e, url)

    def put(self, url: str, data=None):
        self._update_headers()
        try:
            response = self.session.put(url, json=data, timeout=REQUEST_TIMEOUT)
            return self._parse_response(response)
        except Exception as e:
            self._handle_request_error(e, url)

    def delete(self, url: str):
        self._update_headers()
        try:
            response = self.session.delete(url, timeout=REQUEST_TIMEOUT)
            return self._parse_response(response)
        except Exception as e:
            self._handle_request_error(e, url)
    
    def raise_for_status(self, response, service_name=None):
        """
        Verifica o status da resposta e levanta exceção customizada se houver erro.
        
        Args:
            response: Objeto response do requests
            service_name: Nome do serviço para mensagem de erro
        """
        if not response.ok:
            error_msg = self.last_error or f"Erro {response.status_code}"
            
            from core.exceptions import ExternalAPIError
            raise ExternalAPIError(
                service_name=service_name or self.__class__.__name__,
                message=error_msg,
                status_code=response.status_code,
                original_error=error_msg
            )

