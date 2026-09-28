from rest_framework import serializers

from .models import ProposalEtlFlow, ProposalEtlRun, ProposalEtlBankProfile, default_flow_definition


class ProposalEtlFlowSerializer(serializers.ModelSerializer):
    last_run_status = serializers.SerializerMethodField()
    last_batch_id = serializers.SerializerMethodField()
    bank_name = serializers.CharField(source='bank.name', read_only=True)

    class Meta:
        model = ProposalEtlFlow
        fields = [
            'id', 'name', 'bank', 'bank_name', 'is_active', 'flow_definition',
            'shared_auth_enabled', 'shared_auth_type', 'shared_auth_config',
            'created_by', 'created_at', 'updated_at',
            'last_run_status', 'last_batch_id',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_last_run_status(self, obj):
        last = obj.runs.order_by('-started_at').first()
        return last.status if last else None

    def get_last_batch_id(self, obj):
        last = obj.runs.filter(proposal_batch__isnull=False).order_by('-started_at').first()
        return str(last.proposal_batch_id) if last and last.proposal_batch_id else None

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        if not validated_data.get('flow_definition'):
            validated_data['flow_definition'] = default_flow_definition()
        return super().create(validated_data)


class ProposalEtlRunSerializer(serializers.ModelSerializer):
    flow_name = serializers.CharField(source='flow.name', read_only=True)

    class Meta:
        model = ProposalEtlRun
        fields = [
            'id', 'flow', 'flow_name', 'proposal_batch', 'status',
            'started_at', 'finished_at', 'fetched_count', 'rows_written',
            'node_outputs', 'execution_log', 'trigger_source',
            'error_message', 'error_node_id', 'celery_task_id',
        ]
        read_only_fields = fields


class ProposalEtlBankProfileSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source='bank.name', read_only=True)

    class Meta:
        model = ProposalEtlBankProfile
        fields = ['id', 'bank', 'bank_name', 'settings', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
