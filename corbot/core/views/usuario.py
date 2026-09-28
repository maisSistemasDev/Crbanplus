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
from core.search_utils import apply_user_list_search, paginate_queryset


class UserListCreateView(BaseApiView):
    """
    API endpoint para listar e criar usuários.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """
        Lista os usuários de acordo com a hierarquia do usuário autenticado.
        """
        search = request.query_params.get('search', '').strip()
        role = request.query_params.get('role', '').strip()
        company_id = request.query_params.get('company', '').strip()

        if request.user.role in (User.ADMIN, User.COLABORADOR):
            # Promotora controla toda a rede de corbans
            corban_roles = [User.EMPRESA_ADMIN, User.GERENTE, User.LIDER, User.VENDEDOR]
            if role:
                users = User.objects.filter(role=role)
            else:
                users = User.objects.filter(role__in=corban_roles)
        elif request.user.role == User.GERENTE_COMERCIAL:
            from commercial.services import team_company_ids_for
            company_ids = team_company_ids_for(request.user)
            users = User.objects.filter(
                company_id__in=company_ids,
                role__in=[User.EMPRESA_ADMIN, User.GERENTE, User.LIDER, User.VENDEDOR],
            )
        elif request.user.role == User.EMPRESA_ADMIN:
            users = User.objects.filter(
                company=request.user.company,
                role__in=[User.EMPRESA_ADMIN, User.GERENTE, User.LIDER, User.VENDEDOR],
            )
        elif request.user.role == User.GERENTE:
            users = User.objects.filter(
                company=request.user.company,
                role__in=[User.VENDEDOR, User.LIDER],
            )
        elif request.user.role == User.LIDER:
            users = User.objects.filter(leader=request.user)
        else:
            users = User.objects.filter(
                company=request.user.company,
                role__in=[User.VENDEDOR, User.LIDER],
            )

        users = apply_user_list_search(users, search)

        # Filtro por role para perfis de corban (promotora já filtrou acima)
        if role and request.user.role not in (User.ADMIN, User.COLABORADOR):
            users = users.filter(role=role)

        if company_id:
            users = users.filter(company_id=company_id)

        self.log_info(
            request=request,
            action='list_users',
            message=f'Usuário listou usuários'
        )

        return paginate_queryset(request, users, UserListSerializer)
    
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
            if self.request.user.is_authenticated and self.request.user.role == User.GERENTE_COMERCIAL:
                permission_classes = [permissions.IsAuthenticated]
            else:
                permission_classes = [IsAdminOrEmpresaAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_object(self, pk):
        user = get_object_or_404(User, pk=pk)
        requester = self.request.user
        if requester.role == User.EMPRESA_ADMIN:
            if not user.company or user.company != requester.company:
                self.permission_denied(self.request)
        if requester.role == User.GERENTE_COMERCIAL:
            from commercial.services import team_company_ids_for
            company_ids = team_company_ids_for(requester)
            if not user.company_id or user.company_id not in company_ids:
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
        
        payload = request.data
        if request.user.role == User.GERENTE_COMERCIAL:
            allowed = {}
            if 'email' in request.data:
                allowed['email'] = request.data.get('email')
            if 'password' in request.data:
                allowed['password'] = request.data.get('password')
            extra = request.data.get('extra_data') or {}
            pix = {}
            if isinstance(extra, dict):
                if 'pix_key' in extra:
                    pix['pix_key'] = extra.get('pix_key')
                if 'pix_type' in extra:
                    pix['pix_type'] = extra.get('pix_type')
            if pix:
                allowed['extra_data'] = pix
            payload = allowed
        
        serializer = UserSerializer(user, data=payload, partial=True)
            
        if serializer.is_valid():
            updated_user = serializer.save()
            #se o vendedor for convertido para líder, remove o líder vinculado
            if(old_data['role'] == User.VENDEDOR and request.data.get('role') == User.LIDER):
                updated_user.leader = None
                updated_user.save()

            if(old_data['company'] != request.data.get('company', old_data['company']) and request.data.get('role') == User.LIDER):
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
        if request.user.role == User.GERENTE_COMERCIAL:
            return Response(
                {'detail': 'Gerente comercial não pode excluir usuários.'},
                status=status.HTTP_403_FORBIDDEN,
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
            action='delete_user',
            message=f'Usuário excluiu o usuário: {user.cpf}',
            data={'user_id': user.id, 'user_cpf': user.cpf}
        )
        
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserActivationView(BaseApiView):
    """
    API endpoint para inativar/reativar um usuário, com registro de
    data/hora, motivo e responsável pela inativação.
    """
    permission_classes = [IsAdminOrEmpresaAdmin]

    def get_object(self, pk):
        user = get_object_or_404(User, pk=pk)
        requester = self.request.user
        if requester.role == User.EMPRESA_ADMIN:
            if not user.company or user.company != requester.company:
                self.permission_denied(self.request)
        return user

    def post(self, request, pk, format=None):
        """
        Body: {"action": "deactivate", "reason": "..."} ou {"action": "activate"}.
        """
        user = self.get_object(pk)
        action = (request.data.get('action') or 'deactivate').strip().lower()
        old_data = UserSerializer(user).data

        if action == 'activate':
            user.reactivate()
            message = f'Usuário reativou o usuário: {user.cpf}'
            audit_action = 'activate_user'
        else:
            reason = (request.data.get('reason') or '').strip()
            if not reason:
                return Response(
                    {'detail': 'Motivo da inativação é obrigatório (reason).'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.deactivate(by_user=request.user, reason=reason)
            message = f'Usuário inativou o usuário: {user.cpf} (motivo: {reason})'
            audit_action = 'deactivate_user'

        serializer = UserSerializer(user)
        self.audit_update(
            request=request,
            instance=user,
            data_before=old_data,
            data_after=serializer.data,
        )
        self.log_info(
            request=request,
            action=audit_action,
            message=message,
            data={
                'user_id': user.id,
                'inactivated_at': user.inactivated_at.isoformat() if user.inactivated_at else None,
                'inactivation_reason': user.inactivation_reason,
            },
        )
        return Response(serializer.data)


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