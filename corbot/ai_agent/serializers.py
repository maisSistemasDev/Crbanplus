from rest_framework import serializers

from .models import Conversation, Message, TableUpdateSuggestion


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'role', 'content', 'tool_calls', 'created_at']
        read_only_fields = ['id', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'created_at', 'updated_at', 'messages']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TableUpdateSuggestionSerializer(serializers.ModelSerializer):
    commission_group_name = serializers.CharField(
        source='commission_group.name', read_only=True
    )
    table_name = serializers.CharField(
        source='table.name_in_bank', read_only=True
    )
    bank_name = serializers.CharField(
        source='table.bank.name', read_only=True
    )

    class Meta:
        model = TableUpdateSuggestion
        fields = [
            'id',
            'commission_group',
            'commission_group_name',
            'table',
            'table_name',
            'bank_name',
            'old_config',
            'suggested_config',
            'ai_reasoning',
            'status',
            'created_at',
            'applied_at',
            'applied_by',
        ]
        read_only_fields = [
            'id', 'commission_group', 'table', 'old_config',
            'suggested_config', 'ai_reasoning', 'created_at',
            'applied_at', 'applied_by',
        ]
