import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
import pandas as pd
import datetime
from django.http import FileResponse
import os
import csv
from django.http import HttpResponse
from rest_framework.pagination import PageNumberPagination
import json
import tempfile
from rest_framework import viewsets, views
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from datetime import datetime
import uuid
from .utils import read_file_columns, get_required_fields, get_model_fields, file_to_dict

from .models import Proposal, Layout, LayoutField, ProposalFile, ProposalBatch
from .serializers import *
from core.permissions import IsGerente, IsGerenteOrLider, IsAdmin
from core.services import AuditService, LogService
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Bank, Agreement, ProposalBatch, ErroredProposal, StatusPayment
from celery.result import AsyncResult
from core.base_views import BaseApiView
from bank.models import Table, Agreement, Bank
from bank_access.models import BankAccess
from payments.models import Payment, Commission
from .tasks import process_proposal_batch, process_proposal_batch_with_pipeline
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def normalize_value(value):
    value = value.lower()
    value = value.strip()
    return value

def match_object(model_name, value):
    """
    Função utilitária para corresponder objetos.
    """
    normalize_value_lower = normalize_value(value)
    
    if model_name == 'table':
        tables = Table.objects.all()
        for table in tables:
            alias_list = table.alias or []
            for alias in alias_list:
                if normalize_value(alias) == normalize_value_lower:
                    return table
        return None
        
    elif model_name == 'user':
        bank_accesses = BankAccess.objects.all()
        for bank_access in bank_accesses:
            alias_list = bank_access.alias or []
            for alias in alias_list:
                if normalize_value(alias) == normalize_value_lower:
                    return bank_access.user
        return None

    return None

class ProposalFieldsView(BaseApiView):
    """
    View para obter informações sobre os campos do modelo Proposal.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Retorna todos os campos do modelo Proposal e identifica quais são obrigatórios.
        """
        required_fields = get_required_fields()
        model_fields = get_model_fields()
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='get_proposal_fields',
            message='Usuário obteve informações dos campos do modelo Proposal'
        )
        
        return Response({
            'required_fields': required_fields,
            'model_fields': model_fields
        })

class ReadFileView(BaseApiView):
    """
    View para ler o arquivo de proposta e retornar os dados e o nome das colunas na ordem que aparecem no arquivo.
    """
    parser_classes = (MultiPartParser, FormParser)  
    permission_classes = [IsAdmin]
    
    def post(self, request):
        file = request.FILES.get('file')
        if file:
            proposal_file = ProposalFile.objects.create(
                file=file
            )
            columns_order = read_file_columns(proposal_file.file.path)
            
           # Obter todos os campos do modelo com suas propriedades
            model_fields = get_model_fields(exclude_fields=['id', 'created_at', 'uploaded_at', 'files', 'bank', 'updated_at', 'original_data','batch','company','hash'])
            
            return Response(status=status.HTTP_200_OK, data={
                'columns_order': columns_order,
                'model_fields': model_fields
            })
        return Response(status=status.HTTP_400_BAD_REQUEST)

class LayoutView(BaseApiView):
    """
    View para aplicar o layout no arquivo de proposta.
    """
    permission_classes = [IsAdmin]
    
    def post(self, request):
        bank = request.data.get('bank')
        name = request.data.get('name')
        bank = get_object_or_404(Bank, id=bank)
        if not bank:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': 'Banco não encontrado'})
        layout = Layout.objects.create(
            bank=bank,
            name=name,
        )
        
        mapping = request.data.get('mapping')
        for column, obj in mapping.items():
            # Suporta múltiplas colunas por campo (obj pode ser uma lista)
            if isinstance(obj, list):
                for mapping_item in obj:
                    layout_field = LayoutField.objects.create(
                        name=column,
                        index=mapping_item['index'],
                        header_name=mapping_item['name'],
                        data_type=mapping_item['data_type']
                    )
                    layout.map_fields.add(layout_field)
            else:
                # Backward compatibility: suporta formato antigo (objeto único)
                layout_field = LayoutField.objects.create(
                    name=column,
                    index=obj['index'],
                    header_name=obj['name'],
                    data_type=obj['data_type']
                )
                layout.map_fields.add(layout_field)
        layout.save()
        return Response(status=status.HTTP_200_OK, data={'layout': layout.id})
    
    def get(self, request):
        layouts = Layout.objects.all()
        return Response(status=status.HTTP_200_OK, data=LayoutSerializer(layouts, many=True).data)
    
    def delete(self, request, pk, format=None):
        layout = Layout.objects.get(id=pk)
        layout.delete()
        return Response(status=status.HTTP_200_OK)

    def put(self, request, pk):
        layout = Layout.objects.get(id=pk)
        layout.name = request.data.get('name')
        layout.file = request.data.get('file')
        layout.map_fields.clear()
        for column in request.data.get('columns_order'):
            layout_field = LayoutField.objects.create(
                name=column['name'],
                index=column['index'],
                header_name=column['header_name']
            )
            layout.map_fields.add(layout_field)
        layout.save()
        return Response(status=status.HTTP_200_OK)

class LayoutFormFieldsView(BaseApiView):
    """
    View para gerenciar os campos de layout.
    """
    permission_classes = [IsAdmin]
    
    def get(self, request):
        serializer = LayoutSerializer()
        fields = serializer.form_fields()
        return Response(fields)

class ProposalBatchView(BaseApiView):
    """
    View para processar um arquivo de proposta em lote.
    """
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAdmin]

    def post(self, request):
        file = request.data.get('file')
        layout_id = request.data.get('layout_id')
        if not file:
            return Response({'detail': 'Arquivo é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
        if not layout_id:
            return Response({'detail': 'Layout é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            layout = Layout.objects.get(id=layout_id)
        except Layout.DoesNotExist:
            return Response({'detail': 'Layout não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        proposal_file = ProposalFile.objects.create(
            file=file
        )
        proposal_batch = ProposalBatch.objects.create(
            file=proposal_file,
            layout=layout,
            status='pending'
        )
        return Response(status=status.HTTP_200_OK, data=ProposalBatchSerializer(proposal_batch).data)
    
    def get(self, request, pk=None):
        if pk:
            proposal_batch = ProposalBatch.objects.get(id=pk)
            return Response(status=status.HTTP_200_OK, data=ProposalBatchSerializer(proposal_batch).data)
        proposal_batches = ProposalBatch.objects.all()
        return Response(status=status.HTTP_200_OK, data=ProposalBatchSerializer(proposal_batches, many=True).data)
    
    def put(self, request, pk):
        proposal_batch = ProposalBatch.objects.get(id=pk)
        proposal_batch.status = 'processing'
        
        # Verificar se deve usar pipeline
        use_pipeline = request.data.get('use_pipeline', False)
        
        if use_pipeline:
            # Usar a nova task com pipeline
            task = process_proposal_batch_with_pipeline.delay(proposal_batch.id)
            message = "Processamento iniciado com pipeline modular"
        else:
            # Usar a task original
            task = process_proposal_batch.delay(proposal_batch.id)
            message = "Processamento iniciado com task original"
        
        # Capturar o task_id real retornado pelo Celery
        proposal_batch.task_id = task.id  # Salvar o task_id real
        proposal_batch.save()
        
        return Response(status=status.HTTP_200_OK, data={
            'proposal_batch': proposal_batch.id,
            'task_id': task.id,
            'message': message,
            'use_pipeline': use_pipeline
        })

    def delete(self, request, pk):
        try:
            proposal_batch = ProposalBatch.objects.get(id=pk)

            # Verificar se existem comissões geradas a partir deste lote
            commission_count = Commission.objects.filter(
                proposal__batch=proposal_batch
            ).count()

            if commission_count > 0:
                return Response(
                    {
                        'detail': f'Não é possível deletar este lote. Existem {commission_count} comissões geradas.',
                        'commission_count': commission_count
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Se não houver comissões, deletar o lote
            batch_id = proposal_batch.id
            proposal_batch.delete()

            self.log_info(
                request=request,
                action='delete_batch',
                message=f'Lote {batch_id} deletado com sucesso'
            )

            return Response(
                {'detail': 'Lote deletado com sucesso'},
                status=status.HTTP_204_NO_CONTENT
            )

        except ProposalBatch.DoesNotExist:
            return Response(
                {'detail': 'Lote não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Erro ao deletar lote: {str(e)}")
            return Response(
                {'detail': f'Erro ao deletar lote: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProposalPreviewView(BaseApiView):
    """
    View para visualizar as propostas antes de processar o arquivo em lote.
    """
    permission_classes = [IsAdmin]
    
    
    
    def match_object(self, object_name, value):
        try:
            value = normalize_value(value)
            if(object_name == 'table'):
                table = Table.objects.filter(name_in_bank__icontains=value).first()
                if(not table):
                    tables = Table.objects.all()
                    for table in tables:
                        if(value in table.alias):
                            return table
                    return None
                return table
            elif(object_name == 'agreement'):
                agreement = Agreement.objects.filter(name__icontains=value).first()
                if(not agreement):
                    agreements = Agreement.objects.all()
                    for agreement in agreements:
                        if(value in agreement.alias):
                            return agreement
                    return None
                return agreement
            elif(object_name == 'user'):
                user = BankAccess.objects.filter(username__icontains=value).first()
                if(not user):
                    users = BankAccess.objects.all()
                    for user in users:
                        if(value in user.alias):
                            return user.user
                    return None
                return user.user
        except Exception as e:
            logger.error(e)
            return None
    def get(self, request, pk):
        proposal_batch = ProposalBatch.objects.get(id=pk)
        file_path = proposal_batch.file.file.path
        data = file_to_dict(file_path)
        relation_tables = []
        relation_users = []
        relation_agreements = []
        relation_statuses = []
        tables_seen = set()
        users_seen = set()
        agreements_seen = set()
        statuses_seen = set()

        # Resolve field mappings once (outside the loop)
        table_field = proposal_batch.layout.map_fields.filter(name='table').first()
        user_field = proposal_batch.layout.map_fields.filter(name='seller').first()
        agreement_field = proposal_batch.layout.map_fields.filter(name='agreement').first()
        status_field = proposal_batch.layout.map_fields.filter(name='status').first()

        for row in data:
            # Lookup by header_name (dict key) instead of positional index
            def get_value(field):
                if not field:
                    return None
                val = row.get(field.header_name)
                if val is None or str(val) == 'nan' or val == '':
                    return None
                return str(val).strip()

            # Processa tabelas
            table_name = get_value(table_field)
            if table_name and table_name not in tables_seen:
                tables_seen.add(table_name)
                table = self.match_object('table', table_name)
                if table:
                    # Use agreement name for display instead of table ID
                    display_name = table.agreement.name if table.agreement else table.name_in_bank
                    relation_tables.append({'name_in_bank': table_name, 'id': table.id, 'name': display_name})
                else:
                    relation_tables.append({'name_in_bank': table_name, 'id': None, 'name': None})

            # Processa usuários
            user_name = get_value(user_field)
            if user_name and user_name not in users_seen:
                users_seen.add(user_name)
                user = self.match_object('user', user_name)
                if user:
                    relation_users.append({'name_in_bank': user_name, 'id': user.id, 'name': user.first_name, 'type': 'user'})
                else:
                    relation_users.append({'name_in_bank': user_name, 'id': None, 'name': None, 'type': 'user'})

            # Processa acordos
            agreement_name = get_value(agreement_field)
            if agreement_name and agreement_name not in agreements_seen:
                agreements_seen.add(agreement_name)
                agreement = self.match_object('agreement', agreement_name)
                if agreement:
                    relation_agreements.append({'name_in_bank': agreement_name, 'id': agreement.id, 'name': agreement.name, 'type': 'agreement'})
                else:
                    relation_agreements.append({'name_in_bank': agreement_name, 'id': None, 'name': None, 'type': 'agreement'})

            # Processa status
            status_name = get_value(status_field)
            if status_name and status_name not in statuses_seen:
                statuses_seen.add(status_name)
                bank = proposal_batch.layout.bank
                status_name_lower = status_name.lower().strip()
                # First try exact name match
                status_payment = StatusPayment.objects.filter(name=status_name, bank=bank).first()
                # Then try alias match (iterate like other categories)
                if not status_payment:
                    for sp in StatusPayment.objects.filter(bank=bank):
                        if sp.alias and status_name_lower in [a.lower().strip() for a in sp.alias]:
                            status_payment = sp
                            break
                if status_payment:
                    relation_statuses.append({'name_in_bank': status_name, 'id': status_payment.id, 'name': status_payment.name, 'type': 'status'})
                else:
                    relation_statuses.append({'name_in_bank': status_name, 'id': None, 'name': None, 'type': 'status'})

        return Response(status=status.HTTP_200_OK, data={'relation_tables': relation_tables, 'relation_users': relation_users, 'relation_agreements': relation_agreements, 'relation_statuses': relation_statuses})
    
class AgreementNamesView(BaseApiView):
    """
    View para relacionar os nomes dos acordos com os nomes no arquivo de proposta.
    """
    permission_classes = [IsAdmin]
    
    def post(self, request):
        data = request.data
        for row in data.get('relationships'):
            agreements_names = list(map(normalize_value, row['names_in_bank']))
            id = row['id']
            agreement = Agreement.objects.get(id=id)
            agreement.alias = agreements_names
            agreement.save()
            logger.info(f"Mapeamento de Convenio salvo: {id} -> {agreements_names}")
        return Response(status=status.HTTP_200_OK, data=data)
    
    def get(self, request):
        agreements = Agreement.objects.all()
        return Response(status=status.HTTP_200_OK, data=AgreementSerializer(agreements, many=True).data)
    
class TableNamesView(BaseApiView):
    """
    View para relacionar os nomes das tabelas com os nomes no arquivo de proposta.
    """
    permission_classes = [IsAdmin]
    
    def post(self, request):
        data = request.data
        bank_id = data.get('bank_id')
        Table.objects.filter(bank_id=bank_id).update(alias=[])
        for row in data.get('relationships'):
            table_names = list(map(normalize_value, row['names_in_bank']))
            id = row['id']
            table = Table.objects.get(id=id)
            tables = Table.objects.filter(name_in_bank = table.name_in_bank, bank_id=bank_id)
            for table_ in tables:
                table_.alias = table_names
                table_.save()
                logger.info(f"Mapeamento de Tabela salvo: {id} -> {table_names}")
        return Response(status=status.HTTP_200_OK, data=data)
    
    def get(self, request):
        bank_id = request.query_params.get('bank_id')
        if(bank_id):
            tables = Table.objects.filter(bank_id=bank_id)
        else:
            tables = Table.objects.all()
        tables_data = []
        tb = []
        for table in tables:
            if(table.name_in_bank not in tables_data):
                tb.append(table)
            tables_data.append(table.name_in_bank)
            
        return Response(status=status.HTTP_200_OK, data=TableSerializer(tb, many=True).data)  
class UserNamesView(BaseApiView):
    """
    View para relacionar os nomes dos usuários com os nomes no arquivo de proposta.
    """
    permission_classes = [IsAdmin]  
    
    def post(self, request):
        data = request.data
        proposal_batch = ProposalBatch.objects.get(id=data.get('proposal_batch'))
        for row in data.get('relationships'):
            user_names = list(map(normalize_value, row['names_in_bank']))
            id = row['id']
            user = BankAccess.objects.filter(user_id=id).first()

            # Se names_in_bank está vazio, limpar mapeamento
            if not user_names:
                if user:
                    user.alias = []
                    user.username = ""
                    user.save()
                    logger.info(f"Mapeamento de Vendedor limpo: {id}")
                continue

            if(not user):
                user = BankAccess.objects.create(
                    bank=proposal_batch.layout.bank,
                    username=user_names[0],
                    password="",
                    alias=user_names,
                    user_id=id
                )
                logger.info(f"Novo BankAccess criado: {id} -> {user_names}")
            else:
                same_alias = BankAccess.objects.filter(alias__in=user_names)
                if(same_alias.exists()):
                    for alias in same_alias:
                        for name in user_names:
                            if(name in alias.alias):
                                alias.alias.remove(name)
                                alias.save()
                user.alias = user_names
                user.username = user_names[0]
                user.save()
                logger.info(f"Mapeamento de Vendedor salvo: {id} -> {user_names}")

        return Response(status=status.HTTP_200_OK, data=data)
    
    def get(self, request):
        users = BankAccess.objects.all()
        users_data = []
        for user in users:
            serializer_data = UserSerializer(user.user).data
            serializer_data['alias'] = user.alias
            users_data.append(serializer_data)
        return Response(status=status.HTTP_200_OK, data=users_data)

class ProposalsByBatchView(BaseApiView):
    """
    View para obter as propostas por lote.
    """
    permission_classes = [IsAdmin]
    
    def get(self, request, pk):
        proposal_batch = ProposalBatch.objects.get(id=pk)
        proposals = Proposal.objects.filter(batch=proposal_batch)
        return Response(status=status.HTTP_200_OK, data=ProposalSerializer(proposals, many=True).data)
    
    def delete(self, request, pk):
        proposal_batch = ProposalBatch.objects.get(id=pk)
        proposals = Proposal.objects.filter(batch=proposal_batch)
        check = Commission.objects.filter(proposal__in=[p.id for p in proposals], released=True).exists()
        if check:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': 'Não é possível excluir propostas com comissões liberadas.'})
        for proposal in proposals:
            Commission.objects.filter(proposal=proposal).delete()
            proposal.delete()
        proposal_batch.delete()
        return Response(status=status.HTTP_200_OK, data={'message': 'Propostas e lote excluídos com sucesso'})

class ProposalListView(BaseApiView):
    """
    View para listar propostas com filtros e paginação.
    """
    permission_classes = [IsAdmin]
    
    def get(self, request):
        # Paginação
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        
        # Filtros
        bank_id = request.GET.get('bank')
        client_cpf = request.GET.get('client_cpf')
        company_id = request.GET.get('company')
        seller_id = request.GET.get('seller')
        contract_number = request.GET.get('contract_number')
        begin_date = request.GET.get('begin_date')
        end_date = request.GET.get('end_date')
        agreement_id = request.GET.get('agreement')
        table_id = request.GET.get('table')
        search = request.GET.get('search')
        
        # Query base
        proposals = Proposal.objects.select_related(
            'seller', 'company', 'bank', 'agreement', 'table', 'batch'
        ).all()
        
        # Aplicar filtros
        if bank_id:
            proposals = proposals.filter(bank_id=bank_id)
        if client_cpf:
            proposals = proposals.filter(client_document__icontains=client_cpf)
        if company_id:
            proposals = proposals.filter(company_id=company_id)
        if seller_id:
            proposals = proposals.filter(seller_id=seller_id)
        if contract_number:
            proposals = proposals.filter(contract_number__icontains=contract_number)
        if agreement_id:
            proposals = proposals.filter(agreement_id=agreement_id)
        if table_id:
            proposals = proposals.filter(table_id=table_id)
        if begin_date and end_date:
            proposals = proposals.filter(created_at__range=(begin_date, end_date))
        if search:
            proposals = proposals.filter(
                Q(contract_number__icontains=search) |
                Q(client_document__icontains=search) |
                Q(client_name__icontains=search)
            )
        
        # Ordenar
        proposals = proposals.order_by('-created_at')
        
        # Contar total
        total_count = proposals.count()
        
        # Paginar
        start = (page - 1) * page_size
        end = start + page_size
        proposals = proposals[start:end]
        
        return Response({
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'results': ProposalSerializer(proposals, many=True).data
        })


class StatusPaymentView(BaseApiView):
    """
    View para gerenciar os status de pagamento.
    """
    permission_classes = [IsAdmin]
    
    def get(self, request):
        bank = Bank.objects.get(id=request.query_params.get('bank_id'))
        statuses = StatusPayment.objects.filter(bank=bank)
        if not statuses.exists():
            statuses = [
                StatusPayment(name="Pago", bank=bank),
                StatusPayment(name="Aguardando pagamento", bank=bank),
                StatusPayment(name="Cancelado", bank=bank),
            ]
            StatusPayment.objects.bulk_create(statuses)
        return Response(status=status.HTTP_200_OK, data=StatusPaymentSerializer(statuses, many=True).data)  
    
    def post(self, request):
        data = request.data
        relationships = data.get('relationships', [])
        if not relationships:
            logger.warning("StatusPaymentView.post() recebeu relationships vazio")
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'error': 'relationships é obrigatório'})

        for relationship in relationships:
            status_id = relationship.get('id')
            names_in_bank = relationship.get('names_in_bank', [])

            if not status_id:
                logger.warning(f"StatusPaymentView.post() recebeu id vazio em relationship: {relationship}")
                continue

            status_payment = StatusPayment.objects.filter(id=status_id).first()
            if not status_payment:
                logger.error(f"StatusPayment com id {status_id} não encontrado")
                continue

            status_payment.alias = names_in_bank
            status_payment.save()
            logger.info(f"Mapeamento de Status salvo: {status_id} -> {names_in_bank}")

        return Response(status=status.HTTP_200_OK, data=data)
    
    def delete(self, request, pk):
        status_payment = get_object_or_404(StatusPayment, id=pk)
        status_payment.delete()
        return Response(status=status.HTTP_200_OK, data={'message': 'Status de pagamento excluído com sucesso'})