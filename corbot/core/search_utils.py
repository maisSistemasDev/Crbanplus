"""Filtros de busca textuais reutilizáveis nas listagens."""
import re

from django.db.models import Q, QuerySet


def _normalize_search_text(search: str) -> str:
    """Remove espaços extras e normaliza o termo de busca."""
    return ' '.join((search or '').split())


def split_filter_values(raw: str | None) -> list[str]:
    """Quebra um filtro multivalor (linhas, vírgulas ou ponto e vírgula) em itens limpos."""
    if not raw:
        return []
    return [value.strip() for value in re.split(r'[\n\r,;]+', raw) if value.strip()]


def apply_user_list_search(queryset: QuerySet, search: str) -> QuerySet:
    """
    Busca textual robusta em usuários.

    Estratégia:
      1. Busca o termo completo em qualquer campo relevante (first_name,
         last_name, cpf, email, matricula). Isso cobre o caso comum de
         sobrenome digitado dentro de first_name.
      2. Se houver múltiplas palavras, tenta também encaixar como
         first_name + last_name (normal e invertido), mas sem excluir o
         match do item 1.
      3. Dígitos no termo buscam também dentro de CPF e matrícula.
    """
    search = _normalize_search_text(search)
    if not search:
        return queryset

    parts = search.split()

    # Termo completo em qualquer campo
    base_filter = (
        Q(first_name__icontains=search)
        | Q(last_name__icontains=search)
        | Q(cpf__icontains=search)
        | Q(email__icontains=search)
        | Q(matricula__icontains=search)
    )

    digits = re.sub(r'\D', '', search)
    if digits:
        base_filter |= Q(cpf__icontains=digits)
        base_filter |= Q(matricula__icontains=digits)

    if len(parts) == 1:
        return queryset.filter(base_filter)

    # Múltiplas palavras: tenta first_name + last_name (ambas as ordens) e
    # também exige que cada palavra apareça em algum campo textual.
    structured = (
        Q(first_name__icontains=parts[0]) & Q(last_name__icontains=' '.join(parts[1:]))
    ) | (
        Q(first_name__icontains=parts[-1]) & Q(last_name__icontains=' '.join(parts[:-1]))
    )

    # Fallback: cada palavra deve aparecer em pelo menos um campo textual
    per_word = Q()
    for part in parts:
        word_filter = (
            Q(first_name__icontains=part)
            | Q(last_name__icontains=part)
            | Q(cpf__icontains=part)
            | Q(email__icontains=part)
            | Q(matricula__icontains=part)
        )
        per_word &= word_filter

    return queryset.filter(base_filter | structured | per_word)


def apply_company_list_search(queryset: QuerySet, search: str) -> QuerySet:
    """
    Busca textual robusta em empresas/corbans.

    Estratégia:
      1. Termo completo em name, trading_name, document, email, city, phone.
      2. Se houver dígitos, busca também documento somente com números.
      3. Múltiplas palavras: cada uma pode bater em qualquer campo.
    """
    search = _normalize_search_text(search)
    if not search:
        return queryset

    parts = search.split()

    base_filter = (
        Q(name__icontains=search)
        | Q(trading_name__icontains=search)
        | Q(document__icontains=search)
        | Q(email__icontains=search)
        | Q(city__icontains=search)
        | Q(phone__icontains=search)
    )

    digits = re.sub(r'\D', '', search)
    if digits:
        base_filter |= Q(document__icontains=digits)
        base_filter |= Q(phone__icontains=digits)

    if len(parts) == 1:
        return queryset.filter(base_filter)

    per_word = Q()
    for part in parts:
        word_filter = (
            Q(name__icontains=part)
            | Q(trading_name__icontains=part)
            | Q(document__icontains=part)
            | Q(email__icontains=part)
            | Q(city__icontains=part)
            | Q(phone__icontains=part)
        )
        per_word &= word_filter

    return queryset.filter(base_filter | per_word)


def paginate_queryset(request, queryset, serializer_class):
    """Paginação padrão DRF (page + page_size)."""
    from rest_framework.pagination import PageNumberPagination
    from rest_framework.response import Response

    paginator = PageNumberPagination()
    try:
        page_size = int(request.query_params.get('page_size', 10))
        paginator.page_size = min(max(page_size, 1), 500)
    except (TypeError, ValueError):
        paginator.page_size = 10
    page = paginator.paginate_queryset(queryset, request)
    serializer = serializer_class(page, many=True)
    return paginator.get_paginated_response(serializer.data)
