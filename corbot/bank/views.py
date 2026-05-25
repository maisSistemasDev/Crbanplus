from rest_framework.response import Response
from rest_framework import status, permissions
import logging
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
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
        Lista as tabelas.
        """
        tables = Table.objects.all()

        if request.user.role == User.ADMIN:
            serializer = TableSerializer(tables, many=True)
            
            self.log_info(
                request=request,
                action='list_tables',
                message=f'Usuário admin listou {tables.count()} tabelas'
            )
            
            return Response(serializer.data)
        else:
            # Buscar o grupo de comissionamento da empresa do usuário
            commission_group = CommissionGroupByCompany.objects.filter(
                companies__id=request.user.company.id
            ).first()
            
            if not commission_group:
                # Se não há grupo de comissionamento, retorna todas as tabelas sem taxa específica
                serializer = TableSerializer(tables, many=True)
                return Response(serializer.data)
            
            # Buscar as regras de comissão do grupo
            commission_rules = commission_group.comission_rules.all()
            
            # Criar um dicionário para mapear table_id -> commission_rate
            table_commission_rates = {}
            for rule in commission_rules:
                logger.debug(rule)
                if rule.table:
                    logger.debug(rule.table)
                    table_commission_rates[str(rule.table.id)] = rule.commission_rate
                    logger.debug(table_commission_rates)
            # Serializar todas as tabelas
            serializer = TableSerializer(tables, many=True)
            tables_data = serializer.data
            
            # Adicionar ou atualizar o commission_rate baseado nas regras do grupo
            for table_data in tables_data:
                table_id = table_data['id']
                logger.debug(table_id)
                value = table_commission_rates.get(table_id)
                logger.debug(value)
                if value:
                    table_data['commission_rate'] = float(value)
                # Se não há regra específica, mantém o commission_rate original da tabela
            
            self.log_info(
                request=request,
                action='list_tables',
                message=f'Usuário listou {tables.count()} tabelas com taxas de comissionamento do grupo'
            )
            
            return Response(tables_data)
    
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

        if not file:
            return Response({"detail": "Arquivo não encontrado."}, status=status.HTTP_400_BAD_REQUEST)
        if not bank_id:
            return Response({"detail": "ID do banco não informado."}, status=status.HTTP_400_BAD_REQUEST)

        try:
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

            # --- Passo 1: ler todas as linhas e agrupar por tabela ---
            for row in reader:
                line_number += 1

                if line_number == 1 and row and any(
                    h in row[0].lower() for h in ['nome_no_banco', 'convenio', 'tabela', 'nome']
                ):
                    continue

                if len(row) < 6:
                    errors.append(f"Linha {line_number}: Dados insuficientes (esperado 6 campos, encontrado {len(row)})")
                    continue

                table_name_norm = normalize_name(row[0].strip())
                agreement_name_norm = normalize_name(row[1].strip())

                if not table_name_norm or not agreement_name_norm:
                    errors.append(f"Linha {line_number}: Nome da tabela ou convênio vazio")
                    continue

                try:
                    min_value = float(row[2].strip().replace(',', '.')) if row[2].strip() else None
                    max_value = float(row[3].strip().replace(',', '.')) if row[3].strip() else None
                    commission_rate = float(row[4].strip().replace(',', '.')) if row[4].strip() else None
                except ValueError as e:
                    errors.append(f"Linha {line_number}: Valores numéricos inválidos - {str(e)}")
                    continue

                if min_value is None or max_value is None or commission_rate is None:
                    errors.append(f"Linha {line_number}: Valores numéricos obrigatórios (min, max, taxa)")
                    continue

                vigency_date = None
                if row[5].strip():
                    date_str = row[5].strip()
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                        try:
                            vigency_date = datetime.strptime(date_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    if vigency_date is None:
                        errors.append(f"Linha {line_number}: Formato de data inválido '{row[5]}'. Use YYYY-MM-DD, DD/MM/YYYY ou DD-MM-YYYY")
                        continue

                key = (table_name_norm, agreement_name_norm, str(vigency_date))
                if key not in table_groups:
                    table_groups[key] = {
                        'table_name_norm': table_name_norm,
                        'agreement_name_norm': agreement_name_norm,
                        'vigency_date': vigency_date,
                        'ranges': [],
                        'line_start': line_number,
                    }
                table_groups[key]['ranges'].append({
                    'min_value': min_value,
                    'max_value': max_value,
                    'commission_rate': commission_rate,
                })

            # --- Passo 2: criar/atualizar cada tabela com suas faixas ---
            created_tables = []
            updated_tables = []

            for key, group in table_groups.items():
                try:
                    agreement = Agreement.objects.filter(
                        banks=bank
                    ).filter(
                        name__iexact=group['agreement_name_norm']
                    ).first()

                    if not agreement:
                        agreement = Agreement.objects.create(name=group['agreement_name_norm'])
                        agreement.banks.add(bank)

                    existing_table = Table.objects.filter(
                        bank=bank,
                        agreement=agreement,
                        name_in_bank__iexact=group['table_name_norm'],
                    ).first()

                    if existing_table:
                        old_ranges = list(
                            existing_table.commission_ranges.values('min_value', 'max_value', 'commission_rate')
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
                            )

                        TableHistory.objects.create(
                            table=existing_table,
                            action='CSV_UPDATE',
                            user=request.user if request.user.is_authenticated else None,
                            previous_values={'commission_ranges': [
                                {k: str(v) for k, v in r.items()} for r in old_ranges
                            ]},
                            new_values={'commission_ranges': [
                                {'min_value': str(r['min_value']), 'max_value': str(r['max_value']), 'commission_rate': str(r['commission_rate'])}
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
                            )

                        TableHistory.objects.create(
                            table=new_table,
                            action='CSV_IMPORT',
                            user=request.user if request.user.is_authenticated else None,
                            new_values={'commission_ranges': [
                                {'min_value': str(r['min_value']), 'max_value': str(r['max_value']), 'commission_rate': str(r['commission_rate'])}
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
        """Retorna um arquivo CSV de exemplo com múltiplas faixas de comissionamento por tabela"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="exemplo_tabelas.csv"'
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'nome_no_banco', 'convenio', 'valor_minimo', 'valor_maximo',
            'taxa_de_comissionamento', 'data_de_vigencia',
        ])
        # Exemplo: mesma tabela com 3 faixas
        writer.writerow(['INSS Proposta', 'INSS', '50', '1000', '25', '2026-01-01'])
        writer.writerow(['INSS Proposta', 'INSS', '1000.01', '5000', '23', '2026-01-01'])
        writer.writerow(['INSS Proposta', 'INSS', '5000.01', '10000', '20', '2026-01-01'])
        # Outra tabela com 1 faixa
        writer.writerow(['FGTS Tabela', 'FGTS', '500', '10000', '18', '2026-01-01'])
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
                'data_de_vigencia'
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
                            str(cr.commission_rate),
                            table.vigency_date.strftime('%Y-%m-%d') if table.vigency_date else '',
                        ])
                else:
                    # Tabela sem faixas: exporta linha vazia para não perdê-la
                    writer.writerow([
                        table.name_in_bank or '',
                        table.agreement.name or '',
                        '', '', '',
                        table.vigency_date.strftime('%Y-%m-%d') if table.vigency_date else '',
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