from datetime import datetime

from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response

from core.base_views import BaseApiView
from core.models import User
from payments.models import Commission, UserDebit
from proposals.models import Proposal
from proposals.services import proposal_queryset_for_actor

MONTH_LABELS = [
    'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
    'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez',
]


def _aware(dt: datetime) -> datetime:
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _month_start(year: int, month: int) -> datetime:
    return _aware(datetime(year, month, 1, 0, 0, 0))


def _next_month_start(year: int, month: int) -> datetime:
    if month == 12:
        return _month_start(year + 1, 1)
    return _month_start(year, month + 1)


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    absolute = year * 12 + (month - 1) + delta
    return absolute // 12, absolute % 12 + 1


def commission_queryset_for_actor(actor):
    qs = Commission.objects.all()
    if actor.role == User.VENDEDOR:
        return qs.filter(user=actor)
    if actor.role == User.LIDER:
        return qs.filter(Q(user=actor) | Q(user__leader=actor))
    if actor.role in (User.EMPRESA_ADMIN, User.GERENTE):
        if actor.company_id:
            return qs.filter(
                Q(company=actor.company)
                | Q(user__company=actor.company)
                | Q(proposal__company=actor.company)
            ).distinct()
        return qs.filter(user=actor)
    if actor.role == User.GERENTE_COMERCIAL:
        from commercial.services import team_company_ids_for
        company_ids = team_company_ids_for(actor)
        return qs.filter(
            Q(company_id__in=company_ids)
            | Q(user__company_id__in=company_ids)
            | Q(proposal__company_id__in=company_ids)
        ).distinct()
    if actor.role in (User.ADMIN, User.COLABORADOR):
        if actor.role == User.ADMIN and actor.company_id:
            return qs.filter(proposal__company=actor.company)
        return qs
    return qs.none()


def debit_queryset_for_actor(actor):
    qs = UserDebit.objects.filter(is_active=True)
    if actor.role == User.VENDEDOR:
        return qs.filter(user=actor)
    if actor.role == User.LIDER:
        return qs.filter(Q(user=actor) | Q(user__leader=actor))
    if actor.role in (User.EMPRESA_ADMIN, User.GERENTE):
        if actor.company_id:
            return qs.filter(Q(user__company=actor.company) | Q(company=actor.company))
        return qs.filter(user=actor)
    if actor.role == User.GERENTE_COMERCIAL:
        from commercial.services import team_company_ids_for
        company_ids = team_company_ids_for(actor)
        return qs.filter(Q(user__company_id__in=company_ids) | Q(company_id__in=company_ids))
    if actor.role in (User.ADMIN, User.COLABORADOR):
        if actor.role == User.ADMIN and actor.company_id:
            return qs.filter(Q(user__company=actor.company) | Q(company=actor.company))
        return qs
    return qs.none()


class PortalDashboardView(BaseApiView):
    """Indicadores do dashboard do portal (produção e comissões da rede do usuário)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        actor = request.user
        today = timezone.localdate()
        month_begin = _month_start(today.year, today.month)
        month_end = _next_month_start(today.year, today.month)

        proposals = proposal_queryset_for_actor(Proposal.objects.all(), actor)
        month_proposals = proposals.filter(created_at__gte=month_begin, created_at__lt=month_end)
        month_count = month_proposals.count()
        averbadas_value = month_proposals.aggregate(total=Sum('amount'))['total'] or 0

        commissions = commission_queryset_for_actor(actor)
        predicted = commissions.filter(
            release_status__in=[
                Commission.NOT_RELEASED,
                Commission.WITHDRAW_AVAILABLE,
                Commission.PENDING_MANUAL_PAYMENT,
            ]
        ).aggregate(total=Sum('value'))['total'] or 0

        advances = debit_queryset_for_actor(actor).aggregate(
            total=Sum('remaining_amount')
        )['total'] or 0

        paid_commissions = list(
            commissions.filter(release_status=Commission.PAID).only('value', 'paid_at', 'updated_at')
        )
        received_commission = sum(float(commission.value or 0) for commission in paid_commissions)

        received_by_month = []
        for offset in range(4, -1, -1):
            year, month = _shift_month(today.year, today.month, -offset)
            begin = _month_start(year, month)
            end = _next_month_start(year, month)
            total = 0
            for commission in paid_commissions:
                ref = commission.paid_at or commission.updated_at
                if ref is None:
                    continue
                if timezone.is_naive(ref):
                    ref = _aware(ref)
                if begin <= ref < end:
                    total += float(commission.value or 0)
            received_by_month.append({
                'year': year,
                'month': month,
                'label': MONTH_LABELS[month - 1],
                'value': round(total, 2),
            })

        return Response({
            'generated_at': timezone.now().isoformat(),
            'month_proposals_count': month_count,
            'averbadas_value': float(averbadas_value),
            'analysis_value': 0,
            'predicted_commission': float(predicted),
            'received_commission': round(received_commission, 2),
            'advances_value': float(advances),
            'physical_pending_count': 0,
            'open_tickets_count': 0,
            'received_by_month': received_by_month,
        })
