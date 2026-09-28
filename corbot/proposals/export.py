"""Exportação das propostas para Excel, com o mesmo recorte da listagem."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from rest_framework import permissions, status
from rest_framework.response import Response

from core.base_views import BaseApiView
from payments.models import Commission

HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
CELL_BORDER = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin'),
)
CURRENCY_FORMAT = 'R$ #,##0.00'
DATE_FORMAT = 'DD/MM/YYYY'

# Teto de segurança: acima disso o Excel vira um problema maior que a análise.
MAX_ROWS = 20000

COLUMNS = [
    ("Cód. da Proposta", 22),
    ("Cliente", 30),
    ("CPF do Cliente", 18),
    ("Corban", 28),
    ("Vendedor", 26),
    ("Matrícula", 14),
    ("Banco", 20),
    ("Convênio", 22),
    ("Tabela", 26),
    ("Valor da Operação", 18),
    ("Comissão", 16),
    ("Status do Pagamento", 22),
    ("Sinistro", 18),
    ("Data de Liberação", 18),
    ("Criado em", 18),
]

CURRENCY_COLUMNS = (10, 11)
DATE_COLUMNS = (14, 15)

STATUS_LABELS = dict(Commission.RELEASE_STATUS_CHOICES)

# Mesma regra do ProposalSerializer: vence o status mais avançado.
STATUS_PRIORITY = {
    Commission.SINISTRO: 0,
    Commission.NOT_RELEASED: 1,
    Commission.WITHDRAW_AVAILABLE: 2,
    Commission.PENDING_MANUAL_PAYMENT: 3,
    Commission.PAID: 4,
}


def _payment_status(proposal) -> str:
    commissions = list(proposal.commissions.all())
    if not commissions:
        return STATUS_LABELS[Commission.NOT_RELEASED]
    best = max(commissions, key=lambda c: STATUS_PRIORITY.get(c.release_status, 0))
    return STATUS_LABELS.get(best.release_status, best.release_status or '-')


def _commission_total(proposal) -> Decimal:
    return sum(
        (Decimal(str(item.value or 0)) for item in proposal.commissions.all()),
        Decimal('0'),
    )


def _claim_label(proposal) -> str:
    claims = list(proposal.claims.all())
    if not claims:
        return ''
    claim = max(claims, key=lambda c: (c.created_at, c.id))
    return claim.get_claim_type_display()


def _seller_name(proposal) -> str:
    seller = proposal.seller
    if not seller:
        return ''
    return f'{seller.first_name or ""} {seller.last_name or ""}'.strip() or seller.username


def _row(proposal) -> list:
    return [
        proposal.contract_number or '',
        proposal.client_name or '',
        proposal.client_document or '',
        proposal.company.name if proposal.company_id else '',
        _seller_name(proposal),
        proposal.seller.matricula if proposal.seller_id else '',
        proposal.bank.name if proposal.bank_id else '',
        proposal.agreement.name if proposal.agreement_id else '',
        (proposal.table.name_in_bank or proposal.table.code_in_bank or '') if proposal.table_id else '',
        Decimal(str(proposal.amount or 0)),
        _commission_total(proposal),
        _payment_status(proposal),
        _claim_label(proposal),
        proposal.disbursement_date,
        proposal.created_at.replace(tzinfo=None) if proposal.created_at else None,
    ]


class ProposalExportView(BaseApiView):
    """Gera o Excel das propostas conforme os filtros aplicados na tela."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .views import filtered_proposals_for

        proposals = filtered_proposals_for(request).order_by('-created_at')
        total = proposals.count()

        if total == 0:
            return Response(
                {"error": "Nenhuma proposta encontrada para os filtros aplicados."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if total > MAX_ROWS:
            return Response(
                {
                    "error": (
                        f"São {total} propostas no filtro atual, acima do limite de "
                        f"{MAX_ROWS} por arquivo. Restrinja o período ou os filtros."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Propostas"

        worksheet.append([header for header, _ in COLUMNS])
        for cell in worksheet[1]:
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = CELL_BORDER

        for index, (_, width) in enumerate(COLUMNS, start=1):
            worksheet.column_dimensions[worksheet.cell(row=1, column=index).column_letter].width = width

        for proposal in proposals.iterator(chunk_size=500):
            worksheet.append(_row(proposal))
            for cell in worksheet[worksheet.max_row]:
                cell.border = CELL_BORDER
                if cell.column in CURRENCY_COLUMNS:
                    cell.number_format = CURRENCY_FORMAT
                elif cell.column in DATE_COLUMNS:
                    cell.number_format = DATE_FORMAT

        worksheet.freeze_panes = 'A2'

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f'propostas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        workbook.save(response)
        return response
