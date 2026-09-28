"""
Views relacionadas a operações com pagamentos e saques.
"""
import logging
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Q
from core.base_views import BaseApiView
from core.models import User
from payments.models import Payment, Withdraw
from payments.serializers import PaymentSerializer, WithdrawSerializer

logger = logging.getLogger(__name__)


class PaymentView(BaseApiView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.role == User.ADMIN:
            payments = Payment.objects.all()
        elif user.role in (User.EMPRESA_ADMIN, User.GERENTE):
            payments = Payment.objects.filter(user__company=user.company)
        elif user.role == User.GERENTE_COMERCIAL:
            from commercial.services import team_company_ids_for
            payments = Payment.objects.filter(user__company_id__in=team_company_ids_for(user))
        elif user.role == User.LIDER:
            payments = Payment.objects.filter(Q(user=user) | Q(user__leader=user))
        else:
            payments = Payment.objects.filter(user=user)
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)


class WithdrawView(BaseApiView):
    """
    Endpoint para saques de comissões.
    GET: lista saques do usuário (ou todos para admin).

    Criação de saque ocorre exclusivamente via CorbanPay em:
    POST /payments/withdrawals/corbanpay/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == User.ADMIN:
            withdrawals = Withdraw.objects.select_related('user', 'payment').all()
        elif user.role in (User.EMPRESA_ADMIN, User.GERENTE):
            withdrawals = Withdraw.objects.select_related('user', 'payment').filter(user__company=user.company)
        elif user.role == User.LIDER:
            withdrawals = Withdraw.objects.select_related('user', 'payment').filter(Q(user=user) | Q(user__leader=user))
        else:
            withdrawals = Withdraw.objects.select_related('user', 'payment').filter(user=user)
        serializer = WithdrawSerializer(withdrawals, many=True)
        return Response(serializer.data)
