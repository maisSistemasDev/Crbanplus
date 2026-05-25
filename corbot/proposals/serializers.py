import logging
from rest_framework import serializers
from .models import (
    Proposal, Layout, LayoutField, ProposalBatch, ErroredProposal, Agreement, Table, User, BatchLogFile, StatusPayment
)
from payments.models import Payment, Commission

logger = logging.getLogger(__name__)

class LayoutFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = LayoutField
        fields = ['id', 'name', 'index', 'header_name']
    
    def form_fields(self):
        return [
            {'name': 'name', 'type': 'text', 'label': 'Nome', 'required': True},
            {'name': 'index', 'type': 'number', 'label': 'Índice', 'required': True},
            {'name': 'header_name', 'type': 'text', 'label': 'Nome do cabeçalho', 'required': True},
        ]

class LayoutSerializer(serializers.ModelSerializer):
    map_fields = LayoutFieldSerializer(many=True)
    bank_name = serializers.CharField(source='bank.name', read_only=True)
    class Meta:
        model = Layout
        fields = ['id', 'name','bank', 'map_fields', 'bank_name', 'created_at', 'updated_at']
        
    def create(self, validated_data):
        map_fields_data = validated_data.pop('map_fields')
        layout = Layout.objects.create(**validated_data)
        for field_data in map_fields_data:
            LayoutField.objects.create(layout=layout, **field_data)
        return layout
    
    def form_fields(self):
        return [
            {'name': 'bank', 'type': 'select', 'label': 'Banco', 'required': True, 'relation': 'Bank'},
            {'name': 'map_fields', 'type': 'array', 'label': 'Campos', 'required': True, 'relation': 'LayoutField', 'options': LayoutField._meta.get_field('name').choices},
        ]

class ProposalBatchSerializer(serializers.ModelSerializer):
    log_url = serializers.SerializerMethodField()
    original_file_url = serializers.SerializerMethodField()
    bank_name = serializers.SerializerMethodField()
    bank_id = serializers.SerializerMethodField()
    layout_name = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    commissions_to_generate = serializers.SerializerMethodField()
    
    class Meta:
        model = ProposalBatch
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'processed_at', 'processed_rows', 'total_rows']

    def get_name(self, obj):
        """Gera um nome descritivo para o lote"""
        try:
            bank_name = obj.layout.bank.name if obj.layout else 'Sem banco'
            date_str = obj.created_at.strftime('%d/%m/%Y %H:%M') if obj.created_at else ''
            status_map = {
                'pending': 'Pendente',
                'processing': 'Processando',
                'completed': 'Concluído',
                'failed': 'Erro'
            }
            status_label = status_map.get(obj.status, obj.status)
            return f"{bank_name} - {date_str} - {status_label}"
        except Exception:
            return f"Lote {str(obj.id)[:8]}"

    def get_bank_name(self, obj):
        try:
            return obj.layout.bank.name if obj.layout else None
        except Exception:
            return None

    def get_bank_id(self, obj):
        try:
            return str(obj.layout.bank.id) if obj.layout else None
        except Exception:
            return None

    def get_layout_name(self, obj):
        try:
            return obj.layout.name if obj.layout else None
        except Exception:
            return None

    def get_log_url(self, obj):
        try:
            batchLog = BatchLogFile.objects.filter(batch=obj).first()
            if batchLog and batchLog.log_file:
                url = batchLog.log_file.url
                # Se houver request no contexto, construir URL absoluta
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(url)
                return url
        except Exception as e:
            logger.error(f"Erro ao gerar log_url: {e}")
        return None

    def get_original_file_url(self, obj: ProposalBatch):
        try:
            if obj.file and obj.file.file:
                url = obj.file.file.url
                # Se houver request no contexto, construir URL absoluta
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(url)
                return url
        except Exception as e:
            logger.error(f"Erro ao gerar original_file_url: {e}")
        return None

    def get_commissions_to_generate(self, obj: ProposalBatch):
        """Quantidade de propostas do lote que ainda nao possuem nenhuma comissao."""
        try:
            return Proposal.objects.filter(
                batch=obj,
                release_date__isnull=True,
                commissions__isnull=True,
            ).count()
        except Exception:
            return 0

class ErroredProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ErroredProposal
        fields = ['id', 'original_data', 'error_message', 'created_at', 'updated_at']

class AgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agreement
        fields = ['id', 'name', 'alias']

class TableSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = ['id', 'name', 'name_in_bank', 'alias']

    def get_name(self, obj):
        """Return name_in_bank if available, otherwise use agreement name"""
        if obj.name_in_bank:
            return obj.name_in_bank
        return obj.agreement.name if obj.agreement else None

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'cpf', 'first_name', 'last_name', 'email']

class ProposalSerializer(serializers.ModelSerializer):
    commissions = serializers.SerializerMethodField()
    seller_details = serializers.SerializerMethodField()
    company_details = serializers.SerializerMethodField()
    bank_details = serializers.SerializerMethodField()
    agreement_details = serializers.SerializerMethodField()
    table_details = serializers.SerializerMethodField()

    def get_commissions(self, obj):
        commission = Commission.objects.filter(proposal=obj).first()
        if commission:
            return {
                'id': commission.id,
                'user': commission.user.id if commission.user else None,
                'company': commission.company.id if commission.company else None,
                'role': commission.role,
                'percentage': commission.percentage,
                'value': commission.value,
                'table': commission.commission_config.table_config if commission.commission_config else None,
                'payment': commission.payment.id if commission.payment else None
            }
        return None

    def get_seller_details(self, obj):
        if obj.seller:
            return {'first_name': obj.seller.first_name, 'last_name': obj.seller.last_name}
        return None

    def get_company_details(self, obj):
        if obj.company:
            return {'name': obj.company.name}
        return None

    def get_bank_details(self, obj):
        if obj.bank:
            return {'name': obj.bank.name}
        return None

    def get_agreement_details(self, obj):
        if obj.agreement:
            return {'name': obj.agreement.name}
        return None

    def get_table_details(self, obj):
        if obj.table:
            return {'name_in_bank': obj.table.name_in_bank}
        return None

    class Meta:
        model = Proposal
        fields = '__all__'

class StatusPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusPayment
        fields = ['id', 'name', 'bank']