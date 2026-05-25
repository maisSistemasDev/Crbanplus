"""
Serializers para os modelos de pagamentos e comissionamentos.
"""
from rest_framework import serializers
from core.serializers import UserListSerializer
from core.models import User, Company
from .models import CommissionGroup, Payment, Commission, CommissionGroupByCompany, CommissionRules, CommissionRulesByUser, PaymentManual, Withdraw
from bank.models import Bank, Table
from core.serializers import CompanySerializer
from proposals.serializers import ProposalSerializer
import csv
from datetime import datetime

class CommissionRulesSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo CommissionRules.
    """
    class Meta:
        model = CommissionRules
        fields = ['id', 'bank', 'table', 'commission_range', 'commission_rate']

class CommissionRulesByUserSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo CommissionRulesByUser.
    """
    class Meta:
        model = CommissionRulesByUser
        fields = ['id', 'bank', 'table', 'commission_range', 'leader_commission_rate', 'seller_commission_rate']

class CommissionGroupSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo CommissionGroup.
    """
    commission_rules = CommissionRulesByUserSerializer(many=True, read_only=True)
    promotora_rules = CommissionRulesSerializer(many=True, read_only=True)
    class Meta:
        model = CommissionGroup
        fields = [
            'id', 'name', 'description', 'company', 'is_active',
            'created_at', 'updated_at', 'sellers', 'leaders', 'color',
            'commission_rules', 'promotora_rules', 'is_active', 'by_leader', 'leader'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'company': {'required': False, 'allow_null': True},
        }
    
    def sellers_options(self):  
        """
        Retorna as opções de vendedores disponíveis para o formulário.
        """
        return [
            {'value': user.id, 'label': user.get_full_name()}
            for user in self.instance.sellers.all()
        ]
    
    def leaders_options(self):
        """
        Retorna as opções de líderes disponíveis para o formulário.
        """
        return [
            {'value': user.id, 'label': user.get_full_name()}
            for user in self.instance.leaders.all()
        ]
    
    def get_company_options(self, user: User):
        """
        Retorna as opções de empresas disponíveis para o formulário.
        """
        companies = Company.objects.all() if user.role == User.ADMIN else [user.company]
        return [
            {'value': company.id, 'label': company.name}
            for company in companies
        ]
        
    
    def form_fields(self, user: User):
        """
        Retorna informações sobre os campos para construção de formulários no frontend.
        """
        fields = [
            {'name': 'name', 'type': 'text', 'label': 'Nome', 'required': True},
            {'name': 'description', 'type': 'textarea', 'label': 'Descrição', 'required': False},
            {'name': 'is_active', 'type': 'checkbox', 'label': 'Ativo', 'required': False},
            {'name': 'company', 'type': 'select', 'label': 'Empresa', 'required': True, 'options': self.get_company_options(user)},
            {'name': 'color', 'type': 'color', 'label': 'Cor', 'required': False}
        ]
        return fields

class CommissionGroupByCompanySerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo CommissionGroupByCompany.
    """
    commission_rules = CommissionRulesSerializer(source='comission_rules', many=True, read_only=True)
    companies = CompanySerializer(many=True, read_only=True)
    class Meta:
        model = CommissionGroupByCompany
        fields = [
            'id', 'name', 'description', 
            'created_at', 'updated_at', 'color',
            'commission_rules', 'is_active', 'companies'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def bank_options(self):
        """
        Retorna as opções de bancos disponíveis para o formulário.
        """
        return [
                {'value': bank.id, 'label': bank.name} for bank in Bank.objects.all()
        ]
    
    def table_options(self):
        """
        Retorna as opções de tabelas disponíveis para o formulário.
        """
        return [
            {'value': table.id, 'label': table.name_in_bank} for table in Table.objects.all()
        ]
    
    def form_fields(self):
        """
        Retorna informações sobre os campos para construção de formulários no frontend.
        """
        return [
            {'name': 'name', 'type': 'text', 'label': 'Nome', 'required': True},
            {'name': 'description', 'type': 'textarea', 'label': 'Descrição', 'required': False},
            {'name': 'comission_rate', 'type': 'number', 'label': 'Porcentagem de Comissão', 'required': True, 'min': 0, 'max': 100, 'step': '0.01'},
            {'name': 'color', 'type': 'color', 'label': 'Cor', 'required': False}
            ,
        ]
 
        
class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo Payment.
    """
    user_details = UserListSerializer(source='user', read_only=True)
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_details', 'total_amount', 'status',
            'status_display', 'approved_by', 'approved_at', 'paid_at',
            'payment_method', 'payment_details', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'approved_at', 'approved_by', 'status_display']
    
    def get_status_display(self, obj):
        return obj.get_status_display()
    
    def form_fields(self):
        """
        Retorna informações sobre os campos para construção de formulários no frontend.
        """
        return [
            {'name': 'user', 'type': 'select', 'label': 'Usuário', 'required': True, 'options_url': '/api/users/'},
            {'name': 'total_amount', 'type': 'number', 'label': 'Valor Total', 'required': True, 'step': '0.01'},
            {'name': 'status', 'type': 'select', 'label': 'Status', 'required': True, 'options': [
                {'value': 'pending', 'label': 'Pendente'},
                {'value': 'approved', 'label': 'Aprovado'},
                {'value': 'paid', 'label': 'Pago'},
                {'value': 'rejected', 'label': 'Rejeitado'},
            ]},
            {'name': 'payment_method', 'type': 'text', 'label': 'Método de Pagamento', 'required': False},
            {'name': 'notes', 'type': 'textarea', 'label': 'Observações', 'required': False},
        ]


class CommissionSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo Commission.
    """
    user_details = UserListSerializer(source='user', read_only=True)
    role_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Commission
        fields = [
            'id', 'proposal', 'user', 'user_details', 'company', 'role',
            'role_display', 'percentage', 'value', 'payment',
            'commission_config', 'created_at', 'updated_at', 'released', 
            'released_at', 'released_by', 'paid_at', 'paid_by', 'release_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'role_display', 'released', 'released_at', 'released_by', 'paid_at', 'paid_by', 'release_status']
    
    def get_role_display(self, obj):
        return obj.get_role_display()
    
    def form_fields(self):
        """
        Retorna informações sobre os campos para construção de formulários no frontend.
        """
        return [
            {'name': 'proposal', 'type': 'select', 'label': 'Proposta', 'required': True, 'options_url': '/api/proposals/'},
            {'name': 'user', 'type': 'select', 'label': 'Usuário', 'required': False, 'options_url': '/api/users/'},
            {'name': 'company', 'type': 'select', 'label': 'Empresa', 'required': False, 'options_url': '/api/companies/'},
            {'name': 'role', 'type': 'select', 'label': 'Função', 'required': True, 'options': [
                {'value': Commission.VENDEDOR, 'label': 'Vendedor'},
                {'value': Commission.LIDER, 'label': 'Líder'},
                {'value': Commission.EMPRESA, 'label': 'Empresa'},
            ]},
            {'name': 'percentage', 'type': 'number', 'label': 'Porcentagem', 'required': True, 'min': 0, 'max': 100, 'step': '0.01'},
            {'name': 'value', 'type': 'number', 'label': 'Valor', 'required': False, 'step': '0.01'},
            {'name': 'payment', 'type': 'select', 'label': 'Pagamento', 'required': False, 'options_url': '/api/payments/'},
            {'name': 'commission_group', 'type': 'select', 'label': 'Grupo de Comissionamento', 'required': False, 'options_url': '/api/commission-groups/'},
        ]
        

class CommissionMirrorSerializer(serializers.Serializer):
    """
    Serializer para o modelo CommissionMirror.
    """
    
    proposal = ProposalSerializer()
    commissions = CommissionSerializer(many=True)
    
    # Campos calculados para os nomes
    company_name = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()
    leader_name = serializers.SerializerMethodField()
    
    # Campos calculados para as comissões separadas por tipo
    seller_commissions = serializers.SerializerMethodField()
    leader_commissions = serializers.SerializerMethodField()
    company_commissions = serializers.SerializerMethodField()
    
    def get_company_name(self, obj):
        """
        Retorna o nome da empresa.
        """
        company_commission = next((c for c in obj.commissions if c.role == Commission.EMPRESA), None)
        return company_commission.company.name if company_commission and company_commission.company else None

    def get_seller_name(self, obj):
        """
        Retorna o nome do vendedor.
        """
        seller_commission = next((c for c in obj.commissions if c.role == Commission.VENDEDOR), None)
        return seller_commission.user.get_full_name() if seller_commission and seller_commission.user else None

    def get_leader_name(self, obj):
        """
        Retorna o nome do líder.
        """
        leader_commission = next((c for c in obj.commissions if c.role == Commission.LIDER), None)
        return leader_commission.user.get_full_name() if leader_commission and leader_commission.user else None

    def get_seller_commissions(self, obj):
        """
        Retorna as comissões do vendedor.
        """
        return [commission for commission in obj.commissions if commission.role == Commission.VENDEDOR]

    def get_leader_commissions(self, obj):
        """
        Retorna as comissões do líder.
        """
        return [commission for commission in obj.commissions if commission.role == Commission.LIDER]

    def get_company_commissions(self, obj):
        """
        Retorna as comissões da empresa.
        """
        return [commission for commission in obj.commissions if commission.role == Commission.EMPRESA]

class PaymentManualSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo PaymentManual.
    """
    class Meta:
        model = PaymentManual
        fields = ['id', 'payments', 'file', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        #Cria um novo pagamento manual com o csv com os pagamentos
        csv_file = f'payments_manual_{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.csv'
        with open(csv_file, 'w') as file:
            writer = csv.writer(file)
            writer.writerow(['ID', 'Valor', 'Status', 'Método de Pagamento', 'Detalhes do Pagamento'])
            for payment in validated_data['payments']:
                writer.writerow([payment.id, payment.total_amount, payment.status, payment.payment_method, payment.payment_details])
        payment_manual = PaymentManual.objects.create(file=csv_file)
        payment_manual.payments.set(validated_data['payments'])
        payment_manual.save()
        return payment_manual

class WithdrawSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo Withdraw.
    """
    class Meta:
        model = Withdraw
        fields = ['id', 'user', 'amount', 'created_at', 'payment']