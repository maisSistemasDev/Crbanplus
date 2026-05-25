"""
Views para gerenciar usuários internos da promotora (Admin e Colaborador).
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from ..models import User, UserPermission, PermissionTemplate
from ..serializers import (
    InternalUserSerializer,
    UserPermissionSerializer,
    PermissionTemplateSerializer,
    CollaboratorPermissionsSerializer
)
from ..permissions import IsPromotoraAdmin


class InternalUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar usuários internos da promotora (Admin e Colaborador).
    Apenas Admin da promotora pode acessar.
    """
    serializer_class = InternalUserSerializer
    permission_classes = [IsAuthenticated, IsPromotoraAdmin]
    
    def get_queryset(self):
        """Retorna apenas usuários internos da promotora"""
        return User.objects.filter(
            Q(role=User.ADMIN) | Q(role=User.COLABORADOR),
            company__isnull=True
        ).order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """Cria um novo usuário interno"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response(
            {
                'message': 'Usuário interno criado com sucesso.',
                'user': InternalUserSerializer(user).data
            },
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """Atualiza um usuário interno"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response(
            {
                'message': 'Usuário interno atualizado com sucesso.',
                'user': InternalUserSerializer(user).data
            },
            status=status.HTTP_200_OK
        )
    
    def destroy(self, request, *args, **kwargs):
        """Deleta um usuário interno"""
        instance = self.get_object()
        
        # Não permite deletar o próprio usuário
        if instance.id == request.user.id:
            return Response(
                {'detail': 'Você não pode deletar seu próprio usuário.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.delete()
        return Response(
            {'message': 'Usuário interno deletado com sucesso.'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=['get'])
    def form_fields(self, request):
        """Retorna os campos do formulário para criação/edição"""
        serializer = self.get_serializer()
        return Response(serializer.form_fields())
    
    @action(detail=True, methods=['get', 'post'])
    def permissions(self, request, pk=None):
        """
        GET: Lista as permissões de um colaborador
        POST: Atualiza as permissões de um colaborador
        """
        user = self.get_object()
        
        if user.role != User.COLABORADOR:
            return Response(
                {'detail': 'Apenas colaboradores têm permissões gerenciadas.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if request.method == 'GET':
            permissions = user.custom_permissions.all()
            serializer = UserPermissionSerializer(permissions, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            # Atualiza as permissões
            data = {'user_id': user.id, 'permissions': request.data.get('permissions', [])}
            serializer = CollaboratorPermissionsSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            updated_user = serializer.save()
            
            return Response(
                {
                    'message': 'Permissões atualizadas com sucesso.',
                    'user': InternalUserSerializer(updated_user).data
                },
                status=status.HTTP_200_OK
            )
    
    @action(detail=False, methods=['get'])
    def available_permissions(self, request):
        """
        Retorna a lista de permissões disponíveis para atribuir a colaboradores.
        """
        permissions = [
            # Gestão de Corbans
            {'codename': 'view_corbans', 'name': 'Visualizar Corbans', 'category': UserPermission.CATEGORY_CORBANS},
            {'codename': 'create_corbans', 'name': 'Criar Corbans', 'category': UserPermission.CATEGORY_CORBANS},
            {'codename': 'edit_corbans', 'name': 'Editar Corbans', 'category': UserPermission.CATEGORY_CORBANS},
            {'codename': 'delete_corbans', 'name': 'Deletar Corbans', 'category': UserPermission.CATEGORY_CORBANS},
            
            # Gestão de Usuários
            {'codename': 'view_users', 'name': 'Visualizar Usuários', 'category': UserPermission.CATEGORY_USERS},
            {'codename': 'create_users', 'name': 'Criar Usuários', 'category': UserPermission.CATEGORY_USERS},
            {'codename': 'edit_users', 'name': 'Editar Usuários', 'category': UserPermission.CATEGORY_USERS},
            {'codename': 'delete_users', 'name': 'Deletar Usuários', 'category': UserPermission.CATEGORY_USERS},
            
            # Gestão de Propostas
            {'codename': 'view_proposals', 'name': 'Visualizar Propostas', 'category': UserPermission.CATEGORY_PROPOSALS},
            {'codename': 'create_proposals', 'name': 'Criar Propostas', 'category': UserPermission.CATEGORY_PROPOSALS},
            {'codename': 'edit_proposals', 'name': 'Editar Propostas', 'category': UserPermission.CATEGORY_PROPOSALS},
            {'codename': 'delete_proposals', 'name': 'Deletar Propostas', 'category': UserPermission.CATEGORY_PROPOSALS},
            {'codename': 'approve_proposals', 'name': 'Aprovar Propostas', 'category': UserPermission.CATEGORY_PROPOSALS},
            
            # Gestão de Pagamentos
            {'codename': 'view_payments', 'name': 'Visualizar Pagamentos', 'category': UserPermission.CATEGORY_PAYMENTS},
            {'codename': 'create_payments', 'name': 'Criar Pagamentos', 'category': UserPermission.CATEGORY_PAYMENTS},
            {'codename': 'edit_payments', 'name': 'Editar Pagamentos', 'category': UserPermission.CATEGORY_PAYMENTS},
            {'codename': 'approve_payments', 'name': 'Aprovar Pagamentos', 'category': UserPermission.CATEGORY_PAYMENTS},
            
            # Relatórios
            {'codename': 'view_reports', 'name': 'Visualizar Relatórios', 'category': UserPermission.CATEGORY_REPORTS},
            {'codename': 'export_reports', 'name': 'Exportar Relatórios', 'category': UserPermission.CATEGORY_REPORTS},
            
            # Configurações
            {'codename': 'view_settings', 'name': 'Visualizar Configurações', 'category': UserPermission.CATEGORY_SETTINGS},
            {'codename': 'edit_settings', 'name': 'Editar Configurações', 'category': UserPermission.CATEGORY_SETTINGS},
        ]
        
        # Agrupa por categoria
        grouped_permissions = {}
        for perm in permissions:
            category = perm['category']
            if category not in grouped_permissions:
                grouped_permissions[category] = {
                    'category': category,
                    'label': dict(UserPermission.CATEGORY_CHOICES).get(category, category),
                    'permissions': []
                }
            grouped_permissions[category]['permissions'].append(perm)
        
        return Response(list(grouped_permissions.values()))


class PermissionTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar templates de permissões.
    """
    queryset = PermissionTemplate.objects.all()
    serializer_class = PermissionTemplateSerializer
    permission_classes = [IsAuthenticated, IsPromotoraAdmin]
    
    @action(detail=True, methods=['post'])
    def apply_to_user(self, request, pk=None):
        """
        Aplica um template de permissões a um colaborador.
        """
        template = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'detail': 'user_id é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id, role=User.COLABORADOR)
        except User.DoesNotExist:
            return Response(
                {'detail': 'Usuário não encontrado ou não é um colaborador.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Remove permissões antigas
        user.custom_permissions.all().delete()
        
        # Busca detalhes das permissões disponíveis
        available_permissions = self._get_available_permissions_dict()
        
        # Adiciona permissões do template
        for codename in template.permissions:
            if codename in available_permissions:
                perm = available_permissions[codename]
                UserPermission.objects.create(
                    user=user,
                    codename=perm['codename'],
                    name=perm['name'],
                    category=perm['category']
                )
        
        return Response(
            {
                'message': f'Template "{template.name}" aplicado ao usuário com sucesso.',
                'user': InternalUserSerializer(user).data
            },
            status=status.HTTP_200_OK
        )
    
    def _get_available_permissions_dict(self):
        """Retorna dicionário de permissões disponíveis"""
        permissions = [
            {'codename': 'view_corbans', 'name': 'Visualizar Corbans', 'category': UserPermission.CATEGORY_CORBANS},
            {'codename': 'create_corbans', 'name': 'Criar Corbans', 'category': UserPermission.CATEGORY_CORBANS},
            {'codename': 'edit_corbans', 'name': 'Editar Corbans', 'category': UserPermission.CATEGORY_CORBANS},
            {'codename': 'delete_corbans', 'name': 'Deletar Corbans', 'category': UserPermission.CATEGORY_CORBANS},
            {'codename': 'view_users', 'name': 'Visualizar Usuários', 'category': UserPermission.CATEGORY_USERS},
            {'codename': 'create_users', 'name': 'Criar Usuários', 'category': UserPermission.CATEGORY_USERS},
            {'codename': 'edit_users', 'name': 'Editar Usuários', 'category': UserPermission.CATEGORY_USERS},
            {'codename': 'delete_users', 'name': 'Deletar Usuários', 'category': UserPermission.CATEGORY_USERS},
            {'codename': 'view_proposals', 'name': 'Visualizar Propostas', 'category': UserPermission.CATEGORY_PROPOSALS},
            {'codename': 'create_proposals', 'name': 'Criar Propostas', 'category': UserPermission.CATEGORY_PROPOSALS},
            {'codename': 'edit_proposals', 'name': 'Editar Propostas', 'category': UserPermission.CATEGORY_PROPOSALS},
            {'codename': 'delete_proposals', 'name': 'Deletar Propostas', 'category': UserPermission.CATEGORY_PROPOSALS},
            {'codename': 'approve_proposals', 'name': 'Aprovar Propostas', 'category': UserPermission.CATEGORY_PROPOSALS},
            {'codename': 'view_payments', 'name': 'Visualizar Pagamentos', 'category': UserPermission.CATEGORY_PAYMENTS},
            {'codename': 'create_payments', 'name': 'Criar Pagamentos', 'category': UserPermission.CATEGORY_PAYMENTS},
            {'codename': 'edit_payments', 'name': 'Editar Pagamentos', 'category': UserPermission.CATEGORY_PAYMENTS},
            {'codename': 'approve_payments', 'name': 'Aprovar Pagamentos', 'category': UserPermission.CATEGORY_PAYMENTS},
            {'codename': 'view_reports', 'name': 'Visualizar Relatórios', 'category': UserPermission.CATEGORY_REPORTS},
            {'codename': 'export_reports', 'name': 'Exportar Relatórios', 'category': UserPermission.CATEGORY_REPORTS},
            {'codename': 'view_settings', 'name': 'Visualizar Configurações', 'category': UserPermission.CATEGORY_SETTINGS},
            {'codename': 'edit_settings', 'name': 'Editar Configurações', 'category': UserPermission.CATEGORY_SETTINGS},
        ]
        
        return {perm['codename']: perm for perm in permissions}
