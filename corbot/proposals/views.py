import logging
import re

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import CharField, Count, Func, Prefetch, Q
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
from .utils import read_file_columns, get_required_fields, get_layout_mapping_fields, file_to_dict
from .preview_matcher import BatchPreviewMatcher
from .services import proposal_queryset_for_actor, proposal_batch_queryset_for_actor
from .proposal_query import StripNonDigits, apply_proposal_filters

from .models import Proposal, Layout, LayoutField, ProposalFile, ProposalBatch, ErroredProposal
from .serializers import *
from core.permissions import IsGerente, IsGerenteOrLider, IsAdmin
from core.services import AuditService, LogService
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Bank, Agreement, ProposalBatch, ErroredProposal, StatusPayment
from celery.result import AsyncResult
from core.base_views import BaseApiView
from core.search_utils import split_filter_values
from bank.models import Table, Agreement, Bank
from bank_access.models import BankAccess
from payments.models import Payment, Commission
from .tasks import process_proposal_batch, process_proposal_batch_with_pipeline
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def filtered_proposals_for(request):
    """Propostas do escopo do usuário já com os filtros da tela aplicados."""
    proposals = proposal_queryset_for_actor(
        Proposal.objects.select_related(
            'seller', 'company', 'bank', 'agreement', 'table', 'batch', 'bank_access',
        ).prefetch_related(
            Prefetch(
                'commissions',
                queryset=Commission.objects.select_related(
                    'user', 'company', 'payment', 'commission_config',
                ),
            ),
            'claims__charged_company',
            'claims__correct_company',
        ),
        request.user,
    )
    return apply_proposal_filters(request, proposals)


def delete_proposal_batch(proposal_batch: ProposalBatch) -> dict:
    """
    Remove lote e tudo vinculado: propostas, erros, comissões não pagas e logs.
    Bloqueia apenas se houver comissão já paga.
    """
    proposal_ids = list(
        Proposal.objects.filter(batch=proposal_batch).values_list('id', flat=True)
    )

    paid_count = Commission.objects.filter(
        proposal_id__in=proposal_ids,
        release_status=Commission.PAID,
    ).count()
    if paid_count:
        raise ValueError(
            f'Não é possível excluir este lote. Existem {paid_count} comissões já pagas.'
        )

    payment_ids = list(
        Commission.objects.filter(proposal_id__in=proposal_ids)
        .exclude(payment_id=None)
        .values_list('payment_id', flat=True)
        .distinct()
    )
    commissions_deleted, _ = Commission.objects.filter(proposal_id__in=proposal_ids).delete()
    Payment.objects.filter(id__in=payment_ids, commissions__isnull=True).delete()
    proposals_count = len(proposal_ids)
    errored_count = ErroredProposal.objects.filter(batch=proposal_batch).count()

    batch_id = proposal_batch.id
    proposal_batch.delete()

    return {
        'batch_id': batch_id,
        'deleted_proposals': proposals_count,
        'deleted_errored': errored_count,
        'deleted_commissions': commissions_deleted,
    }


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
        model_fields = get_layout_mapping_fields()
        
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
            
            model_fields = get_layout_mapping_fields()
            
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
        # Validação: pelo menos um dos campos "digitador" ou "bank_access" deve estar mapeado
        mapped_names = set(mapping.keys()) if mapping else set()
        if not mapped_names.intersection({'digitador', 'bank_access'}):
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={
                    'error': 'Layout deve possuir pelo menos um dos campos mapeados: "Digitador" ou "Acessos".',
                    'code': 'missing_digitador_or_access'
                }
            )

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


class LayoutBulkDeleteView(BaseApiView):
    """
    API endpoint para exclusão em massa de layouts.
    Recebe uma lista de IDs via body: {"ids": ["uuid1", "uuid2", ...]}
    """
    permission_classes = [IsAdmin]

    def delete(self, request, format=None):
        ids = request.data.get('ids', [])
        if not ids or not isinstance(ids, list):
            return Response({"detail": "Forneça uma lista de IDs em 'ids'."}, status=status.HTTP_400_BAD_REQUEST)

        layouts = Layout.objects.filter(id__in=ids)
        deleted_count = layouts.count()
        layouts.delete()

        self.log_info(
            request=request,
            action='bulk_delete_layouts',
            message=f'Usuário excluiu {deleted_count} layout(s) em massa.',
            data={'ids': ids, 'deleted_count': deleted_count}
        )

        return Response({"deleted": deleted_count}, status=status.HTTP_200_OK)


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
    Leitura (GET) é liberada para toda a hierarquia (filtrada); escrita é restrita ao admin.
    """
    parser_classes = (MultiPartParser, FormParser)

    def get_permissions(self):
        if self.request.method == 'GET':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [IsAdmin]
        return [permission() for permission in permission_classes]

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
        batches = proposal_batch_queryset_for_actor(ProposalBatch.objects.all(), request.user)
        if pk:
            proposal_batch = get_object_or_404(batches, id=pk)
            return Response(status=status.HTTP_200_OK, data=ProposalBatchSerializer(proposal_batch).data)
        batches = batches.order_by('-created_at')
        return Response(status=status.HTTP_200_OK, data=ProposalBatchSerializer(batches, many=True).data)
    
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
            proposal_batch = get_object_or_404(ProposalBatch, id=pk)

            with transaction.atomic():
                result = delete_proposal_batch(proposal_batch)

            self.log_info(
                request=request,
                action='delete_batch',
                message=(
                    f"Lote {result['batch_id']} deletado "
                    f"({result['deleted_proposals']} propostas, "
                    f"{result['deleted_commissions']} comissões)"
                ),
            )

            return Response(
                {
                    'detail': 'Lote e propostas vinculadas deletados com sucesso',
                    **result,
                },
                status=status.HTTP_200_OK,
            )

        except ProposalBatch.DoesNotExist:
            return Response(
                {'detail': 'Lote não encontrado'},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Erro ao deletar lote: {str(e)}")
            return Response(
                {'detail': f'Erro ao deletar lote: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProposalPreviewView(BaseApiView):
    """
    View para visualizar as propostas antes de processar o arquivo em lote.
    """
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        proposal_batch = (
            ProposalBatch.objects.select_related('layout__bank', 'file')
            .prefetch_related('layout__map_fields')
            .get(id=pk)
        )
        file_path = proposal_batch.file.file.path
        data = file_to_dict(file_path)
        bank = proposal_batch.layout.bank
        matcher = BatchPreviewMatcher(bank)

        relation_tables = []
        relation_users = []
        relation_agreements = []
        relation_statuses = []
        tables_seen = set()
        users_seen = set()
        agreements_seen = set()
        statuses_seen = set()

        field_by_name = {f.name: f for f in proposal_batch.layout.map_fields.all()}
        table_field = field_by_name.get('table')
        user_field = field_by_name.get('bank_access') or field_by_name.get('seller')
        agreement_field = field_by_name.get('agreement')
        status_field = field_by_name.get('status')

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
                table = matcher.match_table(table_name)
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
                user = matcher.match_user(user_name)
                if user:
                    relation_users.append({'name_in_bank': user_name, 'id': user.id, 'name': user.first_name, 'type': 'user'})
                else:
                    relation_users.append({'name_in_bank': user_name, 'id': None, 'name': None, 'type': 'user'})

            # Processa acordos
            agreement_name = get_value(agreement_field)
            if agreement_name and agreement_name not in agreements_seen:
                agreements_seen.add(agreement_name)
                agreement = matcher.match_agreement(agreement_name)
                if agreement:
                    relation_agreements.append({'name_in_bank': agreement_name, 'id': agreement.id, 'name': agreement.name, 'type': 'agreement'})
                else:
                    relation_agreements.append({'name_in_bank': agreement_name, 'id': None, 'name': None, 'type': 'agreement'})

            # Processa status
            status_name = get_value(status_field)
            if status_name and status_name not in statuses_seen:
                statuses_seen.add(status_name)
                status_payment = matcher.match_status(status_name)
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
    Leitura (GET) liberada para toda a hierarquia (filtrada por vendedor/equipe/empresa); exclusão restrita ao admin.
    """
    def get_permissions(self):
        if self.request.method == 'GET':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [IsAdmin]
        return [permission() for permission in permission_classes]

    def get(self, request, pk):
        proposal_batch = get_object_or_404(
            proposal_batch_queryset_for_actor(ProposalBatch.objects.all(), request.user),
            id=pk,
        )
        proposals = proposal_queryset_for_actor(
            Proposal.objects.filter(batch=proposal_batch).select_related(
                'seller', 'company', 'bank', 'agreement', 'table', 'bank_access',
            ).prefetch_related(
                Prefetch(
                    'commissions',
                    queryset=Commission.objects.select_related(
                        'user', 'company', 'payment', 'commission_config',
                    ),
                ),
                'claims__charged_company',
                'claims__correct_company',
            ),
            request.user,
        )
        return Response(
            status=status.HTTP_200_OK,
            data=ProposalSerializer(proposals, many=True, context={'request': request}).data,
        )
    
    def delete(self, request, pk):
        try:
            proposal_batch = get_object_or_404(ProposalBatch, id=pk)
            with transaction.atomic():
                result = delete_proposal_batch(proposal_batch)
            return Response(
                status=status.HTTP_200_OK,
                data={
                    'message': 'Propostas e lote excluídos com sucesso',
                    **result,
                },
            )
        except ValueError as e:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={'error': str(e)},
            )

class ProposalListView(BaseApiView):
    """
    View para listar propostas com filtros e paginação.
    Leitura liberada para toda a hierarquia; cada perfil só vê as propostas da própria rede.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Paginação
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        
        proposals = filtered_proposals_for(request).order_by('-created_at')
        
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
            'results': ProposalSerializer(proposals, many=True, context={'request': request}).data
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