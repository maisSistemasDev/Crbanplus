from rest_framework.response import Response
from rest_framework import status, permissions
import logging
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
import csv
import io
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from .models import Bank, Agreement, Table, TableHistory, CommissionRange, normalize_name
from .serializers import BankSerializer, AgreementSerializer, TableSerializer
from core.permissions import IsGerente, IsAdmin, IsLider, IsAdminOrGerente
from core.models import User
from core.base_views import BaseApiView
from payments.models import CommissionGroupByCompany, CommissionGroup, CommissionRulesByUser, CommissionRules

logger = logging.getLogger(__name__)

# Novas views para retornar os campos de formulário
class BankFormFieldsView(BaseApiView):
    """
    API endpoint para obter os campos de formulário para o modelo Bank.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """
        Retorna os campos necessários para criar um formulário de banco.
        """
        serializer = BankSerializer()
        form_fields = serializer.form_fields()
        
        self.log_info(
            request=request,
            action='get_bank_form_fields',
            message=f'Usuário obteve campos de formulário para banco'
        )
        
        return Response(form_fields)


class AgreementFormFieldsView(BaseApiView):
    """
    API endpoint para obter os campos de formulário para o modelo Agreement.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """
        Retorna os campos necessários para criar um formulário de convênio.
        """
        serializer = AgreementSerializer()
        form_fields = serializer.form_fields()
        
        self.log_info(
            request=request,
            action='get_agreement_form_fields',
            message=f'Usuário obteve campos de formulário para convênio'
        )
        
        return Response(form_fields)


class TableFormFieldsView(BaseApiView):
    """
    API endpoint para obter os campos de formulário para o modelo Table.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        """
        Retorna os campos necessários para criar um formulário de tabela.
        """
        serializer = TableSerializer()
        form_fields = serializer.form_fields()
        
        self.log_info(
            request=request,
            action='get_table_form_fields',
            message=f'Usuário obteve campos de formulário para tabela'
        )
        
        return Response(form_fields)





class BankListCreateView(BaseApiView):
    """
    API endpoint para listar e criar bancos.
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            permission_classes = [IsAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get(self, request, format=None):
        """
        Lista os bancos.
        """
        banks = Bank.objects.all()
        serializer = BankSerializer(banks, many=True)

        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='list_banks',
            message=f'Usuário listou {banks.count()} bancos'
        )

        return Response(serializer.data)

    def post(self, request, format=None):
        """
        Cria um novo banco.
        """
        serializer = BankSerializer(data=request.data)
        if serializer.is_valid():
            bank = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_create(
                request=request,
                instance=bank,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='create_bank',
                message=f'Usuário criou um novo banco: {bank.name}',
                data={'bank_id': str(bank.id)}
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BankDetailView(BaseApiView):
    """
    API endpoint para recuperar, atualizar e excluir um banco específico.
    """
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            permission_classes = [IsAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_object(self, pk):
        return get_object_or_404(Bank, pk=pk)
    
    def get(self, request, pk, format=None):
        """
        Recupera um banco específico.
        """
        bank = self.get_object(pk)
        serializer = BankSerializer(bank)
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='retrieve_bank',
            message=f'Usuário recuperou detalhes do banco: {bank.name}',
            data={'bank_id': str(bank.id)}
        )
        
        return Response(serializer.data)
    
    def put(self, request, pk, format=None):
        """
        Atualiza um banco específico.
        """
        bank = self.get_object(pk)
        
        # Captura os dados antes da atualização
        old_data = BankSerializer(bank).data
        
        serializer = BankSerializer(bank, data=request.data)
        if serializer.is_valid():
            bank = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,
                instance=bank,
                data_before=old_data,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='update_bank',
                message=f'Usuário atualizou o banco: {bank.name}',
                data={'bank_id': str(bank.id)}
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk, format=None):
        """
        Atualiza parcialmente um banco específico.
        """
        bank = self.get_object(pk)
        
        # Captura os dados antes da atualização
        old_data = BankSerializer(bank).data
        
        serializer = BankSerializer(bank, data=request.data, partial=True)
        if serializer.is_valid():
            bank = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,
                instance=bank,
                data_before=old_data,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='partial_update_bank',
                message=f'Usuário atualizou parcialmente o banco: {bank.name}',
                data={'bank_id': str(bank.id)}
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk, format=None):
        """
        Exclui um banco específico.
        """
        bank = self.get_object(pk)
        
        # Captura os dados antes da exclusão
        data_before = BankSerializer(bank).data
        
        bank_name = bank.name
        bank_id = str(bank.id)
        
        # Registra a auditoria usando o método da classe base
        self.audit_delete(
            request=request,
            instance=bank,
            data_before=data_before
        )
        
        bank.delete()
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='delete_bank',
            message=f'Usuário excluiu o banco: {bank_name}',
            data={'bank_id': bank_id}
        )
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class AgreementListCreateView(BaseApiView):
    """
    API endpoint para listar e criar convênios.
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            permission_classes = [IsAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get(self, request, format=None):
        """
        Lista os convênios.
        """
        agreements = Agreement.objects.all()
        bank_id = request.query_params.get('bank')
        if bank_id:
            # Só convênios que realmente têm tabela naquele banco.
            agreements = agreements.filter(tables__bank_id=bank_id).distinct()
        serializer = AgreementSerializer(agreements, many=True)
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='list_agreements',
            message=f'Usuário listou {agreements.count()} convênios'
        )
        
        return Response(serializer.data)
    
    def post(self, request, format=None):
        """
        Cria um novo convênio.
        """
        serializer = AgreementSerializer(data=request.data)
        if serializer.is_valid():
            agreement = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_create(
                request=request,
                instance=agreement,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='create_agreement',
                message=f'Usuário criou um novo convênio: {agreement.name}',
                data={'agreement_id': str(agreement.id)}
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AgreementDetailView(BaseApiView):
    """
    API endpoint para recuperar, atualizar e excluir um convênio específico.
    """
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            permission_classes = [IsAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_object(self, pk):
        return get_object_or_404(Agreement, pk=pk)
    
    def get(self, request, pk, format=None):
        """
        Recupera um convênio específico.
        """
        agreement = self.get_object(pk)
        serializer = AgreementSerializer(agreement)
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='retrieve_agreement',
            message=f'Usuário recuperou detalhes do convênio: {agreement.name}',
            data={'agreement_id': str(agreement.id)}
        )
        
        return Response(serializer.data)
    
    def put(self, request, pk, format=None):
        """
        Atualiza um convênio específico.
        """
        agreement = self.get_object(pk)
        
        # Captura os dados antes da atualização
        old_data = AgreementSerializer(agreement).data
        
        serializer = AgreementSerializer(agreement, data=request.data)
        if serializer.is_valid():
            agreement = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,
                instance=agreement,
                data_before=old_data,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='update_agreement',
                message=f'Usuário atualizou o convênio: {agreement.name}',
                data={'agreement_id': str(agreement.id)}
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk, format=None):
        """
        Atualiza parcialmente um convênio específico.
        """
        agreement = self.get_object(pk)
        
        # Captura os dados antes da atualização
        old_data = AgreementSerializer(agreement).data
        
        serializer = AgreementSerializer(agreement, data=request.data, partial=True)
        if serializer.is_valid():
            agreement = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,
                instance=agreement,
                data_before=old_data,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='partial_update_agreement',
                message=f'Usuário atualizou parcialmente o convênio: {agreement.name}',
                data={'agreement_id': str(agreement.id)}
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk, format=None):
        """
        Exclui um convênio específico.
        """
        agreement = self.get_object(pk)
        
        # Captura os dados antes da exclusão
        data_before = AgreementSerializer(agreement).data
        
        agreement_name = agreement.name
        agreement_id = str(agreement.id)
        
        # Registra a auditoria usando o método da classe base
        self.audit_delete(
            request=request,
            instance=agreement,
            data_before=data_before
        )
        
        agreement.delete()
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='delete_agreement',
            message=f'Usuário excluiu o convênio: {agreement_name}',
            data={'agreement_id': agreement_id}
        )
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class BankAgreementListCreateView(BaseApiView):
    """
    API endpoint para listar e criar relações banco-convênio.
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            permission_classes = [IsAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get(self, request, format=None):
        """
        Lista as relações banco-convênio.
        """
        bank_agreements = Bank.objects.prefetch_related('agreements').all()
        res = map(
            lambda x: {
                'bank': BankSerializer(x).data,
                'agreements': AgreementSerializer([{'name':ag.name,'id':ag.id} for ag in x.agreements.all()], many=True).data
            },
            bank_agreements
        )
        serializer = list(res)
      
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='list_bank_agreements',
            message=f'Usuário listou {bank_agreements.count()} relações banco-convênio'
        )
        
        return Response(serializer.data)
    
    def post(self, request, format=None):
        """
        Cria uma nova relação banco-convênio.
        """
        serializer = BankSerializer(data=request.data)
        if serializer.is_valid():
            bank_agreement = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_create(
                request=request,
                instance=bank_agreement,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='create_bank_agreement',
                message=f'Usuário criou uma nova relação banco-convênio: {bank_agreement.bank.name} - {bank_agreement.agreement.name}',
                data={'bank_agreement_id': bank_agreement.id}
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TableListCreateView(BaseApiView):
    """
    API endpoint para listar e criar tabelas.
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            permission_classes = [IsAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get(self, request, format=None):
        """
        Lista as tabelas com filtros e paginação.
        """
        tables = Table.objects.select_related('bank', 'agreement').prefetch_related('commission_ranges').all()

        # Filtros por query params
        bank_id = request.query_params.get('bank')
        agreement_id = request.query_params.get('agreement')
        table_id = request.query_params.get('table')
        code_in_bank = request.query_params.get('code_in_bank')
        search = request.query_params.get('search')

        if bank_id:
            tables = tables.filter(bank_id=bank_id)
        if agreement_id:
            tables = tables.filter(agreement_id=agreement_id)
        if table_id:
            tables = tables.filter(id=table_id)
        if code_in_bank:
            tables = tables.filter(code_in_bank__icontains=code_in_bank)
        if search:
            tables = tables.filter(
                Q(name_in_bank__icontains=search) | Q(code_in_bank__icontains=search)
            )

        # Paginação
        try:
            page_size = min(max(int(request.query_params.get('page_size', 25)), 1), 500)
        except (TypeError, ValueError):
            page_size = 25
        page_number = request.query_params.get('page', 1)
        paginator = Paginator(tables, page_size)
        page_obj = paginator.get_page(page_number)

        if request.user.role == User.ADMIN:
            serializer = TableSerializer(page_obj.object_list, many=True)
            tables_data = list(serializer.data)

            self.log_info(
                request=request,
                action='list_tables',
                message=f'Usuário admin listou {paginator.count} tabelas'
            )
        else:
            # Buscar o grupo de comissionamento da empresa do usuário
            commission_group = CommissionGroupByCompany.objects.filter(
                companies__id=request.user.company.id
            ).first()

            table_commission_rates = {}
            if commission_group:
                for rule in commission_group.comission_rules.all():
                    logger.debug(rule)
                    if rule.table:
                        table_commission_rates[str(rule.table.id)] = rule.commission_rate

            serializer = TableSerializer(page_obj.object_list, many=True)
            tables_data = list(serializer.data)

            for table_data in tables_data:
                table_id = table_data['id']
                value = table_commission_rates.get(table_id)
                if value:
                    table_data['commission_rate'] = float(value)

            self.log_info(
                request=request,
                action='list_tables',
                message=f'Usuário listou tabelas com taxas de comissionamento do grupo'
            )

        return Response({
            'count': paginator.count,
            'next': None,
            'previous': None,
            'results': tables_data,
        })
    
    def post(self, request, format=None):
        """
        Cria uma nova tabela.
        """
        serializer = TableSerializer(data=request.data)
        if serializer.is_valid():
            table = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_create(
                request=request,
                instance=table,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='create_table',
                message=f'Usuário criou uma nova tabela: {table.name_in_bank}',
                data={'table_id': str(table.id)}
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _partner_rate_index(user):
    """Índice (table_id, range_id) -> (taxa, valor fixo) das regras do parceiro."""
    index = {}
    role = getattr(user, 'role', None)
    company_id = getattr(user, 'company_id', None)

    if role in (User.EMPRESA_ADMIN, User.GERENTE, User.ADMIN) and company_id:
        group = (
            CommissionGroupByCompany.objects.filter(companies__id=company_id, is_active=True)
            .prefetch_related('comission_rules')
            .first()
        )
        if group:
            for rule in group.comission_rules.all():
                key = (
                    str(rule.table_id) if rule.table_id else None,
                    str(rule.commission_range_id) if rule.commission_range_id else None,
                )
                index[key] = (rule.commission_rate, rule.fixed_value)

    if role == User.VENDEDOR:
        group = (
            CommissionGroup.objects.filter(sellers=user, is_active=True)
            .prefetch_related('commission_rules')
            .first()
        )
        if group:
            for rule in group.commission_rules.all():
                key = (
                    str(rule.table_id) if rule.table_id else None,
                    str(rule.commission_range_id) if rule.commission_range_id else None,
                )
                index[key] = (rule.seller_commission_rate, None)

    if role == User.LIDER:
        group = (
            CommissionGroup.objects.filter(Q(leaders=user) | Q(leader=user), is_active=True)
            .prefetch_related('commission_rules')
            .first()
        )
        if group:
            for rule in group.commission_rules.all():
                key = (
                    str(rule.table_id) if rule.table_id else None,
                    str(rule.commission_range_id) if rule.commission_range_id else None,
                )
                index[key] = (rule.leader_commission_rate, None)

    return index


def _lookup_partner_rate(index, table_id, range_id, fallback_rate, fallback_fixed):
    for key in ((table_id, range_id), (table_id, None)):
        if key in index:
            return index[key]
    return fallback_rate, fallback_fixed


class TableCatalogView(BaseApiView):
    """Catálogo de tabelas vigentes para o parceiro consultar comissões."""

    permission_classes = [permissions.IsAuthenticated]
    MAX_ROWS = 5000

    def get(self, request, format=None):
        today = timezone.now().date()
        tables = (
            Table.objects.filter(is_active=True, vigency_date__lte=today)
            .select_related('bank', 'agreement')
            .prefetch_related('commission_ranges')
            .order_by('bank__name', 'agreement__name', 'name_in_bank', 'vigency_date')
        )

        bank_id = request.query_params.get('bank')
        agreement_id = request.query_params.get('agreement')
        table_id = request.query_params.get('table')
        if bank_id:
            tables = tables.filter(bank_id=bank_id)
        if agreement_id:
            tables = tables.filter(agreement_id=agreement_id)
        if table_id:
            tables = tables.filter(id=table_id)

        sort = request.query_params.get('sort') or 'range'
        rate_index = _partner_rate_index(request.user)

        rows = []
        for table in tables:
            ranges = list(table.commission_ranges.all())
            if not ranges:
                rate, fixed = _lookup_partner_rate(
                    rate_index, str(table.id), None, table.commission_rate, None
                )
                rows.append(self._row(table, None, table.min_value, table.max_value, rate, fixed))
                continue

            emitted = False
            for item in ranges:
                empty_wildcard = (
                    float(item.min_value or 0) == 0
                    and float(item.max_value or 0) == 0
                    and item.fixed_value is None
                    and float(item.commission_rate or 0) == 0
                )
                if empty_wildcard:
                    continue
                rate, fixed = _lookup_partner_rate(
                    rate_index,
                    str(table.id),
                    str(item.id),
                    item.commission_rate,
                    item.fixed_value,
                )
                rows.append(self._row(table, str(item.id), item.min_value, item.max_value, rate, fixed))
                emitted = True
            if not emitted:
                rate, fixed = _lookup_partner_rate(
                    rate_index, str(table.id), None, table.commission_rate, None
                )
                rows.append(self._row(table, None, table.min_value, table.max_value, rate, fixed))

        if sort == 'commission':
            rows.sort(
                key=lambda row: (
                    -(float(row['commission_rate'] or 0)),
                    -(float(row['fixed_value'] or 0)),
                    row['bank_name'],
                    row['agreement_name'],
                    row['product'],
                    float(row['min_value'] or 0),
                )
            )
        else:
            rows.sort(
                key=lambda row: (
                    row['bank_name'],
                    row['agreement_name'],
                    row['product'],
                    float(row['min_value'] or 0),
                    float(row['max_value'] or 0),
                )
            )

        truncated = len(rows) > self.MAX_ROWS
        rows = rows[: self.MAX_ROWS]

        self.log_info(
            request=request,
            action='catalog_tables',
            message=f'Usuário consultou catálogo de {len(rows)} faixas de comissão',
        )
        return Response({'count': len(rows), 'truncated': truncated, 'results': rows})

    @staticmethod
    def _row(table, range_id, min_value, max_value, rate, fixed):
        return {
            'table_id': str(table.id),
            'range_id': range_id,
            'bank_id': str(table.bank_id),
            'bank_name': table.bank.name if table.bank_id else '',
            'agreement_id': str(table.agreement_id),
            'agreement_name': table.agreement.name if table.agreement_id else '',
            'product': table.name_in_bank or table.code_in_bank or '',
            'min_value': str(min_value if min_value is not None else 0),
            'max_value': str(max_value if max_value is not None else 0),
            'commission_rate': str(rate if rate is not None else 0),
            'fixed_value': str(fixed) if fixed is not None else None,
            'vigency_date': table.vigency_date.isoformat() if table.vigency_date else None,
            'format': 'Digital',
            'product_type': 'Novo',
        }


class TableDetailView(BaseApiView):
    """
    API endpoint para recuperar, atualizar e excluir uma tabela específica.
    """
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            permission_classes = [IsAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_object(self, pk):
        return get_object_or_404(Table, pk=pk)
    
    def get(self, request, pk, format=None):
        """
        Recupera uma tabela específica.
        """
        table = self.get_object(pk)
        serializer = TableSerializer(table)
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='retrieve_table',
            message=f'Usuário recuperou detalhes da tabela: {table.name_in_bank}',
            data={'table_id': str(table.id)}
        )
        
        return Response(serializer.data)
    
    def put(self, request, pk, format=None):
        """
        Atualiza uma tabela específica.
        """
        table = self.get_object(pk)
        
        # Captura os dados antes da atualização
        old_data = TableSerializer(table).data
        
        serializer = TableSerializer(table, data=request.data)
        if serializer.is_valid():
            table = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,
                instance=table,
                data_before=old_data,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='update_table',
                message=f'Usuário atualizou a tabela: {table.name_in_bank}',
                data={'table_id': str(table.id)}
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk, format=None):
        """
        Atualiza parcialmente uma tabela específica.
        """
        table = self.get_object(pk)
        
        # Captura os dados antes da atualização
        old_data = TableSerializer(table).data
        
        serializer = TableSerializer(table, data=request.data, partial=True)
        if serializer.is_valid():
            table = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,
                instance=table,
                data_before=old_data,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='partial_update_table',
                message=f'Usuário atualizou parcialmente a tabela: {table.name_in_bank}',
                data={'table_id': str(table.id)}
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk, format=None):
        """
        Exclui uma tabela específica.
        """
        table = self.get_object(pk)
        
        # Captura os dados antes da exclusão
        data_before = TableSerializer(table).data
        
        table_name = table.name_in_bank
        table_id = str(table.id)
        
        # Registra a auditoria usando o método da classe base
        self.audit_delete(
            request=request,
            instance=table,
            data_before=data_before
        )
        
        table.delete()
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='delete_table',
            message=f'Usuário excluiu a tabela: {table_name}',
            data={'table_id': table_id}
        )
        
        return Response(status=status.HTTP_204_NO_CONTENT) 



class TableCreateBatchView(BaseApiView):
    """
    API endpoint para criar ou atualizar tabelas a partir de um arquivo CSV.
    Múltiplas linhas com o mesmo (nome, convênio, data) são tratadas como faixas diferentes da mesma tabela.
    """
    permission_classes = [IsAdmin]

    def post(self, request, format=None):
        """
        Cria ou atualiza tabelas a partir de um arquivo CSV.
        Formato: nome_no_banco;convenio;valor_minimo;valor_maximo;taxa_de_comissionamento;data_de_vigencia
        Várias linhas com mesmo nome+convênio+data criam múltiplas faixas na mesma tabela.
        """
        from collections import OrderedDict

        file = request.FILES.get('file')
        bank_id = request.data.get('bank_id')
        # Sem bank_id: modo "Do Arquivo" - 1ª coluna do CSV é o nome do banco
        multi_bank = not bank_id

        if not file:
            return Response({"detail": "Arquivo não encontrado."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bank = None
            banks_by_norm_name = {}
            if multi_bank:
                banks_by_norm_name = {normalize_name(b.name): b for b in Bank.objects.all()}
            else:
                try:
                    bank = Bank.objects.get(id=bank_id)
                except ObjectDoesNotExist:
                    return Response({"detail": "Banco não encontrado."}, status=status.HTTP_404_NOT_FOUND)

            file_data = file.read().decode('utf-8')
            io_string = io.StringIO(file_data)
            reader = csv.reader(io_string, delimiter=';')

            errors = []
            line_number = 0
            table_groups = OrderedDict()
            offset = 1 if multi_bank else 0
            min_cols = 7 if multi_bank else 6

            # --- Passo 1: ler todas as linhas e agrupar por tabela (e banco, no modo "Do Arquivo") ---
            for row in reader:
                line_number += 1

                if line_number == 1 and row and any(
                    h in row[0].lower() for h in ['nome_no_banco', 'convenio', 'tabela', 'nome', 'banco']
                ):
                    continue

                if len(row) < min_cols:
                    errors.append(f"Linha {line_number}: Dados insuficientes (esperado {min_cols} campos, encontrado {len(row)})")
                    continue

                row_bank = bank
                if multi_bank:
                    bank_name_raw = row[0].strip()
                    row_bank = banks_by_norm_name.get(normalize_name(bank_name_raw))
                    if row_bank is None:
                        errors.append(f"Linha {line_number}: Banco '{bank_name_raw}' não encontrado")
                        continue

                table_name_norm = normalize_name(row[0 + offset].strip())
                agreement_name_norm = normalize_name(row[1 + offset].strip())

                if not table_name_norm or not agreement_name_norm:
                    errors.append(f"Linha {line_number}: Nome da tabela ou convênio vazio")
                    continue

                try:
                    min_value = float(row[2 + offset].strip().replace(',', '.')) if row[2 + offset].strip() else None
                    max_value = float(row[3 + offset].strip().replace(',', '.')) if row[3 + offset].strip() else None
                    commission_rate = float(row[4 + offset].strip().replace(',', '.')) if row[4 + offset].strip() else None
                    fixed_value = None
                    extra_idx = 6 + offset
                    if len(row) > extra_idx and row[extra_idx].strip():
                        fixed_value = float(row[extra_idx].strip().replace(',', '.'))
                    if commission_rate is not None and commission_rate > 100 and fixed_value is None:
                        fixed_value = commission_rate
                        commission_rate = 0
                except ValueError as e:
                    errors.append(f"Linha {line_number}: Valores numéricos inválidos - {str(e)}")
                    continue

                if min_value is None or max_value is None:
                    errors.append(f"Linha {line_number}: Valores numéricos obrigatórios (min, max)")
                    continue
                if commission_rate is None and fixed_value is None:
                    errors.append(f"Linha {line_number}: Informe taxa (%) ou valor fixo (R$)")
                    continue

                vigency_date = None
                if row[5 + offset].strip():
                    date_str = row[5 + offset].strip()
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                        try:
                            vigency_date = datetime.strptime(date_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    if vigency_date is None:
                        errors.append(f"Linha {line_number}: Formato de data inválido '{row[5 + offset]}'. Use YYYY-MM-DD, DD/MM/YYYY ou DD-MM-YYYY")
                        continue

                key = (str(row_bank.id), table_name_norm, agreement_name_norm, str(vigency_date))
                if key not in table_groups:
                    table_groups[key] = {
                        'bank': row_bank,
                        'table_name_norm': table_name_norm,
                        'agreement_name_norm': agreement_name_norm,
                        'vigency_date': vigency_date,
                        'ranges': [],
                        'line_start': line_number,
                    }
                table_groups[key]['ranges'].append({
                    'min_value': min_value,
                    'max_value': max_value,
                    'commission_rate': commission_rate if commission_rate is not None else 0,
                    'fixed_value': fixed_value,
                })

            # --- Passo 2: criar/atualizar cada tabela com suas faixas ---
            created_tables = []
            updated_tables = []

            # Normaliza convênios uma única vez por nome para evitar duplicatas
            # durante o processamento do arquivo.
            agreement_by_norm: dict[str, Agreement] = {}
            all_agreements = Agreement.objects.prefetch_related('banks')
            for agr in all_agreements:
                norm = normalize_name(agr.name)
                if norm and norm not in agreement_by_norm:
                    agreement_by_norm[norm] = agr

            for key, group in table_groups.items():
                bank = group['bank']
                try:
                    norm = group['agreement_name_norm']
                    agreement = agreement_by_norm.get(norm)

                    if not agreement:
                        agreement = Agreement.objects.create(name=norm)
                        agreement_by_norm[norm] = agreement

                    # Garante que o banco esteja relacionado ao convênio
                    if not agreement.banks.filter(pk=bank.pk).exists():
                        agreement.banks.add(bank)

                    existing_table = Table.objects.filter(
                        bank=bank,
                        agreement=agreement,
                        name_in_bank__iexact=group['table_name_norm'],
                    ).first()

                    if existing_table:
                        old_ranges = list(
                            existing_table.commission_ranges.values(
                                'min_value', 'max_value', 'commission_rate', 'fixed_value',
                            )
                        )

                        if group['vigency_date']:
                            existing_table.vigency_date = group['vigency_date']
                            existing_table.save()

                        existing_table.commission_ranges.all().delete()
                        for r in group['ranges']:
                            CommissionRange.objects.create(
                                table=existing_table,
                                min_value=r['min_value'],
                                max_value=r['max_value'],
                                commission_rate=r['commission_rate'],
                                fixed_value=r.get('fixed_value'),
                            )

                        TableHistory.objects.create(
                            table=existing_table,
                            action='CSV_UPDATE',
                            user=request.user if request.user.is_authenticated else None,
                            previous_values={'commission_ranges': [
                                {k: str(v) for k, v in r.items()} for r in old_ranges
                            ]},
                            new_values={'commission_ranges': [
                                {
                                    'min_value': str(r['min_value']),
                                    'max_value': str(r['max_value']),
                                    'commission_rate': str(r['commission_rate']),
                                    'fixed_value': str(r['fixed_value']) if r.get('fixed_value') is not None else None,
                                }
                                for r in group['ranges']
                            ]},
                            notes=f'Atualização via CSV - {len(group["ranges"])} faixa(s)',
                        )

                        updated_tables.append({
                            'name': existing_table.name_in_bank,
                            'bank': bank.name,
                            'agreement': agreement.name,
                            'ranges_count': len(group['ranges']),
                            'action': 'updated',
                        })
                        self.audit_update(
                            request=request, instance=existing_table,
                            data_before={'name': group['table_name_norm']},
                            data_after=TableSerializer(existing_table).data,
                        )

                    else:
                        new_table = Table.objects.create(
                            name_in_bank=group['table_name_norm'],
                            bank=bank,
                            agreement=agreement,
                            vigency_date=group['vigency_date'],
                        )
                        for r in group['ranges']:
                            CommissionRange.objects.create(
                                table=new_table,
                                min_value=r['min_value'],
                                max_value=r['max_value'],
                                commission_rate=r['commission_rate'],
                                fixed_value=r.get('fixed_value'),
                            )

                        TableHistory.objects.create(
                            table=new_table,
                            action='CSV_IMPORT',
                            user=request.user if request.user.is_authenticated else None,
                            new_values={'commission_ranges': [
                                {
                                    'min_value': str(r['min_value']),
                                    'max_value': str(r['max_value']),
                                    'commission_rate': str(r['commission_rate']),
                                    'fixed_value': str(r['fixed_value']) if r.get('fixed_value') is not None else None,
                                }
                                for r in group['ranges']
                            ]},
                            notes=f'Criação via CSV - {len(group["ranges"])} faixa(s)',
                        )

                        created_tables.append({
                            'name': new_table.name_in_bank,
                            'bank': bank.name,
                            'agreement': agreement.name,
                            'ranges_count': len(group['ranges']),
                            'action': 'created',
                        })
                        self.audit_create(
                            request=request, instance=new_table,
                            data_after=TableSerializer(new_table).data,
                        )

                except Exception as e:
                    logger.error(f"Erro ao processar tabela '{key}': {str(e)}")
                    errors.append(f"Tabela '{key[0]}' (linha {group['line_start']}): {str(e)}")

            response_data = {
                "created_count": len(created_tables),
                "updated_count": len(updated_tables),
                "created_tables": created_tables,
                "updated_tables": updated_tables,
                "errors_count": len(errors),
                "errors": errors,
            }

            if errors:
                if created_tables or updated_tables:
                    response_data["detail"] = (
                        f"{len(created_tables)} tabelas criadas, {len(updated_tables)} atualizadas e {len(errors)} erro(s)."
                    )
                    return Response(response_data, status=status.HTTP_207_MULTI_STATUS)
                else:
                    response_data["detail"] = "Nenhuma tabela foi criada/atualizada."
                    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
            else:
                response_data["detail"] = f"{len(created_tables)} tabelas criadas, {len(updated_tables)} atualizadas."
                self.log_info(
                    request=request, action='create_update_tables_batch',
                    message=response_data["detail"],
                    data={'created_count': len(created_tables), 'updated_count': len(updated_tables)},
                )
                return Response(response_data, status=status.HTTP_201_CREATED)

        except UnicodeDecodeError:
            return Response(
                {"detail": "Erro ao decodificar arquivo. Certifique-se de que está codificado em UTF-8."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Erro ao processar arquivo: {str(e)}")
            return Response(
                {"detail": f"Erro ao processar arquivo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get(self, request, format=None):
        """Retorna um arquivo CSV de exemplo com múltiplas faixas de comissionamento por tabela.

        Com ?multi_bank=1, inclui a coluna "banco" (1ª coluna) para importar tabelas
        de vários bancos de uma vez (opção "Do Arquivo").
        """
        multi_bank = request.query_params.get('multi_bank') in ('1', 'true', 'True')

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = 'exemplo_tabelas_multi_banco.csv' if multi_bank else 'exemplo_tabelas.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')

        header = ['nome_no_banco', 'convenio', 'valor_minimo', 'valor_maximo',
                  'taxa_de_comissionamento', 'data_de_vigencia', 'valor_fixo']
        rows = [
            ['INSS Proposta', 'INSS', '50', '1000', '25', '2026-01-01', ''],
            ['INSS Proposta', 'INSS', '1000.01', '5000', '23', '2026-01-01', ''],
            ['INSS Proposta', 'INSS', '5000.01', '10000', '20', '2026-01-01', ''],
            ['FGTS Tabela', 'FGTS', '500', '10000', '18', '2026-01-01', ''],
            ['FGTS FIXO', 'FGTS', '0', '0', '', '2026-01-01', '960'],
        ]

        if multi_bank:
            header = ['banco'] + header
            bank_names = ['Banco Exemplo A', 'Banco Exemplo A', 'Banco Exemplo A', 'Banco Exemplo B', 'Banco Exemplo B']
            rows = [[bank_name] + row for bank_name, row in zip(bank_names, rows)]

        writer.writerow(header)
        for row in rows:
            writer.writerow(row)
        return response


class TableExportCSVView(BaseApiView):
    """
    API endpoint para exportar tabelas de um banco para CSV.
    Útil para baixar, editar e fazer re-upload das tabelas.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, bank_id=None, format=None):
        """
        Exporta tabelas de um banco específico para CSV.
        Se bank_id não for fornecido, exporta todas as tabelas.
        """
        try:
            if bank_id:
                # Buscar banco
                try:
                    bank = Bank.objects.get(id=bank_id)
                    tables = Table.objects.filter(bank=bank).select_related('bank', 'agreement')
                    filename = f"tabelas_{bank.name.replace(' ', '_')}.csv"
                except ObjectDoesNotExist:
                    return Response({"detail": "Banco não encontrado."}, status=status.HTTP_404_NOT_FOUND)
            else:
                # Exportar todas as tabelas
                tables = Table.objects.all().select_related('bank', 'agreement')
                filename = "tabelas_todas.csv"
            
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Adicionar BOM para UTF-8
            response.write('\ufeff')
            
            writer = csv.writer(response, delimiter=';')
            
            # Cabeçalho
            writer.writerow([
                'nome_no_banco',
                'convenio',
                'valor_minimo',
                'valor_maximo',
                'taxa_de_comissionamento',
                'data_de_vigencia',
                'valor_fixo',
            ])
            
            # Dados: uma linha por faixa de comissionamento
            for table in tables.prefetch_related('commission_ranges'):
                ranges = table.commission_ranges.all()
                if ranges.exists():
                    for cr in ranges:
                        writer.writerow([
                            table.name_in_bank or '',
                            table.agreement.name or '',
                            str(cr.min_value),
                            str(cr.max_value),
                            str(cr.commission_rate) if cr.commission_rate is not None else '',
                            table.vigency_date.strftime('%Y-%m-%d') if table.vigency_date else '',
                            str(cr.fixed_value) if cr.fixed_value is not None else '',
                        ])
                else:
                    # Tabela sem faixas: exporta linha vazia para não perdê-la
                    writer.writerow([
                        table.name_in_bank or '',
                        table.agreement.name or '',
                        '', '', '',
                        table.vigency_date.strftime('%Y-%m-%d') if table.vigency_date else '',
                        '',
                    ])
            
            # Registrar ação
            self.log_info(
                request=request,
                action='export_tables_csv',
                message=f'Usuário exportou {tables.count()} tabelas para CSV' + (f' do banco {bank.name}' if bank_id else ''),
                data={'tables_count': tables.count(), 'bank_id': bank_id}
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Erro ao exportar CSV: {str(e)}")
            return Response(
                {"detail": f"Erro ao exportar CSV: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TablesByBankView(BaseApiView):
    """
    API endpoint para listar tabelas filtradas por banco.
    Útil para interface de seleção de tabelas ao criar grupos de comissionamento.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, bank_id, format=None):
        """
        Lista tabelas de um banco específico com suas comissões.
        """
        try:
            # Buscar banco
            try:
                bank = Bank.objects.get(id=bank_id)
            except ObjectDoesNotExist:
                return Response({"detail": "Banco não encontrado."}, status=status.HTTP_404_NOT_FOUND)
            
            # Buscar tabelas do banco
            tables = Table.objects.filter(
                bank=bank,
                is_active=True
            ).select_related('bank', 'agreement').order_by('agreement__name', 'name_in_bank')
            
            serializer = TableSerializer(tables, many=True)
            
            # Registrar ação
            self.log_info(
                request=request,
                action='list_tables_by_bank',
                message=f'Usuário listou {tables.count()} tabelas do banco {bank.name}',
                data={'bank_id': bank_id, 'tables_count': tables.count()}
            )
            
            return Response({
                'bank': BankSerializer(bank).data,
                'tables': serializer.data,
                'count': tables.count()
            })
            
        except Exception as e:
            logger.error(f"Erro ao listar tabelas por banco: {str(e)}")
            return Response(
                {"detail": f"Erro ao listar tabelas: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TableHistoryView(BaseApiView):
    """
    API endpoint para visualizar o histórico de alterações de uma tabela.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, table_id, format=None):
        """
        Retorna o histórico de alterações de uma tabela específica.
        """
        try:
            # Buscar tabela
            try:
                table = Table.objects.get(id=table_id)
            except ObjectDoesNotExist:
                return Response({"detail": "Tabela não encontrada."}, status=status.HTTP_404_NOT_FOUND)
            
            # Buscar histórico
            history = TableHistory.objects.filter(table=table).select_related('user').order_by('-created_at')
            
            history_data = []
            for entry in history:
                history_data.append({
                    'id': str(entry.id),
                    'action': entry.action,
                    'user': {
                        'id': str(entry.user.id) if entry.user else None,
                        'name': entry.user.get_full_name() if entry.user else 'Sistema'
                    },
                    'field_changes': entry.field_changes,
                    'previous_values': entry.previous_values,
                    'new_values': entry.new_values,
                    'notes': entry.notes,
                    'created_at': entry.created_at.isoformat()
                })
            
            # Registrar ação
            self.log_info(
                request=request,
                action='view_table_history',
                message=f'Usuário visualizou histórico da tabela {table.name_in_bank}',
                data={'table_id': table_id}
            )
            
            return Response({
                'table': TableSerializer(table).data,
                'history': history_data,
                'count': len(history_data)
            })
            
        except Exception as e:
            logger.error(f"Erro ao buscar histórico: {str(e)}")
            return Response(
                {"detail": f"Erro ao buscar histórico: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TableBulkDeleteView(BaseApiView):
    """
    API endpoint para exclusão em massa de tabelas.
    Recebe uma lista de IDs via body: {"ids": ["uuid1", "uuid2", ...]}
    """
    permission_classes = [IsAdmin]

    def delete(self, request, format=None):
        ids = request.data.get('ids', [])
        if not ids or not isinstance(ids, list):
            return Response({"detail": "Forneça uma lista de IDs em 'ids'."}, status=status.HTTP_400_BAD_REQUEST)

        tables = Table.objects.filter(id__in=ids)
        deleted_count = tables.count()
        tables.delete()

        self.log_info(
            request=request,
            action='bulk_delete_tables',
            message=f'Usuário excluiu {deleted_count} tabela(s) em massa.',
            data={'ids': ids, 'deleted_count': deleted_count}
        )

        return Response({"deleted": deleted_count}, status=status.HTTP_200_OK)


class AgreementBulkDeleteView(BaseApiView):
    """
    API endpoint para exclusão em massa de convênios.
    Recebe uma lista de IDs via body: {"ids": ["uuid1", "uuid2", ...]}
    """
    permission_classes = [IsAdmin]

    def delete(self, request, format=None):
        ids = request.data.get('ids', [])
        if not ids or not isinstance(ids, list):
            return Response({"detail": "Forneça uma lista de IDs em 'ids'."}, status=status.HTTP_400_BAD_REQUEST)

        agreements = Agreement.objects.filter(id__in=ids)
        deleted_count = agreements.count()
        agreements.delete()

        self.log_info(
            request=request,
            action='bulk_delete_agreements',
            message=f'Usuário excluiu {deleted_count} convênio(s) em massa.',
            data={'ids': ids, 'deleted_count': deleted_count}
        )

        return Response({"deleted": deleted_count}, status=status.HTTP_200_OK)