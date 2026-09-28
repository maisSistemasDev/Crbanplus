"""
Views relacionadas a operações com empresas.
Inclui listagem, criação, atualização e exclusão de empresas.
"""
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.utils import timezone
import re

from core.base_views import BaseApiView
from core.models import Company, User, validate_pix_binding
from core.serializers import CompanySerializer, UserSerializer
from core.permissions import IsAdmin, IsAdminOrEmpresaAdmin
from core.exceptions import format_serializer_errors
from core.search_utils import apply_company_list_search, paginate_queryset


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
        search = request.query_params.get('search', '').strip()

        # Promotora vê todos os corbans; gerente comercial vê a carteira; demais só o próprio
        if user.role in (User.ADMIN, User.COLABORADOR) and user.company is None:
            companies = Company.objects.filter(is_promotora=False)
        elif user.role == User.GERENTE_COMERCIAL:
            from commercial.services import team_company_ids_for
            companies = Company.objects.filter(id__in=team_company_ids_for(user))
        elif user.company:
            companies = Company.objects.filter(id=user.company.id)
        else:
            companies = Company.objects.none()

        companies = apply_company_list_search(companies, search).order_by('name')

        self.log_info(
            request=request,
            action='list_companies',
            message=f'Usuário listou corbans (busca={search!r})',
        )

        return paginate_queryset(request, companies, CompanySerializer)
    
    def post(self, request, format=None):
        """
        Cria uma nova empresa (corban) e o usuário admin associado.
        O vínculo do corban (usuário admin) é sempre feito por CPF de uma pessoa física —
        o documento da empresa (CNPJ, se PJ) é opcional e pode ser preenchido depois.
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

        # O vínculo do corban é sempre por CPF de uma pessoa física — nunca pelo
        # CNPJ da empresa. O CNPJ (document da Company) é opcional e independente.
        admin_cpf_raw = admin_user_data.get('cpf')
        if not admin_cpf_raw:
            return Response(
                {'detail': 'CPF do administrador é obrigatório (admin_user.cpf). O CNPJ da empresa é opcional.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        admin_cpf = re.sub(r'\D', '', admin_cpf_raw)
        if len(admin_cpf) != 11:
            return Response(
                {'detail': 'CPF do administrador inválido (deve conter 11 dígitos).'},
                status=status.HTTP_400_BAD_REQUEST
            )

        extra_data = admin_user_data.get('extra_data') or {}
        pix_error = validate_pix_binding(
            pix_type=extra_data.get('pix_type'),
            pix_key=extra_data.get('pix_key'),
            cpf=admin_cpf,
            cnpj=company_data.get('document'),
        )
        if pix_error:
            return Response({'detail': pix_error}, status=status.HTTP_400_BAD_REQUEST)
        
        # Criar a empresa
        company = company_serializer.save()
        
        # Perfil admin deste corban — vendedor com mesmo CPF é outro registro
        if User.objects.filter(role=User.EMPRESA_ADMIN, company=company).exists():
            company.delete()
            return Response(
                {'detail': f'Já existe administrador para o corban {company.name}.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Email: usar o da empresa, ou o fornecido, ou gerar um padrão
        email = admin_user_data.get('email') or company.email
        if not email:
            email = f'{admin_cpf}@corban.local'
        
        # Criar o usuário admin vinculado à empresa (login sempre pelo CPF da pessoa)
        user = User.objects.create_user(
            cpf=admin_cpf,
            login_document=admin_cpf,
            password=password,
            email=email,
            first_name=admin_user_data.get('first_name') or company.name,
            last_name=admin_user_data.get('last_name') or '',
            matricula=matricula,
            certificado=certificado,
            role=User.EMPRESA_ADMIN,
            company=company,
            is_active=True,
        )

        if extra_data:
            from core.models import ExtraData
            ExtraData.objects.create(user=user, **extra_data)
        
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
        if user.role == User.GERENTE_COMERCIAL:
            from commercial.services import team_company_ids_for
            if company.id not in team_company_ids_for(user):
                self.permission_denied(self.request)
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


class CompanyActivationView(BaseApiView):
    """
    API endpoint para inativar/reativar um corban, com registro de
    data/hora, motivo e responsável pela inativação.
    """
    permission_classes = [IsAdminOrEmpresaAdmin]

    def get_object(self, pk):
        return get_object_or_404(Company, pk=pk)

    def post(self, request, pk, format=None):
        """
        Body: {"action": "deactivate", "reason": "..."} ou {"action": "activate"}.
        """
        company = self.get_object(pk)
        action = (request.data.get('action') or 'deactivate').strip().lower()
        old_data = CompanySerializer(company).data

        if action == 'activate':
            company.reactivate()
            message = f'Usuário reativou o corban: {company.name}'
            audit_action = 'activate_company'
        else:
            reason = (request.data.get('reason') or '').strip()
            if not reason:
                return Response(
                    {'detail': 'Motivo da inativação é obrigatório (reason).'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            company.deactivate(by_user=request.user, reason=reason)
            message = f'Usuário inativou o corban: {company.name} (motivo: {reason})'
            audit_action = 'deactivate_company'

        serializer = CompanySerializer(company)
        self.audit_update(
            request=request,
            instance=company,
            data_before=old_data,
            data_after=serializer.data,
        )
        self.log_info(
            request=request,
            action=audit_action,
            message=message,
            data={
                'company_id': str(company.id),
                'inactivated_at': company.inactivated_at.isoformat() if company.inactivated_at else None,
                'inactivation_reason': company.inactivation_reason,
            },
        )
        return Response(serializer.data)