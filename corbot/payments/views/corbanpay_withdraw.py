"""
View para o fluxo completo de saque via CorbanPay.

Fluxo (POST /payments/withdrawals/corbanpay/):
  1. Busca as comissões com status 'withdraw_available' do usuário
  2. Verifica (ou cria) o recebedor no CorbanPay pelo CPF/CNPJ
  3. Cria o pré-pagamento no CorbanPay
  4. Gera o token/link de saque
  5. Salva tudo localmente e retorna o link ao usuário

GET /payments/withdrawals/corbanpay/
  Retorna a transação CorbanPay mais recente (ativa) do usuário.
"""
import logging
from decimal import Decimal

from django.db import transaction
from django.utils.timezone import now
from rest_framework import permissions, status
from rest_framework.response import Response

from core.base_views import BaseApiView
from core.base.base_connectors import ConnectorException
from core.models import User
from payments.connectors.corbanpay import CorbanPayConnector
from payments.models import Commission, CorbanPayTransaction, Payment, Withdraw

logger = logging.getLogger(__name__)


def _user_document(user: User) -> str:
    """Retorna CPF ou CNPJ do usuário, sem formatação."""
    doc = getattr(user, "cpf", None) or getattr(user, "cnpj", None) or ""
    return "".join(c for c in doc if c.isdigit())


def _user_name(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip() or user.email


def _user_email(user: User) -> str:
    return user.email or ""


def _user_whatsapp(user: User) -> str:
    phone = getattr(user, "phone", None) or ""
    return "".join(c for c in phone if c.isdigit())


class CorbanPayWithdrawView(BaseApiView):
    """
    POST — inicia o fluxo completo de saque via CorbanPay.
    GET  — retorna a transação CorbanPay ativa mais recente do usuário.
    """

    permission_classes = [permissions.IsAuthenticated]

    # ── GET ──────────────────────────────────────────────────────────────

    def get(self, request):
        user = request.user
        txn = (
            CorbanPayTransaction.objects.filter(withdraw__user=user)
            .exclude(status=CorbanPayTransaction.FAILED)
            .order_by("-created_at")
            .first()
        )
        if not txn:
            return Response(
                {"detail": "Nenhuma transação CorbanPay encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(self._serialize_txn(txn))

    # ── POST ─────────────────────────────────────────────────────────────

    def post(self, request):
        user = request.user

        # 1. Verificar comissões disponíveis
        available = Commission.objects.filter(
            user=user,
            release_status=Commission.WITHDRAW_AVAILABLE,
        )
        if not available.exists():
            return Response(
                {"detail": "Não há comissões disponíveis para saque."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total = sum(c.value for c in available)
        if total <= Decimal("0"):
            return Response(
                {"detail": "Valor total das comissões é zero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        document = _user_document(user)
        if not document:
            return Response(
                {"detail": "Usuário sem CPF/CNPJ cadastrado. Não é possível processar o saque."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Inicializar conector (valida envs)
        try:
            connector = CorbanPayConnector()
        except ConnectorException as exc:
            logger.error("CorbanPay – conector não configurado: %s", exc)
            return Response(
                {"detail": f"Integração CorbanPay não configurada: {exc.message}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # 3. Fluxo atômico local + chamadas à API
        try:
            with transaction.atomic():
                # Criar Payment + Withdraw locais
                payment = Payment.objects.create(
                    user=user,
                    total_amount=total,
                    status=Payment.PENDING,
                    payment_method=Payment.WITHDRAW,
                )
                available.update(
                    payment=payment,
                    release_status=Commission.PAID,
                    paid_at=now(),
                    paid_by=user,
                )
                withdraw = Withdraw.objects.create(
                    user=user,
                    amount=total,
                    payment=payment,
                )

                # Criar registro de transação CorbanPay (status=pending)
                txn = CorbanPayTransaction.objects.create(
                    withdraw=withdraw,
                    receiver_id="",  # será preenchido abaixo
                )

        except Exception as exc:
            logger.error("CorbanPay – erro ao criar registros locais: %s", exc)
            return Response(
                {"detail": "Erro interno ao preparar o saque."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 4. Chamar CorbanPay (fora da transaction local para não fazer rollback da BD em falha da API)
        try:
            # 4a. Verificar / criar recebedor
            receiver = connector.get_or_create_receiver(
                name=_user_name(user),
                document_number=document,
                email=_user_email(user),
                whatsapp=_user_whatsapp(user),
            )
            receiver_id = str(receiver.get("id") or receiver.get("receiver_id", ""))
            txn.receiver_id = receiver_id
            txn.save(update_fields=["receiver_id"])

            # 4b. Criar pré-pagamento
            pre_payment = connector.create_pre_payment(
                receiver_id=receiver_id,
                amount=str(total),
                external_id=f"withdraw-{withdraw.id}",
            )
            pre_payment_id = str(pre_payment.get("id") or pre_payment.get("pre_payment_id", ""))
            txn.pre_payment_id = pre_payment_id
            txn.save(update_fields=["pre_payment_id"])

            # 4c. Gerar token / link de saque
            token_data = connector.generate_token(pre_payment_id=pre_payment_id, ttl_minutes=1440)
            withdrawal_link = (
                token_data.get("link")
                or token_data.get("withdrawal_link")
                or token_data.get("url")
                or ""
            )
            txn.withdrawal_link = withdrawal_link
            txn.status = CorbanPayTransaction.ACTIVE
            txn.save(update_fields=["withdrawal_link", "status"])

            self.log_info(
                request=request,
                action="corbanpay_withdraw",
                message=f"Saque CorbanPay criado: R${total} – pré-pagamento {pre_payment_id}",
                data={"withdraw_id": withdraw.id, "pre_payment_id": pre_payment_id},
            )

            return Response(self._serialize_txn(txn), status=status.HTTP_201_CREATED)

        except ConnectorException as exc:
            # Marcar transação como falha mas manter o Payment/Withdraw criados para auditoria
            txn.status = CorbanPayTransaction.FAILED
            txn.error_message = str(exc)
            txn.save(update_fields=["status", "error_message"])
            logger.error("CorbanPay – erro na API: %s", exc)
            return Response(
                {"detail": f"Erro na integração CorbanPay: {exc.message}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _serialize_txn(txn: CorbanPayTransaction) -> dict:
        return {
            "id": txn.id,
            "status": txn.status,
            "receiver_id": txn.receiver_id,
            "pre_payment_id": txn.pre_payment_id,
            "withdrawal_link": txn.withdrawal_link,
            "amount": str(txn.withdraw.amount),
            "error_message": txn.error_message or None,
            "created_at": txn.created_at.isoformat(),
        }
