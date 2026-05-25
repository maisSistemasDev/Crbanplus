"""
Views relacionadas a operações com usuários.
Inclui listagem, criação, atualização e exclusão de usuários.
"""
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from django.shortcuts import get_object_or_404
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from core.base_views import BaseApiView
from core.models import User, ExtraData
from core.serializers import UserSerializer, UserCreateSerializer, UserListSerializer, CreateManagerSerializer
from core.permissions import IsAdmin, IsAdminOrEmpresaAdmin
from core.exceptions import format_serializer_errors


class UserListCreateView(BaseApiView):
    """
    API endpoint para listar e criar usuários.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """
        Lista os usuários de acordo com a hierarquia do usuário autenticado.
        """
        if(request.user.role == User.ADMIN):
            users = User.objects.filter(role__in=[User.ADMIN, User.EMPRESA_ADMIN, User.GERENTE])
        elif(request.user.role == User.EMPRESA_ADMIN):
            users = User.objects.filter(company=request.user.company, role__in=[User.GERENTE, User.LIDER, User.VENDEDOR])
        elif(request.user.role == User.GERENTE):
            users = User.objects.filter(company=request.user.company, role__in=[User.VENDEDOR, User.LIDER])
        elif(request.user.role == User.LIDER):
            users = User.objects.filter(leader=request.user)
        else:
            users = User.objects.filter(company=request.user.company, role__in=[User.VENDEDOR, User.LIDER])

        search = request.query_params.get('search', '').strip()
        if search:
            from django.db.models import Q
            users = users.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(cpf__icontains=search) |
                Q(email__icontains=search)
            )

        role = request.query_params.get('role', '').strip()
        if role:
            users = users.filter(role=role)

        self.log_info(
            request=request,
            action='list_users',
            message=f'Usuário listou usuários'
        )

        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 10
        page = paginator.paginate_queryset(users, request)
        serializer = UserListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request, format=None):
        """
        Cria um novo usuário.
        """
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_create(
                request=request,
                instance=user,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='create_user',
                message=f'Usuário criou um novo usuário: {user.cpf}',
                data={'user_id': user.id}
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        errors = format_serializer_errors(serializer.errors)
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(BaseApiView):
    """
    API endpoint para recuperar, atualizar e excluir um usuário específico.
    """
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            permission_classes = [IsAdminOrEmpresaAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_object(self, pk):
        user = get_object_or_404(User, pk=pk)
        requester = self.request.user
        # Empresa admin can only modify users in their company
        if requester.role == User.EMPRESA_ADMIN:
            if not user.company or user.company != requester.company:
                self.permission_denied(self.request)
        self.check_object_permissions(self.request, user)
        return user
    
    def get(self, request, pk, format=None):
        """
        Recupera os detalhes de um usuário específico.
        """
        user = self.get_object(pk)
        serializer = UserSerializer(user)
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='view_user',
            message=f'Usuário visualizou os detalhes do usuário: {user.cpf}',
            data={'user_id': user.id}
        )
        
        return Response(serializer.data)
    
    def put(self, request, pk, format=None):
        """
        Atualiza um usuário específico.
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
                action='update_user',
                message=f'Usuário atualizou o usuário: {updated_user.cpf}',
                data={'user_id': updated_user.id}
            )
            
            return Response(serializer.data)
        
        errors = format_serializer_errors(serializer.errors)
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk, format=None):
        """
        Atualiza parcialmente um usuário específico.
        """
        user = self.get_object(pk)
        
        # Captura os dados antes da atualização
        old_data = UserSerializer(user).data
        
        serializer = UserSerializer(user, data=request.data, partial=True)
            
        if serializer.is_valid():
            updated_user = serializer.save()
            #se o vendedor for convertido para líder, remove o líder vinculado
            if(old_data['role'] == User.VENDEDOR and request.data['role'] == User.LIDER):
                updated_user.leader = None
                updated_user.save()
                
            if(old_data['company'] != request.data['company'] and request.data['role'] == User.LIDER):
                sellers = User.objects.filter(leader=user)
                for seller in sellers:
                    seller.leader = None
                    seller.save()
                
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
                action='partial_update_user',
                message=f'Usuário atualizou parcialmente o usuário: {updated_user.cpf}',
                data={'user_id': updated_user.id, 'fields_updated': list(request.data.keys())}
            )
            
            return Response(serializer.data)
        
        errors = format_serializer_errors(serializer.errors)
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk, format=None):
        """
        Exclui um usuário específico.
        """
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
            action='delete_user',
            message=f'Usuário excluiu o usuário: {user.cpf}',
            data={'user_id': user.id, 'user_cpf': user.cpf}
        )
        
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class CreateManagerView(generics.CreateAPIView):
    """
    Endpoint para criar um novo usuário com a role de Gerente.
    Apenas administradores podem acessar este endpoint.
    """
    queryset = User.objects.all() # Não é necessário listar usuários aqui
    serializer_class = CreateManagerSerializer
    permission_classes = [IsAdminOrEmpresaAdmin]


class CurrentUserView(BaseApiView):
    """
    API endpoint para recuperar dados do usuário logado.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """
        Retorna os dados do usuário logado.
        """
        user = request.user
        serializer = UserSerializer(user)
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='view_self',
            message=f'Usuário visualizou seus próprios dados'
        )
        
        return Response(serializer.data) 

    def patch(self, request, format=None):
        """
        Atualiza dados do perfil do usuário logado.
        Campos bloqueados: cpf e matricula.
        """
        user = request.user
        payload = request.data.copy()

        blocked_fields = {'cpf', 'matricula'}
        attempted = [field for field in blocked_fields if field in payload]
        if attempted:
            return Response(
                {'detail': 'Não é permitido alterar CPF ou matrícula no perfil.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if 'password' in payload:
            return Response(
                {'detail': 'Use os campos current_password e new_password para alterar a senha.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        current_password = payload.pop('current_password', None)
        new_password = payload.pop('new_password', None)

        if bool(current_password) != bool(new_password):
            return Response(
                {'detail': 'Informe current_password e new_password juntos para alterar a senha.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password:
            if not user.check_password(current_password):
                return Response(
                    {'detail': 'Senha atual inválida.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                validate_password(new_password, user)
            except ValidationError as exc:
                return Response(
                    {'detail': 'Senha inválida.', 'errors': list(exc.messages)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = UserSerializer(user, data=payload, partial=True)
        if not serializer.is_valid():
            errors = format_serializer_errors(serializer.errors)
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        updated_user = serializer.save()

        if new_password:
            updated_user.set_password(new_password)
            updated_user.save(update_fields=['password'])

        self.log_info(
            request=request,
            action='update_self_profile',
            message='Usuário atualizou dados do próprio perfil',
        )

        return Response(UserSerializer(updated_user).data)