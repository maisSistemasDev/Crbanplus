from rest_framework import serializers

from core.models import User
from .models import CommercialTeamMember


class CommercialManagerSerializer(serializers.ModelSerializer):
    """Serializador de leitura para o Gerente Comercial."""
    team_size = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'cpf', 'email', 'first_name', 'last_name', 'is_active',
            'inactivated_at', 'inactivation_reason', 'team_size',
        ]
        read_only_fields = fields

    def get_team_size(self, obj):
        return obj.commercial_team_companies.count()


class CommercialManagerCreateSerializer(serializers.ModelSerializer):
    """Serializador para cadastro de um novo Gerente Comercial."""
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['id', 'cpf', 'email', 'first_name', 'last_name', 'password']
        read_only_fields = ['id']

    def create(self, validated_data):
        validated_data['role'] = User.GERENTE_COMERCIAL
        return User.objects.create_user(**validated_data)


class CommercialTeamMemberSerializer(serializers.ModelSerializer):
    """Serializador para os membros (corbans) da equipe de um gerente comercial."""
    company_name = serializers.CharField(source='company.name', read_only=True)
    manager_name = serializers.SerializerMethodField()
    added_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CommercialTeamMember
        fields = [
            'id', 'manager', 'manager_name', 'company', 'company_name',
            'added_by', 'added_by_name', 'created_at',
        ]
        read_only_fields = ['id', 'added_by', 'created_at']

    def get_manager_name(self, obj):
        return f'{obj.manager.first_name} {obj.manager.last_name}'.strip() or obj.manager.cpf

    def get_added_by_name(self, obj):
        if obj.added_by:
            return f'{obj.added_by.first_name} {obj.added_by.last_name}'.strip() or obj.added_by.cpf
        return None

    def validate_manager(self, value):
        if value.role != User.GERENTE_COMERCIAL:
            raise serializers.ValidationError('O usuário informado não é um Gerente Comercial.')
        return value
