"""Filtros de hierarquia para leitura de Propostas/Lotes pelo Portal."""
from django.db.models import Q

from core.models import User


def proposal_queryset_for_actor(qs, actor):
    """Propostas visíveis ao usuário autenticado conforme hierarquia.

    - admin/colaborador: tudo (ou restrito à empresa, se admin de empresa específica).
    - gerente comercial: propostas dos corbans da sua carteira.
    - empresa_admin/gerente: propostas da própria empresa.
    - lider: propostas próprias e das/dos vendedores da equipe.
    - vendedor: apenas as próprias propostas.
    """
    if actor.role in (User.ADMIN, User.COLABORADOR):
        if actor.role == User.ADMIN and actor.company_id:
            return qs.filter(company=actor.company)
        return qs
    if actor.role == User.GERENTE_COMERCIAL:
        from commercial.services import team_company_ids_for
        return qs.filter(company_id__in=team_company_ids_for(actor))
    if actor.role in (User.EMPRESA_ADMIN, User.GERENTE):
        if actor.company_id:
            return qs.filter(company=actor.company)
        return qs.filter(Q(seller=actor) | Q(bank_access__user=actor))
    if actor.role == User.LIDER:
        return qs.filter(
            Q(seller=actor)
            | Q(seller__leader=actor)
            | Q(bank_access__user=actor)
            | Q(bank_access__user__leader=actor)
        )
    if actor.role == User.VENDEDOR:
        return qs.filter(Q(seller=actor) | Q(bank_access__user=actor))
    return qs.none()


def proposal_batch_queryset_for_actor(qs, actor):
    """Lotes visíveis: apenas lotes que contenham ao menos uma proposta visível ao usuário."""
    if actor.role in (User.ADMIN, User.COLABORADOR) and not (actor.role == User.ADMIN and actor.company_id):
        return qs
    from .models import Proposal
    visible_proposals = proposal_queryset_for_actor(Proposal.objects.all(), actor)
    batch_ids = visible_proposals.values_list('batch_id', flat=True).distinct()
    return qs.filter(id__in=batch_ids)
