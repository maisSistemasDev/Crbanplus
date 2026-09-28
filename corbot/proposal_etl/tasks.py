"""Tasks Celery para execução assíncrona de fluxos ETL."""
import logging

from celery import shared_task
from django.utils import timezone

from proposal_etl.models import ProposalEtlFlow, ProposalEtlRun
from proposal_etl.services.flow_executor import FlowExecutor, FlowExecutionError
from proposal_etl.services.schedule_utils import (
    cron_matches_now,
    get_schedule_from_flow,
    human_schedule_to_cron,
)

logger = logging.getLogger(__name__)


def execute_etl_run(run_id: str) -> dict:
    """Executa um run ETL (usado pela task Celery e fallback em thread)."""
    run = ProposalEtlRun.objects.select_related('flow').get(pk=run_id)
    flow = run.flow
    executor = FlowExecutor(flow, etl_run=run)
    try:
        completed = executor.run_full()
        logger.info('ETL run %s concluído: %s itens', run_id, completed.fetched_count)
        return {
            'run_id': str(completed.id),
            'status': completed.status,
            'proposal_batch_id': str(completed.proposal_batch_id) if completed.proposal_batch_id else None,
            'fetched_count': completed.fetched_count,
        }
    except FlowExecutionError as exc:
        run.refresh_from_db()
        logger.warning('ETL run %s falhou no nó %s: %s', run_id, exc.node_id, exc)
        return {
            'run_id': str(run.id),
            'status': run.status,
            'error': str(exc),
            'node_id': exc.node_id,
        }
    except Exception as exc:
        run.status = ProposalEtlRun.STATUS_FAILED
        run.error_message = str(exc)
        run.finished_at = timezone.now()
        run.save(update_fields=['status', 'error_message', 'finished_at', 'updated_at'])
        logger.exception('ETL run %s erro inesperado', run_id)
        return {'run_id': str(run.id), 'status': 'failed', 'error': str(exc)}


@shared_task(bind=True, max_retries=0)
def run_proposal_etl_flow(self, run_id: str):
    """Executa um fluxo ETL em background (evita timeout HTTP 524)."""
    run = ProposalEtlRun.objects.filter(pk=run_id).first()
    if run:
        run.celery_task_id = self.request.id
        run.status = ProposalEtlRun.STATUS_RUNNING
        run.save(update_fields=['celery_task_id', 'status', 'updated_at'])
    return execute_etl_run(run_id)


@shared_task
def check_scheduled_etl_flows():
    """Dispara fluxos ETL ativos cujo cron coincide com o minuto atual."""
    now = timezone.now()
    triggered = 0

    for flow in ProposalEtlFlow.objects.filter(is_active=True):
        schedule_data = get_schedule_from_flow(flow.flow_definition or {})
        if not schedule_data:
            continue

        cron = human_schedule_to_cron(schedule_data)
        tz_name = (schedule_data.get('timezone') or 'America/Sao_Paulo').strip()
        if not cron_matches_now(cron, tz_name, now=now):
            continue

        running = ProposalEtlRun.objects.filter(
            flow=flow,
            status=ProposalEtlRun.STATUS_RUNNING,
        ).exists()
        if running:
            logger.info('ETL agendado %s ignorado — execução em andamento', flow.id)
            continue

        run = ProposalEtlRun.objects.create(
            flow=flow,
            status=ProposalEtlRun.STATUS_RUNNING,
            trigger_source='schedule',
        )
        run_proposal_etl_flow.delay(str(run.id))
        triggered += 1
        logger.info('ETL agendado disparado: fluxo %s run %s', flow.id, run.id)

    return {'triggered': triggered}
