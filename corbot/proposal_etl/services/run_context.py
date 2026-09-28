"""Contexto compartilhado durante uma execução ETL."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from proposal_etl.models import ProposalEtlFlow, ProposalEtlRun
from proposal_etl.services.auth_handler import AuthSession
from proposal_etl.services.execution_logger import ExecutionLogger


@dataclass
class EtlRunContext:
    flow: ProposalEtlFlow
    run: ProposalEtlRun | None = None
    logger: ExecutionLogger = field(default_factory=ExecutionLogger)
    auth_session: AuthSession = field(default_factory=AuthSession)
    current_node: dict | None = None

    def __post_init__(self) -> None:
        if self.run and self.logger.run is None:
            self.logger.run = self.run

    def resolve_auth(self, node_data: dict) -> tuple[str, dict]:
        """Auth do nó ou autenticação compartilhada do fluxo."""
        use_shared = node_data.get('use_shared_auth')
        if use_shared is None:
            use_shared = bool(self.flow.shared_auth_enabled)
        if self.flow.shared_auth_enabled and use_shared:
            return (
                self.flow.shared_auth_type or 'none',
                dict(self.flow.shared_auth_config or {}),
            )
        return (
            node_data.get('auth_type') or 'none',
            dict(node_data.get('auth_config') or {}),
        )

    def node_meta(self, node: dict | None = None) -> dict[str, str]:
        node = node or self.current_node or {}
        data = node.get('data') or {}
        return {
            'node_id': node.get('id', ''),
            'node_type': node.get('type', ''),
            'node_label': data.get('label') or node.get('type', ''),
        }

    def log_step_start(self, node: dict, params: dict | None = None) -> None:
        meta = self.node_meta(node)
        self.logger.log(
            level='info',
            message='Iniciando etapa',
            params=params,
            **meta,
        )

    def log_step_success(self, node: dict, result: dict) -> None:
        meta = self.node_meta(node)
        self.logger.log(
            level='success',
            message='Etapa concluída',
            result=result,
            **meta,
        )

    def log_step_error(self, node: dict, error: str) -> None:
        meta = self.node_meta(node)
        self.logger.log(
            level='error',
            message=error,
            **meta,
        )
