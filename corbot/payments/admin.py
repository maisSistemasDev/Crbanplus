"""
Configuração do admin para os modelos do app de pagamentos.
"""
from django.contrib import admin
from .models import CommissionGroup, Payment, Commission, UserDebit, CommissionDebitDiscount, ProposalClaim


@admin.register(CommissionGroup)
class CommissionGroupAdmin(admin.ModelAdmin):
    """
    Admin para o modelo CommissionGroup.
    """
    list_display = ('name', 'company', 'is_active')
    list_filter = ('company', 'is_active')
    search_fields = ('name', 'company__name')


class CommissionInline(admin.TabularInline):
    """
    Inline para o modelo Commission.
    """
    model = Commission
    extra = 0
    can_delete = False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Admin para o modelo Payment.
    """
    list_display = ('user', 'total_amount', 'status', 'approved_by', 'approved_at', 'paid_at')
    list_filter = ('status', 'approved_by')
    search_fields = ('user__first_name', 'user__last_name', 'user__cpf')
    readonly_fields = ('approved_by', 'approved_at', 'paid_at')
    inlines = [CommissionInline]


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    """
    Admin para o modelo Commission.
    """
    list_display = ('proposal', 'user', 'company', 'role', 'percentage', 'value', 'payment', 'commission_config', 'created_at')
    readonly_fields = ('proposal', 'user', 'company', 'role',  'value', 'payment', 'commission_config')
    list_filter = ('role', 'payment__status')
    search_fields = ('user__first_name', 'user__last_name', 'user__cpf', 'proposal__proposal_number')


@admin.register(UserDebit)
class UserDebitAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'company', 'origin', 'amount', 'remaining_amount', 'is_active', 'created_by', 'created_at')
    list_filter = ('origin', 'is_active', 'created_at')
    search_fields = (
        'user__first_name', 'user__last_name', 'user__cpf', 'user__email', 'user__matricula',
        'company__name', 'company__document', 'reason',
    )


@admin.register(ProposalClaim)
class ProposalClaimAdmin(admin.ModelAdmin):
    list_display = ('id', 'proposal', 'claim_type', 'amount', 'charged_company', 'correct_company', 'created_by', 'created_at')
    list_filter = ('claim_type', 'created_at')
    search_fields = ('proposal__contract_number', 'proposal__client_document', 'description')


@admin.register(CommissionDebitDiscount)
class CommissionDebitDiscountAdmin(admin.ModelAdmin):
    list_display = ('id', 'commission', 'debit', 'amount', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('commission__proposal__contract_number', 'debit__user__cpf', 'debit__reason')
