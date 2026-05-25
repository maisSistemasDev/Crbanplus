from rest_framework import serializers
from .models import Bank, Agreement, Table, CommissionRange


class BankSerializer(serializers.ModelSerializer):
    """
    Serializador para o modelo Bank.
    """
    class Meta:
        model = Bank
        fields = ['id', 'name', 'logo', 'website', 'is_active']
        read_only_fields = ['id']
        
    def form_fields(self):
        """
        Retorna informações sobre os campos para construção de formulários no NextJS.
        """
        return [
            {'name': 'name', 'type': 'text', 'label': 'Nome', 'required': True},
            {'name': 'logo', 'type': 'file', 'label': 'Logo', 'required': False, 'accept': 'image/*'},
            {'name': 'website', 'type': 'url', 'label': 'Website', 'required': False},
            {'name': 'is_active', 'type': 'checkbox', 'label': 'Ativo', 'default': True}
        ]

class AgreementSerializer(serializers.ModelSerializer):
    """
    Serializador para o modelo Agreement.
    """
    class Meta:
        model = Agreement
        fields = ['id', 'name', 'description', 'is_active', 'alias']
        read_only_fields = ['id']
        
    def form_fields(self):
        """
        Retorna informações sobre os campos para construção de formulários no NextJS.
        """
        return [
            {'name': 'name', 'type': 'text', 'label': 'Nome', 'required': True},
            {'name': 'description', 'type': 'textarea', 'label': 'Descrição', 'required': False},
            {'name': 'is_active', 'type': 'checkbox', 'label': 'Ativo', 'default': True}
        ]


class CommissionRangeSerializer(serializers.ModelSerializer):
    """
    Serializador para faixas de comissionamento de uma tabela.
    """
    class Meta:
        model = CommissionRange
        fields = ['id', 'min_value', 'max_value', 'commission_rate']
        read_only_fields = ['id']


class TableSerializer(serializers.ModelSerializer):
    """
    Serializador para o modelo Table.
    """
    bank_name = serializers.CharField(source='bank.name', read_only=True)
    agreement_name = serializers.CharField(source='agreement.name', read_only=True)
    commission_ranges = CommissionRangeSerializer(many=True, required=False)

    class Meta:
        model = Table
        fields = [
            'id', 'bank', 'bank_name', 'agreement', 'agreement_name',
            'name_in_bank', 'vigency_date', 'is_active', 'alias',
            'commission_ranges',
            # manter campos legados nullable para não quebrar código existente
            'min_value', 'max_value', 'commission_rate',
        ]

    def create(self, validated_data):
        ranges_data = validated_data.pop('commission_ranges', [])
        table = Table.objects.create(**validated_data)
        for r in ranges_data:
            CommissionRange.objects.create(table=table, **r)
        return table

    def update(self, instance, validated_data):
        ranges_data = validated_data.pop('commission_ranges', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if ranges_data is not None:
            instance.commission_ranges.all().delete()
            for r in ranges_data:
                CommissionRange.objects.create(table=instance, **r)
        return instance

    def options_agreemants(self):
        return [{'value': str(a.id), 'label': a.name} for a in Agreement.objects.all()]

    def options_banks(self):
        return [{'value': str(b.id), 'label': b.name} for b in Bank.objects.all()]

    def form_fields(self):
        return [
            {'name': 'bank', 'type': 'select', 'label': 'Banco', 'required': True, 'options': self.options_banks()},
            {'name': 'agreement', 'type': 'select', 'label': 'Convênio', 'required': True, 'options': self.options_agreemants()},
            {'name': 'name_in_bank', 'type': 'text', 'label': 'Nome no Banco', 'required': False},
            {'name': 'vigency_date', 'type': 'date', 'label': 'Data de Vigência', 'required': True},
            {'name': 'is_active', 'type': 'checkbox', 'label': 'Ativo', 'default': True},
            {'name': 'commission_ranges', 'type': 'ranges', 'label': 'Faixas de Comissionamento', 'required': True},
        ]