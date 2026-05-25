"""
Configuração do admin para os modelos do app de pagamentos.
"""
from django.contrib import admin
from .models import CommissionGroup, Payment, Commission


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
