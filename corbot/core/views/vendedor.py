from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import status, permissions
from rest_framework.response import Response

from core.models import User, Company, ExtraData
from core.serializers import UserSerializer, UserListSerializer, UserCreateSerializer
from core.permissions import IsAdminOrGerenteOrLider
from core.base_views import BaseApiView
from core.exceptions import format_serializer_errors

class VendedoresListView(BaseApiView):
    """
    API endpoint para listar vendedores.
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            permission_classes = [IsAdminOrGerenteOrLider]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get(self, request, format=None):
        """
        Lista usuários para mapeamento de lote (Gerente, Lider, Vendedor, Admin_Empresa).
        Exclui Admin da Promotora.
        """
        user = request.user

        # Roles válidas para o mapeamento de lote (exclui ADMIN da promotora)
        valid_roles = [User.VENDEDOR, User.LIDER, User.GERENTE, User.EMPRESA_ADMIN]

        if user.role == User.ADMIN:
            # Admin vê todos os usuários válidos (menos ele mesmo que é ADMIN)
            vendedores = User.objects.filter(role__in=valid_roles)
        elif user.role in (User.EMPRESA_ADMIN, User.GERENTE):
            company = user.company
            # Empresa admin e Gerente veem usuários válidos da sua empresa
            vendedores = User.objects.filter(role__in=valid_roles, company=company)
        elif user.role == User.LIDER:
            company = user.company
            # Lider vê seus vendedores e outros líderes/gerentes da sua empresa
            vendedores = User.objects.filter(
                Q(role=User.VENDEDOR, leader=user, company=company) |
                Q(role__in=[User.LIDER, User.GERENTE, User.EMPRESA_ADMIN], company=company)
            )
        else:
            return Response({"detail": "Permissão negada."}, status=status.HTTP_403_FORBIDDEN)

        serializer = UserListSerializer(vendedores, many=True)

        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='list_vendedores',
            message=f'Usuário listou {vendedores.count()} usuários para mapeamento'
        )

        return Response(serializer.data)
    
    
    def post(self, request, format=None):
        """
        Cria um novo vendedor.
        """
        extra_data = request.data.pop('extra_data', None)
        serializer = UserCreateSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            if extra_data:
                ExtraData.objects.create(user=user, **extra_data)
            else:
                ExtraData.objects.create(user=user)
            
            # Registra a auditoria usando o método da classe base
            self.audit_create(
                request=request,
                instance=user,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='create_vendedor',
                message=f'Usuário criou um novo vendedor: {user.cpf}',
                data={'user_id': user.id}
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        errors = format_serializer_errors(serializer.errors)
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)


class VendedorDetailView(BaseApiView):
    """
    API endpoint para recuperar, atualizar e excluir um vendedor específico.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk):
        vendedor = get_object_or_404(User, pk=pk)
        requester = self.request.user

        # Admin vê tudo
        if requester.role == User.ADMIN:
            return vendedor
        # Empresa admin e Gerente veem vendedores da sua empresa
        if requester.role in (User.EMPRESA_ADMIN, User.GERENTE):
            if vendedor.company != requester.company:
                self.permission_denied(self.request)
            return vendedor
        # Lider vê seus vendedores
        if requester.role == User.LIDER:
            if vendedor.leader != requester and vendedor != requester:
                self.permission_denied(self.request)
            return vendedor
        # Vendedor vê apenas a si mesmo
        if vendedor != requester:
            self.permission_denied(self.request)
        return vendedor
    
    def get(self, request, pk, format=None):
        """
        Recupera os detalhes de um vendedor específico.
        """
        user = self.get_object(pk)
        serializer = UserSerializer(user)

        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='view_vendedor',
            message=f'Usuário visualizou os detalhes do vendedor: {user.cpf}',
            data={'user_id': user.id}   
        )

        return Response(serializer.data)
    
    def put(self, request, pk, format=None):
        """
        Atualiza um vendedor específico.
        """
        user = self.get_object(pk)
        
        # Captura os dados antes da atualização
        old_data = UserSerializer(user).data
        
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            updated_user = serializer.save()    
            
            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,
                instance=updated_user,
                data_before=old_data,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='update_vendedor',
                message=f'Usuário atualizou o vendedor: {updated_user.cpf}',
                data={'user_id': updated_user.id, 'fields_updated': list(request.data.keys())}
            )
            
            return Response(serializer.data)
        
        errors = format_serializer_errors(serializer.errors)
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)  
    
    def delete(self, request, pk, format=None):
        """
        Exclui um vendedor específico.
        """
        
        if(request.user.role not in (User.ADMIN, User.EMPRESA_ADMIN)):
            return Response(
                {"detail": "Apenas administradores podem excluir vendedores."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object(pk)
        
        # Captura os dados antes da exclusão
        old_data = UserSerializer(user).data
        
        # Registra a auditoria usando o método da classe base
        self.audit_delete(
            request=request,
            instance=user,
            data_before=old_data
        )
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='delete_vendedor',
            message=f'Usuário excluiu o vendedor: {user.cpf}',  
            data={'user_id': user.id, 'user_cpf': user.cpf}
        )
        
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def patch(self, request, pk, format=None):
        """
        Atualiza parcialmente um vendedor.
        """
        user = self.get_object(pk)  
        
        # Captura os dados antes da atualização
        old_data = UserSerializer(user).data
        
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            updated_user = serializer.save()

            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,
                instance=updated_user,
                data_before=old_data,
                data_after=serializer.data  
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='partial_update_vendedor',
                message=f'Usuário atualizou parcialmente o vendedor: {updated_user.cpf}',
                data={'user_id': updated_user.id, 'fields_updated': list(request.data.keys())}
            )
            
            return Response(serializer.data)
        
        errors = format_serializer_errors(serializer.errors)
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
