"""
Conector para a API CorbanPay (pré-pagamentos / saques).

Variáveis de ambiente necessárias:
  CORBANPAY_API_KEY   — chave de API do integrador
  CORBANPAY_BASE_URL  — URL base, ex: https://seudominio.com/api/v1/prepayment
"""
import logging
import os

from core.base.base_connectors import BaseConnector, ConnectorException
from core.models import ConnectorLog

logger = logging.getLogger(__name__)


class CorbanPayConnector(BaseConnector):
    """Integra com a API REST do CorbanPay para criar recebedores,
    pré-pagamentos e links de saque."""

    def __init__(self):
        db_api_key = ''
        db_base_url = ''

        try:
            from core.models import SystemSettings
            config = SystemSettings.get_solo()
            db_api_key = (config.corbanpay_api_key or '').strip()
            db_base_url = (config.corbanpay_base_url or '').strip()
        except Exception:
            # Mantém fallback para variáveis de ambiente quando a tabela ainda não existe
            # (ex.: durante migrações iniciais)
            pass

        self.api_key = db_api_key or os.getenv("CORBANPAY_API_KEY", "")
        base_url = (db_base_url or os.getenv("CORBANPAY_BASE_URL", "")).rstrip("/")
        if not base_url:
            raise ConnectorException("CORBANPAY_BASE_URL não configurada")
        if not self.api_key:
            raise ConnectorException("CORBANPAY_API_KEY não configurada")
        self.log_model = ConnectorLog
        super().__init__(base_url)
        self.authenticate()

    # ─── BaseConnector obrigatórios ────────────────────────────────────────

    def authenticate(self, *args, **kwargs) -> str:
        """A autenticação é via API key no header — apenas configura os headers."""
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }
        return self.api_key

    def save_log(self, *args, **kwargs):
        try:
            return self.log_model.objects.create(
                connector=self.__class__.__name__,
                status=self.last_status,
                response=self.last_response,
                error=self.last_error,
            )
        except Exception as exc:
            logger.error("CorbanPayConnector – falha ao salvar log: %s", exc)
            return None

    # ─── Recebedores ───────────────────────────────────────────────────────

    def get_receiver_by_document(self, document_number: str) -> dict | None:
        """
        Busca um recebedor pelo CPF/CNPJ.
        Retorna o dict do recebedor ou None se não encontrado.
        """
        url = f"{self.base_url}/integrator/receivers/by-document/{document_number}/"
        response = self.get(url)
        if response.status_code == 404:
            return None
        self.raise_for_status(response, "CorbanPay – Buscar recebedor por documento")
        return response.json()

    def create_receiver(self, name: str, document_number: str,
                        email: str = "", whatsapp: str = "") -> dict:
        """
        Cria um novo recebedor.
        Retorna o dict criado pelo CorbanPay.
        """
        url = f"{self.base_url}/receivers/"
        payload = {
            "name": name,
            "document_number": document_number,
        }
        if email:
            payload["email"] = email
        if whatsapp:
            payload["whatsapp"] = whatsapp
        response = self.post(url, data=payload)
        self.raise_for_status(response, "CorbanPay – Criar recebedor")
        return response.json()

    def get_or_create_receiver(self, name: str, document_number: str,
                               email: str = "", whatsapp: str = "") -> dict:
        """
        Busca o recebedor pelo documento; se não existir, cria.
        Retorna sempre o dict do recebedor.
        """
        receiver = self.get_receiver_by_document(document_number)
        if receiver:
            logger.info("CorbanPay – recebedor encontrado: %s", receiver.get("id"))
            return receiver
        logger.info("CorbanPay – recebedor não encontrado, criando…")
        return self.create_receiver(name, document_number, email, whatsapp)

    # ─── Pré-pagamentos ────────────────────────────────────────────────────

    def create_pre_payment(self, receiver_id: str, amount: str,
                           external_id: str = "", webhook_url: str = "") -> dict:
        """
        Cria um pré-pagamento para o recebedor.
        Retorna o dict do pré-pagamento criado.
        """
        url = f"{self.base_url}/"
        payload = {
            "receiver_id": receiver_id,
            "amount": str(amount),
            "is_same_holder": True,
        }
        if external_id:
            payload["external_id"] = external_id
        if webhook_url:
            payload["webhook_url"] = webhook_url
        response = self.post(url, data=payload)
        self.raise_for_status(response, "CorbanPay – Criar pré-pagamento")
        return response.json()

    # ─── Token / link de saque ────────────────────────────────────────────

    def generate_token(self, pre_payment_id: str, ttl_minutes: int = 60) -> dict:
        """
        Gera o link/token de saque para o recebedor.
        Retorna o dict com o link de saque.
        """
        url = f"{self.base_url}/{pre_payment_id}/token/"
        payload = {"ttl_minutes": ttl_minutes}
        response = self.post(url, data=payload)
        self.raise_for_status(response, "CorbanPay – Gerar token de saque")
        return response.json()
