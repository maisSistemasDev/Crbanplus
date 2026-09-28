from rest_framework import serializers

from webhooks.models import WebhookDelivery, WebhookEndpoint, generate_webhook_secret


class WebhookEndpointSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source='bank.name', read_only=True)
    layout_name = serializers.CharField(source='layout.name', read_only=True)
    inbound_url = serializers.SerializerMethodField()
    delivery_count = serializers.SerializerMethodField()
    last_delivery_at = serializers.SerializerMethodField()

    class Meta:
        model = WebhookEndpoint
        fields = [
            'id', 'name', 'bank', 'bank_name', 'layout', 'layout_name',
            'items_path', 'mappings', 'is_active', 'auto_process',
            'inbound_url', 'delivery_count', 'last_delivery_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_inbound_url(self, obj):
        request = self.context.get('request')
        return obj.inbound_url(request)

    def get_delivery_count(self, obj):
        return obj.deliveries.count()

    def get_last_delivery_at(self, obj):
        last = obj.deliveries.order_by('-created_at').values_list('created_at', flat=True).first()
        return last


class WebhookEndpointCreateSerializer(serializers.ModelSerializer):
    secret_token = serializers.CharField(read_only=True)
    inbound_url = serializers.SerializerMethodField()

    class Meta:
        model = WebhookEndpoint
        fields = [
            'id', 'name', 'bank', 'layout', 'items_path', 'mappings',
            'is_active', 'auto_process', 'secret_token', 'inbound_url',
            'created_at',
        ]
        read_only_fields = ['id', 'secret_token', 'inbound_url', 'created_at']

    def get_inbound_url(self, obj):
        request = self.context.get('request')
        return obj.inbound_url(request)

    def create(self, validated_data):
        validated_data['secret_token'] = generate_webhook_secret()
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class WebhookDeliverySerializer(serializers.ModelSerializer):
    batch_id = serializers.UUIDField(source='proposal_batch_id', read_only=True)
    batch_total_rows = serializers.SerializerMethodField()

    class Meta:
        model = WebhookDelivery
        fields = [
            'id', 'status', 'items_count', 'error_message', 'source_ip',
            'batch_id', 'batch_total_rows', 'batch_created', 'created_at',
        ]

    def get_batch_total_rows(self, obj):
        if obj.proposal_batch_id:
            return obj.proposal_batch.total_rows
        return None
