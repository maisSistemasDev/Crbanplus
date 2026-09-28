"""
Views para liberação de comissões.
"""
import logging
from datetime import datetime
from decimal import Decimal
from django.http import HttpResponse
from django.utils.timezone import now
from django.db import transaction
from django.db.models import Q, Sum
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.response import Response
from rest_framework import status, permissions
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from core.base_views import BaseApiView
from core.permissions import IsAdmin
from core.utils import resolve_pix_fields, pix_type_label
from payments.models import Commission, Payment
from payments.serializers import CommissionSerializer
from payments.services.commission_query import (
    build_debit_projection,
    commission_amounts,
    consolidation_key,
)
from payments.services.debits import apply_debits, revert_debits

logger = logging.getLogger(__name__)


class CommissionReleaseView(BaseApiView):
    """
    API endpoint para liberar comissões em lote.
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        """
        Libera comissões selecionadas.
        
        Body:
        {
            "commission_ids": [id1, id2, ...],
            "release_type": "withdraw" ou "manual"
        }
        """
        commission_ids = request.data.get('commission_ids', [])
        release_type = request.data.get('release_type')
        
        if not commission_ids:
            return Response(
                {"error": "Nenhuma comissão selecionada"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if release_type not in ['withdraw', 'manual']:
            return Response(
                {"error": "Tipo de liberação inválido. Use 'withdraw' ou 'manual'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Buscar comissões
        commissions = Commission.objects.filter(
            id__in=commission_ids,
            release_status=Commission.NOT_RELEASED
        )
        
        if not commissions.exists():
            return Response(
                {"error": "Nenhuma comissão válida encontrada"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Definir status baseado no tipo de liberação
        new_status = (
            Commission.WITHDRAW_AVAILABLE if release_type == 'withdraw'
            else Commission.PENDING_MANUAL_PAYMENT
        )

        # Coletar user_ids antes do update (para push notifications)
        affected_user_ids = list(commissions.values_list('user_id', flat=True).distinct())

        # Débitos pendentes são abatidos no momento da liberação: o valor da
        # comissão passa a ser o líquido que será efetivamente pago.
        debit_result = apply_debits(commissions.select_related('user', 'company'))

        # Atualizar comissões
        updated_count = commissions.update(
            released=True,
            released_at=now(),
            released_by=request.user,
            release_status=new_status
        )

        # Notificar via push quando liberado para saque
        if release_type == 'withdraw' and updated_count:
            try:
                from core.push_signals import notify_commissions_released
                notify_commissions_released(affected_user_ids)
            except Exception:
                pass  # push é best-effort, nunca bloqueia o response

        return Response({
            "message": f"{updated_count} comissões liberadas com sucesso",
            "updated_count": updated_count,
            "release_type": release_type,
            "status": "withdraw_available" if release_type == "withdraw" else "pending_manual_payment",
            "debit_applied": str(debit_result['applied_total']),
            "debit_affected": debit_result['affected'],
            "zeroed_count": len(debit_result['zeroed_ids']),
        })


HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
CELL_BORDER = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin'),
)
CURRENCY_FORMAT = 'R$ #,##0.00'

PAYMENT_COLUMNS = ["Nome", "CPF/CNPJ", "Chave PIX", "Tipo PIX", "Banco", "Agência", "Conta", "Valor"]
DETAIL_COLUMNS = ["CPF do Cliente", "Nome do Cliente", "Banco", "Tabela", "Porcentagem"]


def _write_header(worksheet, headers: list[str]) -> None:
    worksheet.append(headers)
    for cell in worksheet[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = CELL_BORDER


def _style_last_row(worksheet, currency_columns: tuple[int, ...]) -> None:
    for cell in worksheet[worksheet.max_row]:
        cell.border = CELL_BORDER
        if cell.column in currency_columns:
            cell.number_format = CURRENCY_FORMAT


def payment_identity(commission: Commission) -> dict[str, str]:
    """Dados de pagamento do recebedor: corban nas comissões de empresa, usuário nas demais."""
    if commission.role == Commission.EMPRESA and commission.company_id:
        company = commission.company
        document = company.document or ''
        return {
            'name': company.name or '(sem nome)',
            'document': document,
            'pix_key': document,
            'pix_type': 'CNPJ' if company.person_type == 'PJ' else 'CPF',
        }

    if commission.user_id:
        user = commission.user
        name = f"{user.first_name or ''} {user.last_name or ''}".strip() or '(sem nome)'
        document = user.cpf or ''
        # Reverso de OneToOneField pode lançar RelatedObjectDoesNotExist.
        try:
            extra = user.extra_data
        except (ObjectDoesNotExist, AttributeError):
            extra = None
        pix_key, pix_type_code = resolve_pix_fields(
            extra.pix_key if extra else None,
            extra.pix_type if extra else None,
            fallback_key=document or None,
        )
        return {
            'name': name,
            'document': document,
            'pix_key': pix_key,
            'pix_type': str(pix_type_label(pix_type_code)),
        }

    if commission.company_id:
        company = commission.company
        document = company.document or ''
        return {
            'name': company.name or '(sem nome)',
            'document': document,
            'pix_key': document,
            'pix_type': 'CNPJ' if company.person_type == 'PJ' else 'CPF',
        }

    return {'name': 'N/A', 'document': 'N/A', 'pix_key': 'N/A', 'pix_type': 'N/A'}


class CommissionExportView(BaseApiView):
    """
    API endpoint para gerar arquivo Excel com comissões para pagamento manual.
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        """
        Gera arquivo Excel com dados das comissões selecionadas.

        Body:
        {
            "commission_ids": [id1, id2, ...],
            "consolidated": true | false
        }

        Consolidado: uma linha por recebedor, com tudo somado.
        Detalhado: uma linha por comissão, com CPF/nome do cliente, banco,
        tabela e porcentagem nas colunas finais.
        Comissões zeradas por débito ficam fora do lote e vão para a aba "Zerados".
        """
        commission_ids = request.data.get('commission_ids', [])
        consolidated = bool(request.data.get('consolidated'))

        if not commission_ids:
            return Response(
                {"error": "Nenhuma comissão selecionada"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Pré-carrega extra_data para evitar N+1 ao montar as colunas de PIX.
        commissions = list(
            Commission.objects.filter(id__in=commission_ids)
            .select_related(
                'user', 'user__extra_data', 'company', 'proposal',
                'proposal__bank', 'proposal__table',
            )
            .order_by('created_at', 'id')
        )

        if not commissions:
            return Response(
                {"error": "Nenhuma comissão encontrada"},
                status=status.HTTP_400_BAD_REQUEST
            )

        projection = build_debit_projection(commissions)

        payable: list[tuple[Commission, Decimal, Decimal, Decimal]] = []
        zeroed: list[tuple[Commission, Decimal, Decimal]] = []
        for commission in commissions:
            total_value, debit_value, net_value = commission_amounts(commission, projection)
            if net_value <= 0 and debit_value > 0:
                zeroed.append((commission, total_value, debit_value))
            else:
                payable.append((commission, total_value, debit_value, net_value))

        if not payable:
            return Response(
                {
                    "error": "Nenhuma linha válida para exportação.",
                    "detail": "Todas as comissões selecionadas foram zeradas por débito.",
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        wb = Workbook()
        ws = wb.active
        ws.title = "Pagamentos"

        if consolidated:
            self._write_consolidated(ws, payable)
        else:
            self._write_detailed(ws, payable)

        if zeroed:
            self._write_zeroed(wb.create_sheet(title="Zerados"), zeroed)

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        suffix = 'consolidado' if consolidated else 'detalhado'
        filename = f'pagamentos_comissoes_{suffix}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        wb.save(response)
        return response

    def _write_consolidated(self, worksheet, payable) -> None:
        _write_header(worksheet, PAYMENT_COLUMNS + ["Status", "Qtd. Comissões", "IDs das Comissões"])

        # Uma linha por recebedor e status: valores de status diferentes não se somam.
        groups: dict[tuple, dict] = {}
        for commission, _total, _debit, net_value in payable:
            key = consolidation_key(commission)
            group = groups.get(key)
            if group is None:
                group = {
                    'identity': payment_identity(commission),
                    'status': commission.get_release_status_display(),
                    'status_code': key[2],
                    'value': Decimal('0'),
                    'ids': [],
                }
                groups[key] = group
            group['value'] += net_value
            group['ids'].append(commission.id)

        total = Decimal('0')
        ordered = sorted(
            groups.values(),
            key=lambda item: (item['identity']['name'].lower(), item['status_code']),
        )
        for group in ordered:
            identity = group['identity']
            worksheet.append([
                identity['name'],
                identity['document'],
                identity['pix_key'],
                identity['pix_type'],
                '',
                '',
                '',
                float(group['value']),
                group['status'],
                len(group['ids']),
                ', '.join(str(item) for item in group['ids']),
            ])
            _style_last_row(worksheet, (8,))
            total += group['value']

        worksheet.append(['', '', '', '', '', '', 'TOTAL:', float(total), '', '', ''])
        for cell in worksheet[worksheet.max_row]:
            cell.font = Font(bold=True)
            cell.border = CELL_BORDER
            if cell.column == 8:
                cell.number_format = CURRENCY_FORMAT

        for index, width in enumerate([30, 18, 25, 18, 20, 12, 15, 15, 22, 16, 40], 1):
            worksheet.column_dimensions[get_column_letter(index)].width = width

    def _write_detailed(self, worksheet, payable) -> None:
        _write_header(worksheet, PAYMENT_COLUMNS + ["ID Comissão"] + DETAIL_COLUMNS)

        total = Decimal('0')
        for commission, _total_value, _debit_value, net_value in payable:
            identity = payment_identity(commission)
            proposal = commission.proposal
            table = getattr(proposal, 'table', None)
            worksheet.append([
                identity['name'],
                identity['document'],
                identity['pix_key'],
                identity['pix_type'],
                '',
                '',
                '',
                float(net_value),
                str(commission.id),
                getattr(proposal, 'client_document', '') or '',
                getattr(proposal, 'client_name', '') or '',
                proposal.bank.name if proposal and proposal.bank_id else '',
                (table.name_in_bank or table.name) if table else '',
                float(commission.percentage or 0),
            ])
            _style_last_row(worksheet, (8,))
            total += net_value

        worksheet.append(['', '', '', '', '', '', 'TOTAL:', float(total), '', '', '', '', '', ''])
        for cell in worksheet[worksheet.max_row]:
            cell.font = Font(bold=True)
            cell.border = CELL_BORDER
            if cell.column == 8:
                cell.number_format = CURRENCY_FORMAT

        for index, width in enumerate([30, 18, 25, 18, 20, 12, 15, 15, 14, 18, 30, 20, 24, 14], 1):
            worksheet.column_dimensions[get_column_letter(index)].width = width

    def _write_zeroed(self, worksheet, zeroed) -> None:
        """Comissões totalmente consumidas por débito: não entram no lote, mas precisam aparecer."""
        _write_header(worksheet, [
            "Recebedor", "CPF/CNPJ", "ID Comissão", "Cód. da Proposta", "CPF do Cliente",
            "Nome do Cliente", "Comissão", "Débito", "Total",
        ])

        for commission, total_value, debit_value in zeroed:
            identity = payment_identity(commission)
            proposal = commission.proposal
            worksheet.append([
                identity['name'],
                identity['document'],
                str(commission.id),
                getattr(proposal, 'contract_number', '') or '',
                getattr(proposal, 'client_document', '') or '',
                getattr(proposal, 'client_name', '') or '',
                float(total_value),
                float(debit_value),
                0,
            ])
            _style_last_row(worksheet, (7, 8, 9))

        for index, width in enumerate([30, 18, 14, 20, 18, 30, 15, 15, 15], 1):
            worksheet.column_dimensions[get_column_letter(index)].width = width


class CommissionUpdateStatusView(BaseApiView):
    """
    API endpoint para atualizar status de comissões.
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        """
        Atualiza o status de comissões selecionadas.
        
        Body:
        {
            "commission_ids": [id1, id2, ...],
            "new_status": "withdraw_available", "paid" ou "not_released"
        }
        """
        commission_ids = request.data.get('commission_ids', [])
        new_status = request.data.get('new_status')
        
        if not commission_ids:
            return Response(
                {"error": "Nenhuma comissão selecionada"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_status not in [Commission.WITHDRAW_AVAILABLE, Commission.PAID, Commission.NOT_RELEASED]:
            return Response(
                {"error": "Status inválido. Use 'withdraw_available', 'paid' ou 'not_released'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_status == Commission.NOT_RELEASED:
            commissions = Commission.objects.filter(
                id__in=commission_ids,
                release_status__in=[Commission.PENDING_MANUAL_PAYMENT, Commission.PAID],
            )
            if not commissions.exists():
                return Response(
                    {"error": "Nenhuma comissão paga ou aguardando pagamento encontrada"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            payment_ids = list(
                commissions.exclude(payment_id=None).values_list('payment_id', flat=True)
            )
            with transaction.atomic():
                # Devolve ao débito de origem o que havia sido abatido na liberação.
                revert_debits(list(commissions))

                updated_count = commissions.update(
                    release_status=Commission.NOT_RELEASED,
                    released=False,
                    released_at=None,
                    released_by=None,
                    paid_at=None,
                    paid_by=None,
                    payment=None,
                )
                for payment in Payment.objects.filter(id__in=payment_ids):
                    remaining = payment.commissions.count()
                    if remaining == 0:
                        note = 'Pagamento cancelado; comissões revertidas para não liberado.'
                        payment.status = Payment.REJECTED
                        payment.notes = f"{payment.notes}\n{note}".strip() if payment.notes else note
                        payment.save(update_fields=['status', 'notes', 'updated_at'])
                    else:
                        total_amount = payment.commissions.aggregate(total=Sum('value')).get('total') or Decimal('0')
                        payment.total_amount = total_amount
                        payment.save(update_fields=['total_amount', 'updated_at'])

            return Response({
                "message": f"{updated_count} pagamento(s) cancelado(s). Comissões voltaram para 'não liberado'.",
                "updated_count": updated_count,
                "new_status": new_status,
            })
 
        # Buscar comissões
        commissions = Commission.objects.filter(
            id__in=commission_ids,
            release_status=Commission.PENDING_MANUAL_PAYMENT
        )
        
        if not commissions.exists():
            return Response(
                {"error": "Nenhuma comissão com status 'aguardando pagamento' encontrada"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Atualizar status. Quando marcar como pago, também cria registros
        # em Payment por usuário e vincula as comissões, para aparecer
        # corretamente em /payments.
        created_payments = 0
        if new_status == Commission.PAID:
            paid_at = now()
            grouped_commissions: dict[int, list[int]] = {}
            missing_user_commission_ids: list[int] = []

            for commission in commissions.select_related('user'):
                if commission.user_id:
                    grouped_commissions.setdefault(commission.user_id, []).append(commission.id)
                else:
                    missing_user_commission_ids.append(commission.id)

            updated_count = 0
            with transaction.atomic():
                for user_id, commission_group_ids in grouped_commissions.items():
                    user_commissions = Commission.objects.filter(id__in=commission_group_ids)
                    total_amount = user_commissions.aggregate(total=Sum('value')).get('total') or Decimal('0')

                    payment = Payment.objects.create(
                        user_id=user_id,
                        total_amount=total_amount,
                        status=Payment.PAID,
                        approved_by=request.user,
                        approved_at=paid_at,
                        paid_at=paid_at,
                        payment_method=Payment.MANUAL,
                        notes=f'Pagamento manual gerado a partir de {len(commission_group_ids)} comissões.',
                    )
                    created_payments += 1

                    updated_count += user_commissions.update(
                        release_status=Commission.PAID,
                        payment=payment,
                        paid_at=paid_at,
                        paid_by=request.user,
                    )

                if missing_user_commission_ids:
                    updated_count += Commission.objects.filter(id__in=missing_user_commission_ids).update(
                        release_status=Commission.PAID,
                        paid_at=paid_at,
                        paid_by=request.user,
                    )
        else:
            updated_count = commissions.update(release_status=new_status)
        
        status_label = "saque liberado" if new_status == Commission.WITHDRAW_AVAILABLE else "pago"
        
        return Response({
            "message": f"{updated_count} comissões atualizadas para '{status_label}'",
            "updated_count": updated_count,
            "new_status": new_status,
            "created_payments": created_payments if new_status == Commission.PAID else 0
        })

