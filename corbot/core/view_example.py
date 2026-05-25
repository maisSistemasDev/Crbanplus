from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404

from .models import User, Company
from .serializers import UserSerializer, UserCreateSerializer, CompanySerializer
from .base_views import BaseApiView


class ExampleUserListCreateView(BaseApiView):
    """
    Exemplo de view para listar e criar usuários utilizando BaseApiView.
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get(self, request, format=None):
        """
        Lista os usuários de acordo com a hierarquia do usuário autenticado.
        """
        user = request.user
        
        # Administrador ou Gerente vê todos os usuários
        if user.is_superuser or user.role == User.GERENTE:
            users = User.objects.all()
        # Líder vê apenas seus vendedores
        elif user.role == User.LIDER:
            users = User.objects.filter(leader=user)
        # Vendedor vê apenas ele mesmo
        else:
            users = User.objects.filter(id=user.id)
        
        serializer = UserSerializer(users, many=True)
        
        # Usando o método de log da classe base
        self.log_info(
            request=request,
            action='list_users',
            message=f'Usuário listou {users.count()} usuários'
        )
        
        return Response(serializer.data)
    
    def post(self, request, format=None):
        """
        Cria um novo usuário.
        """
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Usando o método de auditoria da classe base
            self.audit_create(
                request=request,
                instance=user,
                data_after=serializer.data
            )
            
            # Usando o método de log da classe base
            self.log_info(
                request=request,
                action='create_user',
                message=f'Usuário criou um novo usuário: {user.cpf}',
                data={'user_id': user.id}
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExampleCompanyDetailView(BaseApiView):
    """
    Exemplo de view para obter, atualizar e excluir uma empresa utilizando BaseApiView.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self, pk):
        return get_object_or_404(Company, pk=pk)
    
    def get(self, request, pk, format=None):
        """
        Recupera os detalhes de uma empresa específica.
        """
        company = self.get_object(pk)
        serializer = CompanySerializer(company)
        
        # Usando o método de log da classe base
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
            updated_company = serializer.save()
            
            # Usando o método de auditoria da classe base
            self.audit_update(
                request=request,
                instance=updated_company,
                data_before=old_data,
                data_after=serializer.data
            )
            
            # Usando o método de log da classe base
            self.log_info(
                request=request,
                action='update_company',
                message=f'Usuário atualizou a empresa: {updated_company.name}',
                data={'company_id': str(updated_company.id)}
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk, format=None):
        """
        Exclui uma empresa específica.
        """
        company = self.get_object(pk)
        
        # Captura os dados antes da exclusão
        data_before = CompanySerializer(company).data
        
        company_name = company.name
        company_id = str(company.id)
        
        # Usando o método de auditoria da classe base
        self.audit_delete(
            request=request,
            instance=company,
            data_before=data_before
        )
        
        company.delete()
        
        # Usando o método de log da classe base
        self.log_info(
            request=request,
            action='delete_company',
            message=f'Usuário excluiu a empresa: {company_name}',
            data={'company_id': company_id}
        )
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProposalImportView(BaseApiView):
    """View para importação de propostas a partir de arquivos."""
    
    def post(self, request, format=None):
        # Processa o arquivo enviado (suporta .json, .csv, .xlsx)
        data, file_path = self.process_file_upload(
            request, 
            supported_types=['.json', '.csv', '.xlsx']
        )
        
        if not data:
            return Response(
                {"detail": "Erro ao processar o arquivo"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Converte tipos de dados
        type_mapping = {
            'valor_solicitado': 'decimal',
            'data_nascimento': 'date',
            'ativo': 'boolean',
            'telefone': 'string'
        }
        data = self.convert_data_types(data, type_mapping)
        
        # Valida os dados
        required_fields = ['cpf', 'nome', 'valor_solicitado']
        allowed_values = {'tipo_proposta': ['1', '2', '3']}
        min_max_values = {'valor_solicitado': {'min': 500, 'max': 50000}}
        
        valid, errors = self.validate_data(
            data, 
            required_fields, 
            allowed_values, 
            min_max_values
        )
        
        if not valid:
            return Response(
                {"errors": errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Processar os dados válidos...
        
        # Registra a ação
        self.log_info(
            request=request,
            action='import_proposals',
            message=f'Usuário importou {len(data)} propostas',
            data={'file_path': file_path}
        )
        
        return Response({"detail": f"{len(data)} propostas importadas com sucesso"}) 