from django.contrib import admin
from .models import BankAccess, AccessLog


@admin.register(BankAccess)
class BankAccessAdmin(admin.ModelAdmin):
    list_display = ('username', 'bank', 'user', 'is_master', 'is_active')
    list_filter = ('is_active', 'bank')
    search_fields = ('username', 'bank__name', 'user__first_name', 
                    'user__last_name', 'user__cpf')
    readonly_fields = ('id', 'created_by')
    date_hierarchy = 'created_at'


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('bank_access', 'user', 'access_time', 'status')
    list_filter = ('status', 'access_time')
    search_fields = ('bank_access__username', 'bank_access__bank__name', 
                    'user__first_name', 'user__last_name', 'user__cpf')
    readonly_fields = ('id', 'bank_access', 'user', 'access_time', 'ip_address', 
                      'user_agent', 'status', 'details', 'data')
    date_hierarchy = 'access_time' 