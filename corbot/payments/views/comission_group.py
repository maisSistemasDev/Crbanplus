"""
Views relacionadas a operações com grupos de comissionamento.
"""
from decimal import Decimal
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.http import HttpResponse
import csv
import io
import logging

from core.base_views import BaseApiView
from core.permissions import IsGerente, IsAdmin, IsLider, IsAdminOrGerente, IsAdminOrGerenteOrLider
from core.models import User
from core.models import Company
from payments.models import CommissionGroup, CommissionGroupByCompany, CommissionRules, CommissionRulesByUser
from payments.serializers import CommissionGroupSerializer, CommissionGroupByCompanySerializer, CommissionRulesSerializer, CommissionRulesByUserSerializer
from bank.models import Bank, Table, normalize_name

logger = logging.getLogger(__name__)


def validate_company_rules(rules_data, company):
    """
    Valida que as taxas de CommissionRulesByUser de um CommissionGroup (empresa)
    não excedem as taxas definidas no CommissionGroupByCompany da promotora.
    """
    errors = []
    company_group = CommissionGroupByCompany.objects.filter(
        companies=company, is_active=True
    ).first()

    if not company_group:
        return errors

    max_rates = {}
    for rule in company_group.comission_rules.all():
        key = (str(rule.bank_id), str(rule.table_id))
        max_rates[key] = rule.commission_rate

    for rule_data in rules_data:
        bank_id = str(rule_data.get('bank', ''))
        table_id = str(rule_data.get('table', ''))
        leader_rate = Decimal(str(rule_data.get('leader_commission_rate', 0)))
        seller_rate = Decimal(str(rule_data.get('seller_commission_rate', 0)))
        total = leader_rate + seller_rate
        key = (bank_id, table_id)

        if key in max_rates and total > max_rates[key]:
            table = Table.objects.filter(id=table_id).first()
            table_name = table.name_in_bank if table else table_id
            errors.append(
                f"Tabela '{table_name}': soma das taxas ({total}%) excede o limite da promotora ({max_rates[key]}%)"
            )

    return errors


def validate_promotora_rules(rules_data):
    """
    Valida que as taxas de CommissionRules (promotora) não excedem
    a commission_rate da Table original.
    """
    errors = []
    for rule_data in rules_data:
        table_id = rule_data.get('table')
        rate = Decimal(str(rule_data.get('commission_rate', 0)))

        table = Table.objects.filter(id=table_id).first()
        if table and table.commission_rate is not None and rate > table.commission_rate:
            errors.append(
                f"Tabela '{table.name_in_bank}': taxa ({rate}%) excede a taxa base da tabela ({table.commission_rate}%)"
            )

    return errors

class CommissionGroupListCreateView(BaseApiView):
    """
    API endpoint para listar e criar grupos de comissionamento.
    """
    serializer_class = CommissionGroupSerializer
    model = CommissionGroup
    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            permission_classes = [IsAdminOrGerenteOrLider]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get(self, request, format=None):
        """
        Lista os grupos de comissionamento.
        """
        user = request.user

        if user.role == User.ADMIN:
            groups = CommissionGroup.objects.all()
        elif user.role == User.GERENTE:
            from django.db.models import Q
            groups = CommissionGroup.objects.filter(
                Q(company=user.company, by_leader=False) | Q(company__isnull=True)
            )
        elif user.role == User.EMPRESA_ADMIN:
            # Corban vê apenas grupos da sua própria empresa (criados por ele ou pelo gerente)
            # Grupos da promotora (company=None) não são exibidos, mesmo que o corban seja membro
            groups = CommissionGroup.objects.filter(company=user.company)
        elif user.role == User.LIDER:
            groups = CommissionGroup.objects.filter(company=user.company, by_leader=True, leader=user)
        else:
            # Vendedor: only groups they belong to
            groups = CommissionGroup.objects.filter(sellers=user)

        # Filtrar por status ativo se solicitado
        if request.GET.get('active') == 'true':
            groups = groups.filter(is_active=True)
        
        serializer = CommissionGroupSerializer(groups, many=True)
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='list_commission_groups',
            message=f'Usuário listou {groups.count()} grupos de comissionamento'
        )
        
        return Response(serializer.data)
    
    def post(self, request, format=None):
        """
        Cria um novo grupo de comissionamento. 
        Permite ao gerente criar um grupo de comissionamento para a empresa que ele está vinculado. 
        Permite ao admin criar um grupo de comissionamento para uma empresa específica.
        """
        role = request.user.role
        
        if role not in [User.GERENTE, User.ADMIN, User.EMPRESA_ADMIN, User.LIDER]:
            return Response(
                {"error": "Usuário não tem permissão para criar grupo de comissionamento"},
                status=status.HTTP_403_FORBIDDEN
            )
        rules_data = request.data.pop('commission_rules', None)

        # ADMIN pode criar grupo da promotora (company=null) ou grupo para corban (company=X)
        # Demais roles sempre usam a própria empresa
        if role == User.ADMIN:
            company_id = request.data.get('company')
            if company_id:
                from core.models import Company as CompanyModel
                company_obj = CompanyModel.objects.filter(id=company_id).first()
                if not company_obj:
                    return Response(
                        {"error": "Empresa não encontrada"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                company_obj = None  # grupo da promotora (sem empresa vinculada)
        else:
            company_obj = request.user.company
            if not company_obj:
                return Response(
                    {"error": "Empresa não informada"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.data['company'] = company_obj.id

        if role == User.LIDER:
            request.data['leader'] = request.user.id
            request.data['by_leader'] = True

        # Validate cascade limits only for company-specific groups
        if rules_data and company_obj:
            errors = validate_company_rules(rules_data, company_obj)
            if errors:
                return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        serializer = CommissionGroupSerializer(data=request.data)
        
        if serializer.is_valid():
            commission_group = serializer.save()
            rules = []
            if rules_data:
                for rule in rules_data:
                    rule_serializer = CommissionRulesByUserSerializer(data=rule)
                    if rule_serializer.is_valid():
                        rules.append(rule_serializer.save())
                    else:
                        return Response(rule_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            commission_group.commission_rules.set(rules)
            # Registra a auditoria usando o método da classe base
            self.audit_create(
                request=request,
                instance=commission_group,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='create_comission_group',
                message=f'Usuário criou um novo grupo de comissionamento: {commission_group.name}',
                data={'comission_group_id': commission_group.id}
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommissionGroupDetailView(BaseApiView):
    """
    API endpoint para recuperar, atualizar e excluir um grupo de comissionamento específico.
    """
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            permission_classes = [IsAdminOrGerenteOrLider]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_object(self, pk):
        commission_group = get_object_or_404(CommissionGroup, pk=pk)
        user = self.request.user

        if user.role == User.ADMIN:
            return commission_group
        # Corban (empresa_admin) só acessa grupos da sua própria empresa
        if user.role == User.EMPRESA_ADMIN:
            if commission_group.company is None or commission_group.company != user.company:
                self.permission_denied(self.request)
            return commission_group
        # Grupos da promotora (sem empresa vinculada): acessíveis a gerentes e líderes
        if commission_group.company is not None:
            if not user.company or user.company != commission_group.company:
                self.permission_denied(self.request)
            # Lider: must own the group
            if user.role == User.LIDER and commission_group.leader != user:
                self.permission_denied(self.request)
        return commission_group
    
    def get(self, request, pk, format=None):
        """
        Recupera os detalhes de um grupo de comissionamento específico.
        """
        commission_group = self.get_object(pk)
        serializer = CommissionGroupSerializer(commission_group)
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='view_comission_group',
            message=f'Usuário visualizou os detalhes do grupo de comissionamento: {commission_group.name}',
            data={'comission_group_id': commission_group.id}
        )
        
        return Response(serializer.data)
    
    def put(self, request, pk, format=None):
        """
        Atualiza um grupo de comissionamento específico.
        """
        commission_group = self.get_object(pk)
        
        # Captura os dados antes da atualização
        old_data = CommissionGroupSerializer(commission_group).data
        
        serializer = CommissionGroupSerializer(commission_group, data=request.data)
        if serializer.is_valid():
            updated_commission_group = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,
                instance=updated_commission_group,
                data_before=old_data,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='update_comission_group',
                message=f'Usuário atualizou o grupo de comissionamento: {updated_commission_group.name}',
                data={'comission_group_id': updated_commission_group.id}
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk, format=None):
        """ 
        Atualiza parcialmente um grupo de comissionamento específico.
        """
        commission_group = self.get_object(pk)
        rules_data = request.data.pop('commission_rules', None)
        promotora_rules_data = request.data.pop('promotora_rules', None)

        # Validate cascade limits only for corban groups (company is set)
        if rules_data and commission_group.company:
            errors = validate_company_rules(rules_data, commission_group.company)
            if errors:
                return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        # Captura os dados antes da atualização
        old_data = CommissionGroupSerializer(commission_group).data
        
        serializer = CommissionGroupSerializer(commission_group, data=request.data, partial=True)
        if serializer.is_valid():
            updated_commission_group = serializer.save()

            # Corban rules (seller+leader split)
            if rules_data is not None:
                rules = []
                for rule in rules_data:
                    rule_serializer = CommissionRulesByUserSerializer(data=rule)
                    if rule_serializer.is_valid():
                        rules.append(rule_serializer.save())
                    else:
                        return Response(rule_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                updated_commission_group.commission_rules.set(rules)

            # Promotora rules (single rate → company)
            if promotora_rules_data is not None:
                p_rules = []
                for rule in promotora_rules_data:
                    rule_serializer = CommissionRulesSerializer(data=rule)
                    if rule_serializer.is_valid():
                        p_rules.append(rule_serializer.save())
                    else:
                        return Response(rule_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                updated_commission_group.promotora_rules.set(p_rules)

            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,
                instance=updated_commission_group,
                data_before=old_data,
                data_after=serializer.data
            )   
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='partial_update_comission_group',
                message=f'Usuário atualizou parcialmente o grupo de comissionamento: {updated_commission_group.name}',
                data={'comission_group_id': updated_commission_group.id, 'fields_updated': list(request.data.keys())}
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk, format=None):
        """
        Exclui um grupo de comissionamento específico.
        """
        commission_group = self.get_object(pk)
        
        # Captura os dados antes da exclusão
        old_data = CommissionGroupSerializer(commission_group).data
        
        # Registra a auditoria usando o método da classe base
        self.audit_delete(
            request=request,
            instance=commission_group,
            data_before=old_data
        )
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='delete_comission_group',
            message=f'Usuário excluiu o grupo de comissionamento: {commission_group.name}',
            data={'comission_group_id': commission_group.id}
        )
        
        commission_group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT) 

class CommissionGroupByCompanyListCreateView(BaseApiView):
    """
    API endpoint para listar e criar grupos de comissionamento por empresa.
    """
    serializer_class = CommissionGroupByCompanySerializer
    model = CommissionGroupByCompany

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            permission_classes = [IsAdmin]
        else:
            permission_classes = [IsAdminOrGerente]
        return [permission() for permission in permission_classes]

    def get(self, request, pk=None, format=None):
        """
        Lista os grupos de comissionamento por empresa ou retorna um específico.
        """
        if pk:
            commission_group = get_object_or_404(self.model, id=pk)
            serializer = self.serializer_class(commission_group)
            return Response(serializer.data)
        if request.user.role == User.ADMIN:
            qs = self.model.objects.all()
        else:
            # Gerente: only groups that include their company
            qs = self.model.objects.filter(companies=request.user.company)
        serializer = self.serializer_class(qs, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        """
        Cria um novo grupo de comissionamento por empresa.
        """
        data:dict = request.data.copy()
        commission_rules = data.pop('commission_rules', None)
        rules = []
        if commission_rules:
            # Validate against table base rates
            errors = validate_promotora_rules(commission_rules)
            if errors:
                return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
            for rule in commission_rules:
                if rule.is_valid():
                    rules.append(rule.save())
                else:
                    return Response(rule.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(data=data)
        if serializer.is_valid():
            commission_group = serializer.save()
            if rules:
                commission_group.comission_rules.set(rules)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk, format=None):
        """
        Atualiza parcialmente um grupo de comissionamento por empresa.
        """
        commission_group = get_object_or_404(self.model, id=pk)
        data: dict = request.data.copy()
        commission_rules = data.pop('commission_rules', None)

        serializer = self.serializer_class(commission_group, data=data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_group: CommissionGroupByCompany = serializer.save()

        if commission_rules is not None:
            # Validate against table base rates
            errors = validate_promotora_rules(commission_rules)
            if errors:
                return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

            rules = []
            for rule in commission_rules:
                rule_serializer = CommissionRulesSerializer(data=rule)
                if rule_serializer.is_valid():
                    rules.append(rule_serializer.save())
                else:
                    return Response(rule_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            updated_group.comission_rules.set(rules)

        return Response(self.serializer_class(updated_group).data)

    def delete(self, request, pk, format=None):
        """
        Exclui um grupo de comissionamento por empresa (soft delete).
        """
        comission_group = get_object_or_404(self.model, id=pk)
        comission_group.is_active = False
        comission_group.save()
        return Response(status=status.HTTP_204_NO_CONTENT)



class CommissionGroupByCompanyFormFieldsView(BaseApiView):
    """
    API endpoint para listar e criar grupos de comissionamento por empresa.
    """
    serializer_class = CommissionGroupByCompanySerializer
    model = CommissionGroupByCompany
    permission_classes = [IsAdmin]
    
    def get(self, request, format=None):
        """
        Lista os grupos de comissionamento por empresa.
        """
        serializer = self.serializer_class(self.model.objects.all(), many=True)
        return Response(serializer.data)
    
    def post(self, request, format=None):
        """
        Cria um novo grupo de comissionamento por empresa.
        """
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk, format=None):
        """
        Atualiza parcialmente um grupo de comissionamento por empresa específico.
        """
        comission_group = get_object_or_404(self.model, id=pk)
        serializer = self.serializer_class(comission_group, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    def delete(self, request, pk, format=None):
        """
        Exclui um grupo de comissionamento por empresa específico.
        """
        comission_group = get_object_or_404(self.model, id=pk)
        comission_group.is_active = False
        comission_group.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CommissionGroupByCompanyManageView(BaseApiView):
    """
    API endpoint para adicionar ou remover empresas de um grupo de comissionamento por empresa.
    """
    serializer_class = CommissionGroupByCompanySerializer
    model = CommissionGroupByCompany

    def get_permissions(self):
        permission_classes = [IsAdmin]
        return [permission() for permission in permission_classes]
    
    def put(self, request, pk, format=None):
        """
        Adiciona empresas a um grupo de comissionamento por empresa.
        Remove as empresas de seus grupos anteriores antes de adicioná-las ao novo grupo.
        """
        companies = request.data.get('companies')
        
        # Remove as empresas de seus grupos atuais
        old_commission_groups = self.model.objects.filter(companies__id__in=companies)
        for commission_group in old_commission_groups:
            old_comp = commission_group.companies.filter(id__in=companies).first()
            if old_comp:
                commission_group.companies.remove(old_comp)
                commission_group.save()
        new_comp = Company.objects.filter(id__in=companies)
        if new_comp.count() > 0:
            # Adiciona as empresas ao novo grupo
            new_commission_group = get_object_or_404(self.model, id=pk)
            new_commission_group.companies.set(new_comp)
            new_commission_group.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class CommissionGroupByUserManageView(BaseApiView):
    """
    API endpoint para adicionar ou remover usuários de um grupo de comissionamento por empresa.
    """
    serializer_class = CommissionGroupSerializer
    model = CommissionGroup

    def get_permissions(self):
        permission_classes = [IsAdminOrGerenteOrLider]
        return [permission() for permission in permission_classes]

    def put(self, request, pk, format=None):
        """
        Adiciona regras de comissionamento por usuário a um grupo de comissionamento por empresa.
        """
        users = request.data.get('user_ids')
        commission_group = get_object_or_404(self.model, id=pk)
        users = User.objects.filter(id__in=users)
        commission_group.sellers.clear()
        commission_group.leaders.clear()
        for user in users:
            if request.user.role in [User.ADMIN, User.EMPRESA_ADMIN, User.GERENTE]:
                if user.role == User.VENDEDOR:
                    commission_group.sellers.add(user)
                #Adiciona o lider e os vendedores associados a ele
                elif user.role == User.LIDER:
                    commission_group.leaders.add(user)
                    sellers = User.objects.filter(leader=user).exclude(id__in=[u.id for u in users])
                    if sellers.count() > 0:
                        commission_group.sellers.set(sellers)
                # Empresa admin (corban) é adicionado como seller em grupos da promotora
                elif user.role == User.EMPRESA_ADMIN:
                    commission_group.sellers.add(user)
            elif request.user.role == User.LIDER:
                if user.role == User.VENDEDOR:
                    commission_group.sellers.add(user)
                    #Remove o vendedor de seus grupos anteriores
                    old_groups = CommissionGroup.objects.filter(sellers=user).exclude(id=pk)
                    for old_group in old_groups:
                        old_group.sellers.remove(user)
                        old_group.save()
                else:
                    return Response(
                        {"error": "Usuário não tem permissão para adicionar líderes a um grupo de comissionamento"},
                        status=status.HTTP_403_FORBIDDEN
                    )
        commission_group.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CommissionGroupMaxRatesView(BaseApiView):
    """
    Retorna as taxas máximas permitidas para rules de um CommissionGroup (empresa).
    Busca as rates do CommissionGroupByCompany que contém a empresa do usuário.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        company = user.company
        if not company:
            return Response({"rates": []})

        company_group = CommissionGroupByCompany.objects.filter(
            companies=company, is_active=True
        ).first()

        if not company_group:
            return Response({"rates": []})

        rates = []
        for rule in company_group.comission_rules.select_related('bank', 'table').all():
            rates.append({
                "bank": str(rule.bank_id) if rule.bank_id else None,
                "bank_name": rule.bank.name if rule.bank else None,
                "table": str(rule.table_id) if rule.table_id else None,
                "table_name": rule.table.name_in_bank if rule.table else None,
                "max_rate": float(rule.commission_rate),
            })

        return Response({"rates": rates})


class CommissionGroupByCompanyMaxRatesView(BaseApiView):
    """
    Retorna as taxas máximas permitidas para rules de um CommissionGroupByCompany (promotora).
    As taxas máximas são as commission_rate das Tables.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        tables = Table.objects.select_related('bank', 'agreement').filter(
            is_active=True, commission_rate__isnull=False
        )

        rates = []
        for table in tables:
            rates.append({
                "bank": str(table.bank_id),
                "bank_name": table.bank.name,
                "table": str(table.id),
                "table_name": table.name_in_bank,
                "max_rate": float(table.commission_rate),
            })

        return Response({"rates": rates})