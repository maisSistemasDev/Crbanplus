from django.contrib import admin
from .models import Bank, Agreement, Table, TableHistory, CommissionRange


@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ('name', 'website', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    readonly_fields = ('id',)


@admin.register(Agreement)
class AgreementAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    readonly_fields = ('id',)


class CommissionRangeInline(admin.TabularInline):
    model = CommissionRange
    extra = 1
    fields = ('min_value', 'max_value', 'commission_rate')
    readonly_fields = ()


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('name_in_bank', 'bank', 'agreement', 'is_active')
    list_filter = ('is_active', 'bank', 'agreement')
    search_fields = ('name_in_bank', 'bank__name', 'agreement__name')
    readonly_fields = ('id',)
    inlines = [CommissionRangeInline]


@admin.register(TableHistory)
class TableHistoryAdmin(admin.ModelAdmin):
    list_display = ('table', 'action', 'user', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('table__name_in_bank', 'user__email', 'notes')
    readonly_fields = ('id', 'table', 'action', 'user', 'field_changes', 'previous_values', 'new_values', 'created_at')
    
    def has_add_permission(self, request):
        # Não permite criar histórico manualmente
        return False
    
    def has_change_permission(self, request, obj=None):
        # Não permite editar histórico
        return False 