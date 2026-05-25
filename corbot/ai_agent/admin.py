from django.contrib import admin

from .models import Conversation, Message, TableUpdateSuggestion


@admin.register(TableUpdateSuggestion)
class TableUpdateSuggestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'commission_group', 'table', 'status', 'created_at', 'applied_by']
    list_filter = ['status', 'created_at']
    search_fields = ['commission_group__name', 'table__name_in_bank']
    readonly_fields = ['old_config', 'suggested_config', 'ai_reasoning', 'created_at', 'applied_at', 'applied_by']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['user__email', 'user__first_name']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'role', 'created_at']
    list_filter = ['role', 'created_at']
