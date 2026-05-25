"""
Views relacionadas a campos de formulário.
Estas views fornecem metadados dos campos para o frontend construir formulários dinamicamente.
"""
from rest_framework.response import Response
from rest_framework import permissions

from core.base_views import BaseApiView
from core.serializers import (
    UserSerializer, 
    UserCreateSerializer, 
    CompanySerializer, 
    CreateManagerSerializer,
    ExtraDataSerializer,
)


class UserFormFieldsView(BaseApiView):
    """
    API endpoint para obter os campos de formulário para o modelo User.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """
        Retorna os campos necessários para criar um formulário de usuário.
        """
        serializer = UserSerializer()
        form_fields = serializer.form_fields(instance=request.user)
        
        self.log_info(
            request=request,
            action='get_user_form_fields',
            message='Usuário obteve campos de formulário para usuário'
        )
        
        return Response(form_fields)


class UserCreateFormFieldsView(BaseApiView):
    """
    API endpoint para obter os campos de formulário para criar um usuário.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """
        Retorna os campos necessários para criar um formulário de criação de usuário.
        """
        serializer = UserCreateSerializer()
        form_fields = serializer.form_fields(instance=request.user)
        
        self.log_info(
            request=request,
            action='get_user_create_form_fields',
            message='Usuário obteve campos de formulário para criação de usuário'
        )
        
        return Response(form_fields)


class CompanyFormFieldsView(BaseApiView):
    """
    API endpoint para obter os campos de formulário para o modelo Company.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """
        Retorna os campos necessários para criar um formulário de empresa.
        """
        serializer = CompanySerializer()
        form_fields = serializer.form_fields(instance=request.user.company)
        
        self.log_info(
            request=request,
            action='get_company_form_fields',
            message='Usuário obteve campos de formulário para empresa'
        )
        
        return Response(form_fields)


class ExtraDataFormFieldsView(BaseApiView):
    """
    API endpoint para obter os campos de formulário para o modelo ExtraData.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """
        Retorna os campos necessários para criar um formulário de dados extras.
        """
        serializer = ExtraDataSerializer()
        form_fields = serializer.form_fields()
        
        self.log_info(
            request=request,
            action='get_extra_data_form_fields',
            message='Usuário obteve campos de formulário para dados extras'
        )
        
        return Response(form_fields)


class CreateManagerFormFieldsView(BaseApiView):
    """
    API endpoint para obter os campos de formulário para criar um gerente.
    """
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request, format=None):
        """
        Retorna os campos necessários para criar um formulário de criação de gerente.
        """
        serializer = CreateManagerSerializer()
        form_fields = serializer.form_fields()
        
        self.log_info(
            request=request,
            action='get_create_manager_form_fields',
            message='Usuário obteve campos de formulário para criação de gerente'
        )
        
        return Response(form_fields)

