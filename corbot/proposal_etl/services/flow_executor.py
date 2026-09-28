"""Executa grafo de fluxo ETL."""
from collections import deque
from typing import Any

from django.conf import settings
from django.utils import timezone

from proposal_etl.models import ProposalEtlFlow, ProposalEtlRun
from proposal_etl.services.execution_logger import sanitize_params
from proposal_etl.services.node_handlers import NODE_HANDLERS
from proposal_etl.services.run_context import EtlRunContext
from proposal_etl.services.http_helpers import prepare_url_and_query


class FlowExecutionError(Exception):
    def __init__(self, node_id: str, message: str):
        self.node_id = node_id
        super().__init__(message)


def _cap_items_result(result: dict, max_items: int) -> dict:
    items = result.get('items')
    if not isinstance(items, list) or len(items) <= max_items:
        return result
    capped = dict(result)
    capped['_items_original_count'] = len(items)
    capped['_items_capped'] = True
    capped['_items_max'] = max_items
    capped['items'] = items[:max_items]
    capped['count'] = len(capped['items'])
    return capped


def _node_step_params(node: dict, ctx: EtlRunContext) -> dict:
    data = node.get('data') or {}
    node_type = node.get('type', '')
    params: dict[str, Any] = {'label': data.get('label')}

    if node_type in ('http_request', 'paginate_http', 'fetch_item_details'):
        auth_type, _ = ctx.resolve_auth(data)
        params.update({
            'auth_type': auth_type,
            'use_shared_auth': ctx.flow.shared_auth_enabled and (
                data.get('use_shared_auth') is not False
            ),
            'method': data.get('method', 'GET'),
        })
        if node_type == 'paginate_http':
            fmt = data.get('date_format') or '%Y-%m-%d'
            tz = data.get('date_timezone') or 'America/Sao_Paulo'
            resolved_url, resolved_query = prepare_url_and_query(
                data.get('url') or '',
                data.get('query_params') or {},
                date_format=fmt,
                date_timezone=tz,
            )
            params.update({
                'url': resolved_url,
                'pagination_mode': data.get('pagination_mode'),
                'items_path': data.get('items_path'),
                'query_params': resolved_query,
                'page_start': data.get('page_start'),
                'page_param': data.get('page_param'),
                'page_size_param': data.get('page_size_param'),
            })
        elif node_type == 'http_request':
            fmt = data.get('date_format') or '%Y-%m-%d'
            tz = data.get('date_timezone') or 'America/Sao_Paulo'
            resolved_url, resolved_query = prepare_url_and_query(
                data.get('url') or '',
                data.get('query_params') or {},
                date_format=fmt,
                date_timezone=tz,
            )
            params.update({
                'url': resolved_url,
                'query_params': resolved_query,
            })
        elif node_type == 'fetch_item_details':
            params.update({
                'url_template': data.get('url_template'),
                'id_field': data.get('id_field'),
            })
    elif node_type == 'schedule_trigger':
        params.update({
            'schedule_mode': data.get('schedule_mode'),
            'schedule_time': data.get('schedule_time'),
            'timezone': data.get('timezone'),
            'cron': data.get('cron'),
        })
    elif node_type == 'extract_items':
        params['items_path'] = data.get('items_path')
    elif node_type == 'map_fields':
        params['mappings_count'] = len(data.get('mappings') or [])
    elif node_type == 'create_batch':
        params['layout_id'] = data.get('layout_id')

    return sanitize_params(params)


class FlowExecutor:
    def __init__(self, flow: ProposalEtlFlow, etl_run: ProposalEtlRun | None = None):
        self.flow = flow
        self.etl_run = etl_run
        definition = flow.flow_definition or {}
        self.nodes = {n['id']: n for n in definition.get('nodes', [])}
        self.edges = definition.get('edges', [])
        self.ctx = EtlRunContext(flow=flow, run=etl_run)

    def _build_order(self, stop_at: str | None = None) -> list[str]:
        incoming = {nid: 0 for nid in self.nodes}
        adjacency: dict[str, list[str]] = {nid: [] for nid in self.nodes}
        for edge in self.edges:
            src, tgt = edge.get('source'), edge.get('target')
            if src in adjacency and tgt in incoming:
                adjacency[src].append(tgt)
                incoming[tgt] += 1

        queue = deque([nid for nid, count in incoming.items() if count == 0])
        order = []
        while queue:
            node_id = queue.popleft()
            order.append(node_id)
            if stop_at and node_id == stop_at:
                break
            for tgt in adjacency.get(node_id, []):
                incoming[tgt] -= 1
                if incoming[tgt] == 0:
                    queue.append(tgt)

        if stop_at and stop_at not in order:
            order.append(stop_at)
        return order

    def _get_input(self, node_id: str, outputs: dict[str, Any]) -> dict:
        for edge in self.edges:
            if edge.get('target') == node_id:
                src = edge.get('source')
                if src in outputs:
                    return outputs[src]
        return {}

    def execute(
        self,
        *,
        stop_at: str | None = None,
        skip_create_batch: bool = False,
        limit_items: int | None = None,
    ) -> dict[str, Any]:
        if self.flow.shared_auth_enabled:
            self.ctx.logger.log(
                level='info',
                message='Autenticação compartilhada ativa — sessão reutilizada entre nós HTTP',
                params=sanitize_params({
                    'auth_type': self.flow.shared_auth_type,
                }),
            )

        order = self._build_order(stop_at=stop_at)
        outputs: dict[str, Any] = {}
        max_items_full = getattr(settings, 'ETL_MAX_ITEMS_PER_RUN', 2000)

        for node_id in order:
            node = self.nodes.get(node_id)
            if not node:
                continue
            node_type = node.get('type')
            if skip_create_batch and node_type == 'create_batch':
                continue

            handler = NODE_HANDLERS.get(node_type)
            if not handler:
                raise FlowExecutionError(node_id, f'Tipo de nó desconhecido: {node_type}')

            self.ctx.current_node = node
            input_data = self._get_input(node_id, outputs)
            data = node.get('data') or {}

            self.ctx.log_step_start(node, _node_step_params(node, self.ctx))

            try:
                if node_type == 'create_batch':
                    result = handler(data, input_data, etl_run=self.etl_run, ctx=self.ctx)
                elif node_type == 'paginate_http':
                    result = handler(
                        data,
                        input_data,
                        max_pages_override=1 if limit_items else None,
                        ctx=self.ctx,
                    )
                elif node_type == 'fetch_item_details':
                    result = handler(data, input_data, limit_items=limit_items, ctx=self.ctx)
                else:
                    result = handler(data, input_data, ctx=self.ctx)
            except Exception as exc:
                self.ctx.log_step_error(node, str(exc))
                raise FlowExecutionError(node_id, str(exc)) from exc

            if limit_items and node_type == 'paginate_http' and isinstance(result.get('items'), list):
                result['items'] = result['items'][:limit_items]
                result['count'] = len(result['items'])

            if limit_items and node_type == 'extract_items' and isinstance(result.get('items'), list):
                result['items'] = result['items'][:limit_items]
                result['count'] = len(result['items'])
            if limit_items and node_type == 'map_fields' and isinstance(result.get('rows'), list):
                result['rows'] = result['rows'][:limit_items]
                result['count'] = len(result['rows'])

            if (
                limit_items is None
                and max_items_full
                and node_type in ('paginate_http', 'extract_items')
                and isinstance(result.get('items'), list)
            ):
                result = _cap_items_result(result, max_items_full)

            outputs[node_id] = result
            self.ctx.log_step_success(node, result)

        return outputs

    @property
    def execution_log(self) -> list[dict]:
        return self.ctx.logger.as_list()

    def run_full(self) -> ProposalEtlRun:
        run = self.etl_run or ProposalEtlRun.objects.create(
            flow=self.flow,
            status=ProposalEtlRun.STATUS_RUNNING,
        )
        self.etl_run = run
        self.ctx.run = run
        self.ctx.logger.run = run
        try:
            outputs = self.execute()
            run.node_outputs = _truncate_outputs(outputs)
            batch_id = None
            for out in outputs.values():
                if out.get('proposal_batch_id'):
                    batch_id = out['proposal_batch_id']
                    run.rows_written = out.get('total_rows', 0)
            if batch_id:
                from proposals.models import ProposalBatch
                run.proposal_batch = ProposalBatch.objects.get(pk=batch_id)
            for out in outputs.values():
                if out.get('count'):
                    run.fetched_count = max(run.fetched_count, out['count'])
                elif out.get('pages_fetched'):
                    run.fetched_count = max(run.fetched_count, out.get('count', 0))
            run.status = ProposalEtlRun.STATUS_SUCCESS
            run.finished_at = timezone.now()
            run.execution_log = self.ctx.logger.as_list()
            run.save()
            return run
        except FlowExecutionError as exc:
            run.status = ProposalEtlRun.STATUS_FAILED
            run.error_node_id = exc.node_id
            run.error_message = str(exc)
            run.finished_at = timezone.now()
            run.execution_log = self.ctx.logger.as_list()
            run.save()
            raise


def _truncate_outputs(outputs: dict, max_items: int = 3) -> dict:
    truncated = {}
    for node_id, out in outputs.items():
        copy = dict(out)
        if isinstance(copy.get('items'), list):
            copy['items'] = copy['items'][:max_items]
        if isinstance(copy.get('rows'), list):
            copy['rows'] = copy['rows'][:max_items]
        if isinstance(copy.get('body'), dict) and len(str(copy['body'])) > 8000:
            copy['body'] = {'truncated': True, 'preview': str(copy['body'])[:2000]}
        truncated[node_id] = copy
    return truncated
