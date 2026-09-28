from datetime import date, timedelta

from django.db import models as django_models
from django.db.models import Count, Sum
from django.db.models.functions import TruncDay, TruncMonth
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import permissions, status
from rest_framework.response import Response

from core.base_views import BaseApiView
from core.exceptions import format_serializer_errors
from core.models import User
from core.permissions import IsAdmin
from core.search_utils import paginate_queryset
from proposals.models import Proposal

from .models import CommercialTeamMember
from .serializers import (
    CommercialManagerSerializer,
    CommercialManagerCreateSerializer,
    CommercialTeamMemberSerializer,
)
from .services import clear_manager_team, team_company_ids_for


class IsAdminOrHasCommercialPermission(permissions.BasePermission):
    """Admin da promotora, ou colaborador com a permissão 'manage_commercial_teams'."""
    required_permission = 'manage_commercial_teams'

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.role == User.ADMIN and user.company is None:
            return True
        if user.role == User.COLABORADOR and user.company is None:
            return user.has_permission(self.required_permission)
        return False


def _agg(qs):
    totals = qs.aggregate(total_amount=Sum('amount'), total_count=Count('id'))
    return {
        'amount': str(totals['total_amount'] or 0),
        'count': totals['total_count'] or 0,
    }


def _company_ranking(qs):
    rows = (
        qs.values('company_id', 'company__name')
        .annotate(total_amount=Sum('amount'), total_count=Count('id'))
        .order_by('-total_amount')
    )
    return [
        {
            'company_id': str(item['company_id']),
            'company_name': item['company__name'],
            'total_amount': str(item['total_amount'] or 0),
            'total_count': item['total_count'],
        }
        for item in rows
    ]


def _bank_ranking(qs):
    rows = (
        qs.values('bank_id', 'bank__name')
        .annotate(total_amount=Sum('amount'), total_count=Count('id'))
        .order_by('-total_amount')
    )
    return [
        {
            'bank_id': str(item['bank_id']),
            'bank_name': item['bank__name'],
            'total_amount': str(item['total_amount'] or 0),
            'total_count': item['total_count'],
        }
        for item in rows
    ]


class CommercialManagerListCreateView(BaseApiView):
    """Lista e cadastra Gerentes Comerciais (usuários da promotora com role=gerente_comercial)."""
    permission_classes = [IsAdminOrHasCommercialPermission]

    def get(self, request, format=None):
        search = request.query_params.get('search', '').strip()
        managers = User.objects.filter(role=User.GERENTE_COMERCIAL, company__isnull=True)
        if search:
            managers = managers.filter(
                django_models.Q(first_name__icontains=search)
                | django_models.Q(last_name__icontains=search)
                | django_models.Q(cpf__icontains=search)
                | django_models.Q(email__icontains=search)
            )
        managers = managers.order_by('first_name', 'last_name')

        self.log_info(
            request=request,
            action='list_commercial_managers',
            message='Usuário listou gerentes comerciais',
        )
        return paginate_queryset(request, managers, CommercialManagerSerializer)

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return [IsAdminOrHasCommercialPermission()]

    def post(self, request, format=None):
        serializer = CommercialManagerCreateSerializer(data=request.data)
        if serializer.is_valid():
            manager = serializer.save()
            self.audit_create(request=request, instance=manager, data_after=serializer.data)
            self.log_info(
                request=request,
                action='create_commercial_manager',
                message=f'Usuário criou o gerente comercial: {manager.cpf}',
                data={'user_id': manager.id},
            )
            return Response(CommercialManagerSerializer(manager).data, status=status.HTTP_201_CREATED)

        return Response(format_serializer_errors(serializer.errors), status=status.HTTP_400_BAD_REQUEST)


class CommercialManagerDetailView(BaseApiView):
    """Atualiza senha (e campos básicos) de um gerente comercial."""
    permission_classes = [IsAdminOrHasCommercialPermission]

    def get(self, request, pk, format=None):
        manager = get_object_or_404(User, pk=pk, role=User.GERENTE_COMERCIAL)
        return Response(CommercialManagerSerializer(manager).data)

    def patch(self, request, pk, format=None):
        manager = get_object_or_404(User, pk=pk, role=User.GERENTE_COMERCIAL)
        old_data = CommercialManagerSerializer(manager).data
        password = request.data.get('password')
        email = request.data.get('email')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')

        if not any([password, email, first_name, last_name]):
            return Response(
                {'detail': 'Informe senha, e-mail ou nome para atualizar.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if email is not None:
            manager.email = email
        if first_name is not None:
            manager.first_name = first_name
        if last_name is not None:
            manager.last_name = last_name
        if password:
            manager.set_password(password)
        manager.save()

        serializer = CommercialManagerSerializer(manager)
        self.audit_update(
            request=request,
            instance=manager,
            data_before=old_data,
            data_after=serializer.data,
        )
        self.log_info(
            request=request,
            action='update_commercial_manager',
            message=f'Usuário atualizou o gerente comercial: {manager.cpf}',
            data={'user_id': manager.id, 'password_changed': bool(password)},
        )
        return Response(serializer.data)


class CommercialManagerActivationView(BaseApiView):
    """Inativa/reativa gerente comercial. Inativar solta toda a equipe (corbans sem gerente)."""
    permission_classes = [IsAdminOrHasCommercialPermission]

    def post(self, request, pk, format=None):
        manager = get_object_or_404(User, pk=pk, role=User.GERENTE_COMERCIAL)
        action = (request.data.get('action') or 'deactivate').strip().lower()
        old_data = CommercialManagerSerializer(manager).data
        released = 0

        if action == 'activate':
            manager.reactivate()
            message = f'Usuário reativou o gerente comercial: {manager.cpf}'
            audit_action = 'activate_commercial_manager'
        else:
            reason = (request.data.get('reason') or '').strip()
            if not reason:
                return Response(
                    {'detail': 'Motivo da inativação é obrigatório (reason).'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            released = clear_manager_team(manager)
            manager.deactivate(by_user=request.user, reason=reason)
            message = (
                f'Usuário inativou o gerente comercial: {manager.cpf} '
                f'(equipe liberada: {released} corban(s))'
            )
            audit_action = 'deactivate_commercial_manager'

        serializer = CommercialManagerSerializer(manager)
        self.audit_update(
            request=request,
            instance=manager,
            data_before=old_data,
            data_after=serializer.data,
        )
        self.log_info(
            request=request,
            action=audit_action,
            message=message,
            data={'user_id': manager.id, 'team_released': released},
        )
        return Response({**serializer.data, 'team_released': released})


class CommercialTeamView(BaseApiView):
    """
    Lista e gerencia os membros (corbans) da equipe de um Gerente Comercial.
    Apenas administradores (ou colaboradores com permissão específica) podem
    adicionar/remover corbans da equipe.

    GET  ?manager=<id>  → membros da equipe do gerente
    GET  (sem manager)  → todos os vínculos gerente↔corban
    POST                → adiciona um corban à equipe
    PUT                 → sincroniza a equipe do gerente (company_ids)
    """
    permission_classes = [IsAdminOrHasCommercialPermission]

    def get(self, request, format=None):
        manager_id = request.query_params.get('manager')
        members = CommercialTeamMember.objects.select_related('company', 'manager', 'added_by')
        if manager_id:
            members = members.filter(manager_id=manager_id)
        members = members.order_by('company__name')
        serializer = CommercialTeamMemberSerializer(members, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = CommercialTeamMemberSerializer(data=request.data)
        if serializer.is_valid():
            if CommercialTeamMember.objects.filter(
                manager=serializer.validated_data['manager'],
                company=serializer.validated_data['company'],
            ).exists():
                return Response(
                    {'detail': 'Este corban já faz parte da equipe deste gerente comercial.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            CommercialTeamMember.objects.filter(company=serializer.validated_data['company']).exclude(
                manager=serializer.validated_data['manager'],
            ).delete()

            member = serializer.save(added_by=request.user)
            self.audit_create(request=request, instance=member, data_after=serializer.data)
            self.log_info(
                request=request,
                action='add_commercial_team_member',
                message=f'Usuário adicionou o corban {member.company.name} à equipe do gerente {member.manager.cpf}',
                data={'manager_id': member.manager_id, 'company_id': str(member.company_id)},
            )
            return Response(CommercialTeamMemberSerializer(member).data, status=status.HTTP_201_CREATED)

        return Response(format_serializer_errors(serializer.errors), status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, format=None):
        manager_id = request.data.get('manager')
        company_ids = request.data.get('company_ids')

        if not manager_id:
            return Response({'detail': 'Campo "manager" é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(company_ids, list):
            return Response({'detail': 'Campo "company_ids" deve ser uma lista.'}, status=status.HTTP_400_BAD_REQUEST)

        manager = get_object_or_404(User, pk=manager_id, role=User.GERENTE_COMERCIAL, is_active=True)
        desired_ids = {str(cid) for cid in company_ids if cid}

        existing = list(
            CommercialTeamMember.objects.filter(manager=manager).select_related('company')
        )
        existing_by_company = {str(m.company_id): m for m in existing}

        to_remove = [m for cid, m in existing_by_company.items() if cid not in desired_ids]
        to_add_ids = [cid for cid in desired_ids if cid not in existing_by_company]

        for member in to_remove:
            data_before = CommercialTeamMemberSerializer(member).data
            self.audit_delete(request=request, instance=member, data_before=data_before)
            member.delete()

        if to_add_ids:
            CommercialTeamMember.objects.filter(company_id__in=to_add_ids).exclude(manager=manager).delete()

        created = []
        for company_id in to_add_ids:
            member = CommercialTeamMember.objects.create(
                manager=manager,
                company_id=company_id,
                added_by=request.user,
            )
            created.append(member)
            self.audit_create(
                request=request,
                instance=member,
                data_after=CommercialTeamMemberSerializer(member).data,
            )

        self.log_info(
            request=request,
            action='sync_commercial_team',
            message=f'Usuário sincronizou a equipe do gerente {manager.cpf}',
            data={
                'manager_id': manager.id,
                'company_ids': list(desired_ids),
                'added': len(created),
                'removed': len(to_remove),
            },
        )

        members = CommercialTeamMember.objects.filter(manager=manager).select_related(
            'company', 'manager', 'added_by'
        )
        return Response(CommercialTeamMemberSerializer(members, many=True).data)


class CommercialTeamMemberDetailView(BaseApiView):
    """Remove um corban da equipe de um Gerente Comercial."""
    permission_classes = [IsAdminOrHasCommercialPermission]

    def delete(self, request, pk, format=None):
        member = get_object_or_404(CommercialTeamMember, pk=pk)
        data_before = CommercialTeamMemberSerializer(member).data

        self.audit_delete(request=request, instance=member, data_before=data_before)
        self.log_info(
            request=request,
            action='remove_commercial_team_member',
            message=f'Usuário removeu o corban {member.company.name} da equipe do gerente {member.manager.cpf}',
            data={'manager_id': member.manager_id, 'company_id': str(member.company_id)},
        )
        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CommercialDashboardView(BaseApiView):
    """
    Dashboard de produção do Gerente Comercial.
    Filtro por intervalo de dias: date_from / date_to (YYYY-MM-DD).
    `period=YYYY-MM` ainda é aceito (primeiro e último dia do mês).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        requester = request.user
        manager_id = request.query_params.get('manager')
        if requester.role == User.GERENTE_COMERCIAL:
            manager = requester
        else:
            if not manager_id:
                return Response({'detail': 'Parâmetro "manager" é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
            manager = get_object_or_404(User, pk=manager_id, role=User.GERENTE_COMERCIAL)

        is_self = requester.id == manager.id
        is_admin = requester.role == User.ADMIN and requester.company is None
        has_perm = (
            requester.role == User.COLABORADOR
            and requester.company is None
            and requester.has_permission('manage_commercial_teams')
        )
        if not (is_self or is_admin or has_perm):
            return Response({'detail': 'Sem permissão para ver este dashboard.'}, status=status.HTTP_403_FORBIDDEN)

        today = timezone.localdate()
        date_from, date_to = self._resolve_range(request, today)
        month_start = today.replace(day=1)
        week_start = today - timedelta(days=today.weekday())

        company_ids = team_company_ids_for(manager)
        proposals_qs = Proposal.objects.filter(company_id__in=company_ids)
        period_qs = proposals_qs.filter(disbursement_date__gte=date_from, disbursement_date__lte=date_to)
        month_qs = proposals_qs.filter(disbursement_date__gte=month_start, disbursement_date__lte=today)
        week_qs = proposals_qs.filter(disbursement_date__gte=week_start, disbursement_date__lte=today)

        production_by_company = _company_ranking(period_qs)
        seen_ids = {item['company_id'] for item in production_by_company}
        for member in CommercialTeamMember.objects.filter(manager=manager).select_related('company'):
            if str(member.company_id) not in seen_ids:
                production_by_company.append({
                    'company_id': str(member.company_id),
                    'company_name': member.company.name,
                    'total_amount': '0',
                    'total_count': 0,
                })
        ranking_by_period = sorted(production_by_company, key=lambda x: float(x['total_amount']), reverse=True)
        ranking_overall = _company_ranking(proposals_qs)
        production_by_bank = _bank_ranking(period_qs)
        top_bank = production_by_bank[0] if production_by_bank else None
        top_10 = ranking_by_period[:10]

        span_days = (date_to - date_from).days
        trunc = TruncDay if span_days <= 62 else TruncMonth
        by_period = (
            period_qs
            .annotate(bucket=trunc('disbursement_date'))
            .values('bucket')
            .annotate(amount=Sum('amount'), count=Count('id'))
            .order_by('bucket')
        )
        date_fmt = '%Y-%m-%d' if span_days <= 62 else '%Y-%m'
        production_by_period = [
            {
                'period': item['bucket'].strftime(date_fmt) if item['bucket'] else None,
                'amount': str(item['amount'] or 0),
                'count': item['count'],
            }
            for item in by_period
        ]

        period_totals = _agg(period_qs)

        self.log_info(
            request=request,
            action='view_commercial_dashboard',
            message=f'Usuário visualizou o dashboard comercial do gerente {manager.cpf}',
            data={'manager_id': manager.id, 'date_from': str(date_from), 'date_to': str(date_to)},
        )

        return Response({
            'manager': {
                'id': manager.id,
                'name': f'{manager.first_name} {manager.last_name}'.strip() or manager.cpf,
                'team_size': len(company_ids),
            },
            'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(),
            'productivity_month': {
                **_agg(month_qs),
                'label': month_start.strftime('%m/%Y'),
            },
            'productivity_week': {
                **_agg(week_qs),
                'label': f'{week_start.strftime("%d/%m")}–{today.strftime("%d/%m")}',
            },
            'productivity_period': period_totals,
            'top_10': top_10,
            'top_bank': top_bank,
            'production_by_bank': production_by_bank,
            'total_production': period_totals['amount'],
            'total_proposals': period_totals['count'],
            'production_by_period': production_by_period,
            'production_by_company': ranking_by_period,
            'ranking_overall': ranking_overall,
            'ranking_by_period': ranking_by_period,
            'period': request.query_params.get('period'),
        })

    def _resolve_range(self, request, today: date) -> tuple[date, date]:
        raw_from = request.query_params.get('date_from')
        raw_to = request.query_params.get('date_to')
        period = request.query_params.get('period')  # YYYY-MM (legado)

        date_from = parse_date(raw_from) if raw_from else None
        date_to = parse_date(raw_to) if raw_to else None

        if not date_from and not date_to and period:
            parts = period.split('-')
            if len(parts) == 2:
                year, month = int(parts[0]), int(parts[1])
                date_from = date(year, month, 1)
                if month == 12:
                    date_to = date(year, 12, 31)
                else:
                    date_to = date(year, month + 1, 1) - timedelta(days=1)

        if not date_from:
            date_from = today.replace(day=1)
        if not date_to:
            date_to = today
        if date_from > date_to:
            date_from, date_to = date_to, date_from
        return date_from, date_to
