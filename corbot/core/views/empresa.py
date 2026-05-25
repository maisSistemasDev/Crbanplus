"""
Views relacionadas a operações com empresas.
Inclui listagem, criação, atualização e exclusão de empresas.
"""
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
import re

from core.base_views import BaseApiView
from core.models import Company, User
from core.serializers import CompanySerializer, UserSerializer
from core.permissions import IsAdmin, IsAdminOrEmpresaAdmin
from core.exceptions import format_serializer_errors


class CompanyListCreateView(BaseApiView):
    """
    API endpoint para listar e criar empresas.
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            permission_classes = [IsAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get(self, request, format=None):
        """
        Lista as empresas (excluindo a promotora).
        """
        user = request.user

        # Admin vê todas as empresas, exceto a promotora
        if user.role == User.ADMIN:
            companies = Company.objects.filter(is_promotora=False)
        # Outros usuários veem apenas sua própria empresa
        elif user.company:
            companies = Company.objects.filter(id=user.company.id)
        else:
            companies = Company.objects.none()
        
        serializer = CompanySerializer(companies, many=True)
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='list_companies',
            message=f'Usuário listou {companies.count()} empresas'
        )
        
        return Response(serializer.data)
    
    def post(self, request, format=None):
        """
        Cria uma nova empresa (corban) e o usuário admin associado.
        O documento da empresa (CPF ou CNPJ) será usado como credencial de login.
        """
        company_data = request.data.get('company', request.data)
        admin_user_data = request.data.get('admin_user', {})
        
        # Validar dados da empresa
        company_serializer = CompanySerializer(data=company_data)
        if not company_serializer.is_valid():
            errors = format_serializer_errors(company_serializer.errors)
            return Response({'company_errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar dados do usuário admin
        if not admin_user_data:
            return Response(
                {'detail': 'Dados do usuário admin são obrigatórios (admin_user).'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar campos obrigatórios do usuário admin
        password = admin_user_data.get('password')
        matricula = admin_user_data.get('matricula') or None
        certificado = admin_user_data.get('certificado') or None
        
        if not password:
            return Response(
                {'detail': 'Senha é obrigatória para o usuário admin.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Criar a empresa
        company = company_serializer.save()
        
        # Usar o documento da empresa como CPF/CNPJ do usuário admin
        user_document = company.document  # Já está normalizado (sem formatação)
        
        # Verificar se já existe usuário com esse documento
        if User.objects.filter(cpf=user_document).exists():
            # Se o usuário já existe, deletar a empresa criada e retornar erro
            company.delete()
            return Response(
                {'detail': f'Já existe um usuário com o documento {user_document}.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Email: usar o da empresa, ou o fornecido, ou gerar um padrão
        email = admin_user_data.get('email') or company.email
        if not email:
            # Gerar email padrão se não fornecido
            email = f'{user_document}@corban.local'
        
        # Criar o usuário admin vinculado à empresa
        user = User.objects.create_user(
            cpf=user_document,  # Usa o mesmo documento da empresa
            password=password,
            email=email,
            first_name=company.name,  # Nome do usuário é o nome da empresa
            last_name='',
            matricula=matricula,
            certificado=certificado,
            role=User.EMPRESA_ADMIN,
            company=company,
            is_active=True,
        )
        
        # Registra a auditoria usando o método da classe base
        self.audit_create(
            request=request,
            instance=company,
            data_after=company_serializer.data
        )
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='create_company',
            message=f'Usuário criou uma nova empresa: {company.name} com admin {user.cpf}',
            data={'company_id': str(company.id), 'admin_user_id': user.id}
        )
        
        # Retornar dados da empresa e do usuário criado
        user_serializer = UserSerializer(user)
        return Response({
            'company': company_serializer.data,
            'admin_user': user_serializer.data,
        }, status=status.HTTP_201_CREATED)


class CompanyDetailView(BaseApiView):
    """
    API endpoint para recuperar, atualizar e excluir uma empresa específica.
    """
    def get_permissions(self):
        if self.request.method == 'DELETE':
            permission_classes = [IsAdmin]
        elif self.request.method in ['PUT', 'PATCH']:
            permission_classes = [IsAdminOrEmpresaAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_object(self, pk):
        company = get_object_or_404(Company, pk=pk)
        user = self.request.user

        # Admin can access any company
        if user.role == User.ADMIN:
            return company
        # Empresa admin and others can only access their own company
        if not user.company or str(user.company.id) != pk:
            self.permission_denied(self.request)

        return company
    
    def get(self, request, pk, format=None):
        """
        Recupera os detalhes de uma empresa específica.
        """
        company = self.get_object(pk)
        serializer = CompanySerializer(company)
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='retrieve_company',
            message=f'Usuário visualizou a empresa: {company.name}',
            data={'company_id': str(company.id)}
        )
        
        return Response(serializer.data)
    
    def put(self, request, pk, format=None):
        """
        Atualiza uma empresa específica.
        """
        company = self.get_object(pk)
        
        # Captura os dados antes da atualização
        old_data = CompanySerializer(company).data
        
        serializer = CompanySerializer(company, data=request.data)
        if serializer.is_valid():
            company = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,
                instance=company,
                data_before=old_data,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='update_company',
                message=f'Usuário atualizou a empresa: {company.name}',
                data={'company_id': str(company.id)}
            )
            
            return Response(serializer.data)
        
        errors = format_serializer_errors(serializer.errors)
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk, format=None):
        """
        Atualiza parcialmente uma empresa específica.
        """
        company = self.get_object(pk)
        
        # Captura os dados antes da atualização
        old_data = CompanySerializer(company).data
        
        serializer = CompanySerializer(company, data=request.data, partial=True)
        if serializer.is_valid():
            company = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,
                instance=company,
                data_before=old_data,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='partial_update_company',
                message=f'Usuário atualizou parcialmente a empresa: {company.name}',
                data={'company_id': str(company.id)}
            )
            
            return Response(serializer.data)
        
        errors = format_serializer_errors(serializer.errors)
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk, format=None):
        """
        Exclui uma empresa específica.
        """
        company = self.get_object(pk)
        
        # Captura os dados antes da exclusão
        data_before = CompanySerializer(company).data
        
        company_name = company.name
        company_id = str(company.id)
        
        # Registra a auditoria usando o método da classe base
        self.audit_delete(
            request=request,
            instance=company,
            data_before=data_before
        )
        
        company.delete()
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='delete_company',
            message=f'Usuário excluiu a empresa: {company_name}',
            data={'company_id': company_id}
        )
        
        return Response(status=status.HTTP_204_NO_CONTENT) 