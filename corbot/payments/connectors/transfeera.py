import logging
import os
from core.base.base_connectors import BaseConnector
from core.models import ConnectorLog
from payments.models import PaymentManual, Payment
from core.utils import UserInstance

logger = logging.getLogger(__name__)


class TransfeeraConnector(BaseConnector):
    def __init__(self):
        self.client_id = os.getenv("TRANSFEERA_API_CLIENT_ID")
        self.client_secret = os.getenv("TRANSFEERA_API_CLIENT_SECRET")
        self.login_url = f"https://login-api.transfeera.com/authorization"
        self.log_model = ConnectorLog
        super().__init__("https://api.transfeera.com.br")
    
    def save_log(self, *args, **kwargs)->ConnectorLog|None:
        try:
            log = self.log_model.objects.create(
                connector=self.__class__.__name__,
                status=self.last_status,
                response=self.last_response,
                error=self.last_error
            )
            return log
        except Exception as e:
            logger.error("Failed to save log: %s", e)
            return None

    def authenticate(self, *args, **kwargs)->str:
        url = self.login_url
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        response = self.post(url, data=data)
        self.raise_for_status(response, "Transfeera Login")
        
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}"
        }
        return self.token
    
    def validate_pix_type(self, key: str, pix_type: str)->dict:
        url = f"{self.base_url}/pix/dict_key/{key}?key_type={pix_type}"
        response = self.get(url)
        self.raise_for_status(response, "Transfeera - Validação PIX")
        return response.json()
    
    def create_payment_batch(self, payments: list[Payment]):
        url = f"{self.base_url}/batch"  
        data = []
        for payment in payments:
            user = UserInstance(payment.user)
            data.append({
        "type": "TRANSFERENCIA",
        "auto_close": False,
        "name": "",
        "transfers": [
            {
            "value": payment.total_amount,
            "integration_id": payment.user.id,
            "idempotency_key": payment.id,
            "pix_description": f"Pagamento {payment.user.get_full_name()}",
            "destination_bank_account": {
                "pix_key_type": user.pix_type,
                "pix_key": user.pix_key,
                "email": user.email
            }
            }
        ]
        })
        response = self.post(url, data=data)
        self.raise_for_status(response, "Transfeera - Criar Lote de Pagamento")
        return response.json()

    def create_withdraw(self, payment: Payment):
        pass

    def get_withdraw(self, id):
        pass

    def get_withdraws(self):
        pass