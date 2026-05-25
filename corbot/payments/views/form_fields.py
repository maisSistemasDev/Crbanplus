"""
Views relacionadas a campos de formulário para entidades de pagamento.
"""
from rest_framework.response import Response
from rest_framework import permissions

from core.base_views import BaseApiView
from payments.serializers import (
    CommissionGroupSerializer,
    PaymentSerializer,
    CommissionSerializer,
    CommissionGroupByCompanySerializer
)


class CommissionGroupFormFieldsView(BaseApiView):
    

    """
    API endpoint para obter os campos de formulário para o modelo ComissionGroup.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """
        Retorna os campos necessários para criar um formulário de grupo de comissionamento.
        """
        user = request.user
        
        serializer = CommissionGroupSerializer()
        form_fields = serializer.form_fields(user)
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='get_commission_group_form_fields',
            message='Usuário obteve campos de formulário para grupo de comissionamento'
        )
        
        return Response(form_fields)

class CommissionGroupByCompanyFormFieldsView(BaseApiView):
    """
    API endpoint para obter os campos de formulário para o modelo CommissionGroupByCompany.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """
        Retorna os campos necessários para criar um formulário de grupo de comissionamento por empresa.
        """
        serializer = CommissionGroupByCompanySerializer()
        form_fields = serializer.form_fields()
        return Response(form_fields)


class PaymentFormFieldsView(BaseApiView):
    """
    API endpoint para obter os campos de formulário para o modelo Payment.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """
        Retorna os campos necessários para criar um formulário de pagamento.
        """
        serializer = PaymentSerializer()
        form_fields = serializer.form_fields()
        
        self.log_info(
            request=request,
            action='get_payment_form_fields',
            message='Usuário obteve campos de formulário para pagamento'
        )
        
        return Response(form_fields)

