"""Helpers compartilhados da camada de integração."""
from __future__ import annotations

from django.conf import settings


def build_registration_url(token: str, request=None) -> str:
    base = getattr(settings, 'PUBLIC_APP_BASE_URL', '').rstrip('/')
    path = f'/cadastro/grupo/{token}'
    if base:
        return f'{base}{path}'
    if request:
        origin = request.build_absolute_uri('/').rstrip('/')
        return f'{origin}{path}'
    return path
