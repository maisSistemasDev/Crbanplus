from rest_framework import status
from rest_framework.response import Response

from core.base_views import BaseApiView
from core.permissions import IsAdmin
from proposals.models import Layout

from .models import ProposalEtlFlow, ProposalEtlRun, ProposalEtlBankProfile
from .serializers import (
    ProposalEtlFlowSerializer,
    ProposalEtlRunSerializer,
    ProposalEtlBankProfileSerializer,
)
from .services.flow_executor import FlowExecutor, FlowExecutionError
from .services.flow_generator import generate_flow_from_documentation
from .services.bank_profile import apply_settings_to_flow, extract_settings_from_flow


from .meta import AUTH_TYPES, NODE_TYPES, PAGINATION_MODES, DATE_EXPRESSION_HELP, FIELD_TRANSFORMS, CONDITION_OPERATORS


class ProposalEtlFlowListCreateView(BaseApiView):
    permission_classes = [IsAdmin]

    def get(self, request):
        flows = ProposalEtlFlow.objects.select_related('bank').all()
        serializer = ProposalEtlFlowSerializer(flows, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ProposalEtlFlowSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        flow = serializer.save()
        return Response(
            ProposalEtlFlowSerializer(flow).data,
            status=status.HTTP_201_CREATED,
        )


class ProposalEtlFlowDetailView(BaseApiView):
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        return ProposalEtlFlow.objects.select_related('bank').get(pk=pk)

    def get(self, request, pk):
        flow = self.get_object(pk)
        return Response(ProposalEtlFlowSerializer(flow).data)

    def patch(self, request, pk):
        flow = self.get_object(pk)
        serializer = ProposalEtlFlowSerializer(
            flow,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        flow = self.get_object(pk)
        flow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProposalEtlTestNodeView(BaseApiView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        flow = ProposalEtlFlow.objects.get(pk=pk)
        node_id = request.data.get('node_id')
        if not node_id:
            return Response({'detail': 'node_id é obrigatório.'}, status=400)

        executor = FlowExecutor(flow)
        try:
            outputs = executor.execute(
                stop_at=node_id,
                skip_create_batch=True,
                limit_items=3,
            )
            return Response({
                'node_id': node_id,
                'outputs': outputs,
                'execution_log': executor.execution_log,
            })
        except FlowExecutionError as exc:
            return Response(
                {
                    'detail': str(exc),
                    'node_id': exc.node_id,
                    'execution_log': executor.execution_log,
                },
                status=400,
            )


class ProposalEtlRunView(BaseApiView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        from django.conf import settings as django_settings

        from proposal_etl.tasks import execute_etl_run, run_proposal_etl_flow

        flow = ProposalEtlFlow.objects.get(pk=pk)
        running = ProposalEtlRun.objects.filter(
            flow=flow,
            status=ProposalEtlRun.STATUS_RUNNING,
        ).exists()
        if running:
            return Response(
                {'detail': 'Já existe uma execução em andamento para este fluxo.'},
                status=409,
            )

        run = ProposalEtlRun.objects.create(
            flow=flow,
            status=ProposalEtlRun.STATUS_RUNNING,
            trigger_source='manual',
        )

        run_id = str(run.id)
        if getattr(django_settings, 'CELERY_TASK_ALWAYS_EAGER', False):
            import threading

            threading.Thread(
                target=execute_etl_run,
                args=(run_id,),
                daemon=True,
            ).start()
        else:
            run_proposal_etl_flow.delay(run_id)

        return Response(
            {
                'run': ProposalEtlRunSerializer(run).data,
                'status': 'queued',
                'message': 'Execução iniciada em background. Acompanhe o status pela API.',
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ProposalEtlRunDetailView(BaseApiView):
    permission_classes = [IsAdmin]

    def get(self, request, run_id):
        run = ProposalEtlRun.objects.select_related('flow', 'proposal_batch').get(pk=run_id)
        return Response(ProposalEtlRunSerializer(run).data)


class ProposalEtlRunListView(BaseApiView):
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        runs = ProposalEtlRun.objects.filter(flow_id=pk).select_related('proposal_batch')
        return Response(ProposalEtlRunSerializer(runs, many=True).data)


class ProposalEtlMetaView(BaseApiView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({
            'auth_types': AUTH_TYPES,
            'node_types': NODE_TYPES,
            'pagination_modes': PAGINATION_MODES,
            'field_transforms': FIELD_TRANSFORMS,
            'condition_operators': CONDITION_OPERATORS,
            'date_expression_help': DATE_EXPRESSION_HELP,
        })


class ProposalEtlLayoutFieldsView(BaseApiView):
    permission_classes = [IsAdmin]

    def get(self, request):
        layout_id = request.query_params.get('layout_id')
        if not layout_id:
            return Response({'detail': 'layout_id é obrigatório.'}, status=400)
        layout = Layout.objects.prefetch_related('map_fields').get(id=layout_id)
        fields = [
            {'name': f.name, 'label': f.header_name or f.name, 'data_type': f.data_type}
            for f in layout.map_fields.all().order_by('index')
        ]
        return Response({'layout_id': str(layout.id), 'fields': fields})


class ProposalEtlBankProfileView(BaseApiView):
    """Perfil ETL reutilizável por banco."""
    permission_classes = [IsAdmin]

    def get(self, request, bank_id):
        profile, _ = ProposalEtlBankProfile.objects.get_or_create(
            bank_id=bank_id,
            defaults={'settings': {}},
        )
        return Response(ProposalEtlBankProfileSerializer(profile).data)

    def put(self, request, bank_id):
        profile, _ = ProposalEtlBankProfile.objects.get_or_create(
            bank_id=bank_id,
            defaults={'settings': {}},
        )
        serializer = ProposalEtlBankProfileSerializer(
            profile,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def post(self, request, bank_id):
        """Aplica perfil salvo a um fluxo ou extrai settings do fluxo atual."""
        action = request.data.get('action')
        flow_id = request.data.get('flow_id')

        if action == 'extract_from_flow':
            if not flow_id:
                return Response({'detail': 'flow_id é obrigatório.'}, status=400)
            flow = ProposalEtlFlow.objects.get(pk=flow_id)
            settings = extract_settings_from_flow(flow.flow_definition or {})
            profile, _ = ProposalEtlBankProfile.objects.get_or_create(
                bank_id=bank_id,
                defaults={'settings': {}},
            )
            profile.settings = settings
            if request.data.get('notes') is not None:
                profile.notes = request.data.get('notes') or ''
            profile.save()
            return Response(ProposalEtlBankProfileSerializer(profile).data)

        if action == 'apply_to_flow':
            if not flow_id:
                return Response({'detail': 'flow_id é obrigatório.'}, status=400)
            flow = ProposalEtlFlow.objects.get(pk=flow_id)
            profile = ProposalEtlBankProfile.objects.filter(bank_id=bank_id).first()
            if not profile or not profile.settings:
                return Response({'detail': 'Nenhum perfil salvo para este banco.'}, status=404)
            flow.flow_definition = apply_settings_to_flow(flow.flow_definition or {}, profile.settings)
            flow.bank_id = bank_id
            flow.save(update_fields=['flow_definition', 'bank', 'updated_at'])
            return Response(ProposalEtlFlowSerializer(flow).data)

        return Response({'detail': 'action inválida. Use extract_from_flow ou apply_to_flow.'}, status=400)


class ProposalEtlGenerateFromDocView(BaseApiView):
    """Gera rascunho de fluxo ETL a partir de documentação/cURL da API."""
    permission_classes = [IsAdmin]

    def post(self, request):
        documentation = (request.data.get('documentation') or '').strip()
        if not documentation:
            return Response({'detail': 'Cole a documentação ou exemplos cURL.'}, status=400)

        layout_id = request.data.get('layout_id') or None
        bank_id = request.data.get('bank') or None
        name_override = (request.data.get('name') or '').strip()

        layout_fields: list[dict] = []
        if layout_id:
            layout = Layout.objects.prefetch_related('map_fields').get(id=layout_id)
            layout_fields = [
                {'name': f.name, 'label': f.header_name or f.name, 'data_type': f.data_type}
                for f in layout.map_fields.all().order_by('index')
            ]

        try:
            generated = generate_flow_from_documentation(
                documentation,
                layout_id=str(layout_id) if layout_id else None,
                layout_fields=layout_fields,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=400)
        except Layout.DoesNotExist:
            return Response({'detail': 'Layout não encontrado.'}, status=404)
        except Exception as exc:
            return Response({'detail': f'Erro ao gerar fluxo: {exc}'}, status=500)

        flow = ProposalEtlFlow.objects.create(
            name=name_override or generated['name'],
            bank_id=bank_id,
            flow_definition=generated['flow_definition'],
            created_by=request.user if request.user.is_authenticated else None,
        )

        data = ProposalEtlFlowSerializer(flow).data
        data['warnings'] = generated['warnings']
        data['source'] = generated['source']
        return Response(data, status=status.HTTP_201_CREATED)
