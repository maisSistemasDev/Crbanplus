"""Utilitários de idempotência para integrações."""
from __future__ import annotations

from typing import Any

from rest_framework.response import Response

from core.models import APIKey, IntegrationIdempotencyRecord


def resolve_idempotency(
    api_key: APIKey,
    idempotency_key: str | None,
    external_id: str | None,
    resource_type: str,
) -> Response | None:
    """
    Retorna Response cacheada se a chave já foi processada.
    A chave efetiva é Idempotency-Key ou external_id.
    """
    key = (idempotency_key or '').strip()
    if not key and external_id:
        key = f'{resource_type}:{external_id}'
    if not key:
        return None

    record = IntegrationIdempotencyRecord.objects.filter(
        api_key=api_key,
        idempotency_key=key,
    ).first()
    if not record:
        return None
    return Response(record.response_body, status=record.response_status)


def store_idempotency(
    api_key: APIKey,
    idempotency_key: str | None,
    external_id: str | None,
    resource_type: str,
    resource_id: str,
    response_status: int,
    response_body: dict[str, Any],
) -> None:
    key = (idempotency_key or '').strip()
    if not key and external_id:
        key = f'{resource_type}:{external_id}'
    if not key:
        return

    IntegrationIdempotencyRecord.objects.update_or_create(
        api_key=api_key,
        idempotency_key=key,
        defaults={
            'resource_type': resource_type,
            'resource_id': str(resource_id),
            'response_status': response_status,
            'response_body': response_body,
        },
    )
