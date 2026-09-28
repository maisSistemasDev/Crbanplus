from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404

from .models import BankAccess, AccessLog
from .serializers import BankAccessSerializer, AccessLogSerializer
from .services import bank_access_queryset_for_actor, filter_bank_accesses_by_user_profile
from core.permissions import IsGerente, IsGerenteOrLider, IsAdmin, IsAdminOrGerente, IsAdminOrGerenteOrLider
from core.base_views import BaseApiView


# Views para retornar os campos de formulário
class BankAccessFormFieldsView(BaseApiView):
    """
    API endpoint para obter os campos de formulário para o modelo BankAccess.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """
        Retorna os campos necessários para criar um formulário de acesso bancário.
        """
        serializer = BankAccessSerializer()
        form_fields = serializer.form_fields()
        
        self.log_info(
            request=request,
            action='get_bank_access_form_fields',
            message='Usuário obteve campos de formulário para acesso bancário'
        )
        
        return Response(form_fields)


class AccessLogFormFieldsView(BaseApiView):
    """
    API endpoint para obter os campos de formulário para o modelo AccessLog.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """
        Retorna os campos necessários para criar um formulário de log de acesso.
        """
        serializer = AccessLogSerializer()
        form_fields = serializer.form_fields()
        
        self.log_info(
            request=request,
            action='get_access_log_form_fields',
            message='Usuário obteve campos de formulário para log de acesso'
        )
        
        return Response(form_fields)


class BankAccessListCreateView(BaseApiView):
    """
    API endpoint para listar e criar acessos bancários.
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            permission_classes = [IsAdminOrGerente]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get(self, request, format=None):
        """
        Lista os acessos bancários de acordo com a hierarquia do usuário.
        """
        user = request.user

        qs = BankAccess.objects.select_related('bank', 'user', 'created_by')
        accesses = bank_access_queryset_for_actor(qs, user)

        self.log_info(
            request=request,
            action='list_bank_accesses',
            message=f'Usuário listou acessos bancários'
        )

        search = request.query_params.get('search', '').strip()
        if search:
            from django.db.models import Q
            accesses = accesses.filter(
                Q(username__icontains=search) |
                Q(bank__name__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__cpf__icontains=search)
            )

        bank_id = request.query_params.get('bank', '').strip()
        if bank_id:
            accesses = accesses.filter(bank_id=bank_id)

        user_id = request.query_params.get('user', '').strip()
        if user_id:
            accesses = filter_bank_accesses_by_user_profile(accesses, user_id)

        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        try:
            page_size = int(request.query_params.get('page_size', 10))
            paginator.page_size = min(max(page_size, 1), 100)
        except (TypeError, ValueError):
            paginator.page_size = 10
        page = paginator.paginate_queryset(accesses, request)
        serializer = BankAccessSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request, format=None):
        """
        Cria um novo acesso bancário.
        """
        # Adiciona o próprio usuário como criador
        data = request.data.copy()
        if not data.get('created_by'):
            data['created_by'] = request.user.id
        
        serializer = BankAccessSerializer(data=data)
        if serializer.is_valid():
            bank_access = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_create(
                request=request,
                instance=bank_access,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='create_bank_access',
                message=f'Usuário criou um novo acesso bancário: {bank_access.username} ({bank_access.bank.name})',
                data={'bank_access_id': str(bank_access.id)}
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BankAccessDetailView(BaseApiView):
    """
    API endpoint para recuperar, atualizar e excluir um acesso bancário específico.
    """
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            permission_classes = [IsAdminOrGerente]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_object(self, pk, user):
        """
        Obtém o acesso bancário de acordo com a hierarquia do usuário.
        """
        qs = BankAccess.objects.select_related('bank', 'user', 'created_by')
        accesses = bank_access_queryset_for_actor(qs, user)
        return get_object_or_404(accesses, pk=pk)
    
    def get(self, request, pk, format=None):
        """
        Recupera um acesso bancário específico.
        """
        bank_access = self.get_object(pk, request.user)
        serializer = BankAccessSerializer(bank_access)
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='retrieve_bank_access',
            message=f'Usuário visualizou o acesso bancário: {bank_access.username} ({bank_access.bank.name})',
            data={'bank_access_id': str(bank_access.id)}
        )
        
        return Response(serializer.data)
    
    def put(self, request, pk, format=None):
        """
        Atualiza um acesso bancário específico.
        """
        bank_access = self.get_object(pk, request.user)
        
        # Captura os dados antes da atualização
        old_data = BankAccessSerializer(bank_access).data
        
        serializer = BankAccessSerializer(bank_access, data=request.data)
        if serializer.is_valid():
            bank_access = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,
                instance=bank_access,
                data_before=old_data,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='update_bank_access',
                message=f'Usuário atualizou o acesso bancário: {bank_access.username} ({bank_access.bank.name})',
                data={'bank_access_id': str(bank_access.id)}
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk, format=None):
        """
        Atualiza parcialmente um acesso bancário específico.
        """
        bank_access = self.get_object(pk, request.user)
        
        # Captura os dados antes da atualização
        old_data = BankAccessSerializer(bank_access).data
        
        serializer = BankAccessSerializer(bank_access, data=request.data, partial=True)
        if serializer.is_valid():
            bank_access = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,
                instance=bank_access,
                data_before=old_data,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='partial_update_bank_access',
                message=f'Usuário atualizou parcialmente o acesso bancário: {bank_access.username} ({bank_access.bank.name})',
                data={'bank_access_id': str(bank_access.id)}
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk, format=None):
        """
        Exclui um acesso bancário específico.
        """
        bank_access = self.get_object(pk, request.user)
        
        # Captura os dados antes da exclusão
        old_data = BankAccessSerializer(bank_access).data
        
        # Registra a auditoria usando o método da classe base
        self.audit_delete(
            request=request,
            instance=bank_access,
            data_before=old_data
        )
        
        bank_access_str = f"{bank_access.username} ({bank_access.bank.name})"
        bank_access_id = str(bank_access.id)
        
        bank_access.delete()
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='delete_bank_access',
            message=f'Usuário excluiu o acesso bancário: {bank_access_str}',
            data={'bank_access_id': bank_access_id}
        )
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class AccessLogListView(BaseApiView):
    """
    API endpoint para listar logs de acesso.
    """
    permission_classes = [IsAdminOrGerenteOrLider]
    
    def get(self, request, format=None):
        """
        Lista os logs de acesso.
        """
        user = request.user
        
        qs = AccessLog.objects.select_related('bank_access__bank', 'bank_access__user', 'user')

        # Filtra os logs por bancos e usuários de acordo com as permissões do usuário
        if user.role == user.ADMIN:
            # Administrador vê todos os logs
            logs = qs.all()
        elif user.role == user.GERENTE and user.company:
            # Gerente vê os logs dos usuários da sua empresa
            logs = qs.filter(bank_access__user__company=user.company)
        elif user.role == user.LIDER:
            # Líder vê os logs dos seus vendedores
            team_users = user.team_members.all()
            logs = qs.filter(bank_access__user__in=team_users)
        else:
            # Vendedor vê apenas seus próprios logs
            logs = qs.filter(bank_access__user=user)
        
        # Filtragem por usuário, se especificado
        user_id = request.query_params.get('user_id')
        if user_id:
            logs = logs.filter(bank_access__user__id=user_id)
        
        # Filtragem por banco, se especificado
        bank_id = request.query_params.get('bank_id')
        if bank_id:
            logs = logs.filter(bank_access__bank__id=bank_id)
        
        # Filtragem por data de início, se especificada
        start_date = request.query_params.get('start_date')
        if start_date:
            logs = logs.filter(created_at__gte=start_date)
        
        # Filtragem por data de fim, se especificada
        end_date = request.query_params.get('end_date')
        if end_date:
            logs = logs.filter(created_at__lte=end_date)
        
        # Ordenação por data decrescente
        logs = logs.order_by('-created_at')
        
        serializer = AccessLogSerializer(logs, many=True)
        result = serializer.data
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='list_access_logs',
            message=f'Usuário listou {len(result)} logs de acesso bancário'
        )
        
        return Response(result)