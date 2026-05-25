from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, ExtraData, AuditLog, ActionLog, Company, UserPermission, PermissionTemplate, APIKey, SystemSettings


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'prefix', 'created_by', 'company', 'is_active', 'last_used_at', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'prefix', 'created_by__cpf')
    readonly_fields = ('id', 'prefix', 'hashed_key', 'last_used_at', 'created_at', 'updated_at')


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('singleton', 'corbanpay_base_url', 'updated_by', 'updated_at')
    readonly_fields = ('singleton', 'updated_by', 'created_at', 'updated_at')


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'trading_name', 'person_type', 'document', 'email', 'is_active')
    list_filter = ('is_active', 'person_type')
    search_fields = ('name', 'trading_name', 'document', 'email')
    readonly_fields = ('id',)
    fieldsets = (
        (None, {'fields': ('id', 'name', 'trading_name', 'person_type', 'document', 'logo')}),
        (_('Cores'), {'fields': ('primary_color', 'secondary_color', 'accent_color')}),
        (_('Configurações'), {'fields': ('settings',)}),
        (_('Contato'), {'fields': ('email', 'phone', 'website')}),
        (_('Endereço'), {'fields': ('address', 'city', 'state', 'zip_code')}),
        (_('Status'), {'fields': ('is_active',)}),
    )


class ExtraDataInline(admin.StackedInline):
    model = ExtraData
    can_delete = False
    verbose_name_plural = 'Dados Adicionais'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('cpf', 'email', 'first_name', 'last_name', 'role', 'leader', 'company', 'is_active')
    list_filter = ('role', 'is_active', 'company')
    search_fields = ('cpf', 'email', 'first_name', 'last_name', 'matricula', 'certificado')
    ordering = ('cpf',)
    inlines = (ExtraDataInline,)
    
    fieldsets = (
        (None, {'fields': ('cpf', 'email', 'password')}),
        (_('Informa\u00e7\u00f5es Pessoais'), {'fields': ('first_name', 'last_name')}),
        (_('Dados Profissionais'), {'fields': ('certificado', 'matricula')}),
        (_('Hierarquia'), {'fields': ('role', 'leader', 'company')}),
        (_('Permissões'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Datas importantes'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('cpf', 'email', 'password1', 'password2', 'role', 'leader', 'company'),
        }),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'content_type', 'object_id', 'created_at')
    list_filter = ('action', 'content_type', 'created_at')
    search_fields = ('user__cpf', 'user__email', 'object_id')
    readonly_fields = ('user', 'action', 'content_type', 'object_id', 'data_before', 'data_after', 'ip_address', 'user_agent', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    list_display = ('level', 'action', 'user', 'message', 'created_at')
    list_filter = ('level', 'action', 'created_at')
    search_fields = ('user__cpf', 'user__email', 'action', 'message')
    readonly_fields = ('user', 'level', 'action', 'message', 'data', 'ip_address', 'user_agent', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'codename', 'category', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('user__cpf', 'user__email', 'name', 'codename')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('user', 'codename', 'name', 'category')}),
        (_('Descrição'), {'fields': ('description',)}),
        (_('Datas'), {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(PermissionTemplate)
class PermissionTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('name', 'description', 'is_active')}),
        (_('Permissões'), {'fields': ('permissions',)}),
        (_('Datas'), {'fields': ('created_at', 'updated_at')}),
    )
 