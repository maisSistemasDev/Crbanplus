from rest_framework import serializers

from bank.models import Bank
from .models import BankAccess, AccessLog
from .validators import validate_bank_access_instance


class BankAccessSerializer(serializers.ModelSerializer):
    """
    Serializador para o modelo BankAccess.
    """
    bank_name = serializers.CharField(source='bank.name', read_only=True)
    bank_access_login_type = serializers.CharField(
        source='bank.access_login_type', read_only=True,
    )
    user_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = BankAccess
        fields = [
            'id', 'bank', 'bank_name', 'bank_access_login_type',
            'username', 'password', 'is_active', 'is_master',
            'notes', 'link', 'alias', 'user', 'user_name',
            'created_by', 'created_by_name',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.cpf
        return None

    def get_created_by_name(self, obj):
        if obj.created_by:
            return (
                f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
                or obj.created_by.cpf
            )
        return None

    def validate(self, attrs):
        user = attrs.get('user')
        if user is None and self.instance is not None:
            user = self.instance.user
        # Não força master no Corban: logins extras de digitador entram como equipe.

        instance = self.instance or BankAccess()
        for key, val in attrs.items():
            setattr(instance, key, val)

        try:
            validate_bank_access_instance(instance)
        except serializers.ValidationError:
            raise
        except Exception as exc:
            from django.core.exceptions import ValidationError as DjangoValidationError
            if isinstance(exc, DjangoValidationError):
                raise serializers.ValidationError(exc.messages)
            raise serializers.ValidationError(str(exc))

        return attrs

    def form_fields(self):
        """
        Retorna informações sobre os campos para construção de formulários.
        """
        return [
            {
                'name': 'bank', 'type': 'select', 'label': 'Banco', 'required': True,
                'relation': 'Bank', 'options_url': '/banks/',
            },
            {
                'name': 'user', 'type': 'select', 'label': 'Usuário', 'required': True,
                'relation': 'User', 'options_url': '/users/?page_size=500',
            },
            {'name': 'username', 'type': 'text', 'label': 'Login (e-mail ou CPF)', 'required': True},
            {'name': 'password', 'type': 'password', 'label': 'Senha', 'required': True},
            {
                'name': 'is_master', 'type': 'checkbox', 'label': 'Master (Corban)',
                'required': False, 'default': False,
                'help': 'Ligado: comissão direta (promotora). Desligado: grupos de comissionamento.',
            },
            {'name': 'notes', 'type': 'textarea', 'label': 'Observação', 'required': False},
            {'name': 'link', 'type': 'url', 'label': 'Link', 'required': False},
            {'name': 'is_active', 'type': 'checkbox', 'label': 'Ativo', 'default': True},
        ]


class AccessLogSerializer(serializers.ModelSerializer):
    """
    Serializador para o modelo AccessLog.
    """
    bank_access_username = serializers.CharField(source='bank_access.username', read_only=True)
    bank_name = serializers.CharField(source='bank_access.bank.name', read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = AccessLog
        fields = [
            'id', 'bank_access', 'bank_access_username', 'bank_name', 'user',
            'user_name', 'access_time', 'ip_address', 'user_agent', 'status',
            'details', 'data',
        ]
        read_only_fields = ['id', 'access_time']

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.cpf
        return None

    def form_fields(self):
        return [
            {'name': 'bank_access', 'type': 'select', 'label': 'Acesso ao Banco', 'required': True, 'relation': 'BankAccess'},
            {'name': 'user', 'type': 'select', 'label': 'Usuário', 'required': True, 'relation': 'User'},
            {'name': 'ip_address', 'type': 'text', 'label': 'Endereço IP', 'required': False},
            {'name': 'user_agent', 'type': 'text', 'label': 'User Agent', 'required': False},
            {'name': 'status', 'type': 'select', 'label': 'Status', 'required': True,
             'options': AccessLog._meta.get_field('status').choices},
            {'name': 'details', 'type': 'textarea', 'label': 'Detalhes', 'required': False},
            {'name': 'data', 'type': 'json', 'label': 'Dados', 'required': False},
        ]
