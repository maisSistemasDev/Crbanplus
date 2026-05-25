"""
Views para liberação de comissões.
"""
import logging
from datetime import datetime
from decimal import Decimal
from django.http import HttpResponse
from django.utils.timezone import now
from django.db.models import Q
from rest_framework.response import Response
from rest_framework import status, permissions
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from core.base_views import BaseApiView
from core.permissions import IsAdmin
from core.models import User
from payments.models import Commission
from payments.serializers import CommissionSerializer

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
            "status": "withdraw_available" if release_type == "withdraw" else "pending_manual_payment"
        })


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
            "commission_ids": [id1, id2, ...]
        }
        """
        commission_ids = request.data.get('commission_ids', [])
        
        if not commission_ids:
            return Response(
                {"error": "Nenhuma comissão selecionada"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Buscar comissões
        commissions = Commission.objects.filter(
            id__in=commission_ids
        ).select_related('user', 'company', 'proposal')
        
        if not commissions.exists():
            return Response(
                {"error": "Nenhuma comissão encontrada"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Criar workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Pagamentos"
        
        # Estilos
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Cabeçalhos
        headers = ["Nome", "CPF/CNPJ", "Chave PIX", "Tipo PIX", "Banco", "Agência", "Conta", "Valor", "ID Comissão"]
        ws.append(headers)
        
        # Aplicar estilo no cabeçalho
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border
        
        # Adicionar dados
        total = Decimal('0')
        for comm in commissions:
            # Determinar nome e documento
            if comm.user:
                name = f"{comm.user.first_name} {comm.user.last_name}"
                document = comm.user.cpf
                pix_key = getattr(comm.user, 'pix_key', '') or document
                pix_type = dict(comm.user.PIX_TYPE_CHOICES).get(getattr(comm.user, 'pix_type', ''), 'CPF')
                bank = getattr(comm.user, 'bank_name', '')
                agency = getattr(comm.user, 'bank_agency', '')
                account = getattr(comm.user, 'bank_account', '')
            elif comm.company:
                name = comm.company.name
                document = comm.company.cnpj
                pix_key = document
                pix_type = 'CNPJ'
                bank = ''
                agency = ''
                account = ''
            else:
                name = "N/A"
                document = "N/A"
                pix_key = "N/A"
                pix_type = "N/A"
                bank = ''
                agency = ''
                account = ''
            
            row = [
                name,
                document,
                pix_key,
                pix_type,
                bank,
                agency,
                account,
                float(comm.value),
                str(comm.id)
            ]
            ws.append(row)
            total += comm.value
            
            # Aplicar bordas
            for cell in ws[ws.max_row]:
                cell.border = border
                if cell.column == 8:  # Coluna Valor
                    cell.number_format = 'R$ #,##0.00'
        
        # Adicionar linha de total
        ws.append(['', '', '', '', '', '', 'TOTAL:', float(total), ''])
        last_row = ws.max_row
        for cell in ws[last_row]:
            cell.font = Font(bold=True)
            cell.border = border
            if cell.column == 8:  # Coluna Valor
                cell.number_format = 'R$ #,##0.00'
        
        # Ajustar largura das colunas
        column_widths = [30, 18, 25, 18, 20, 12, 15, 15, 38]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[chr(64 + i)].width = width
        
        # Gerar response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f'pagamentos_comissoes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        wb.save(response)
        return response


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
            "new_status": "withdraw_available" ou "paid"
        }
        """
        commission_ids = request.data.get('commission_ids', [])
        new_status = request.data.get('new_status')
        
        if not commission_ids:
            return Response(
                {"error": "Nenhuma comissão selecionada"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_status not in [Commission.WITHDRAW_AVAILABLE, Commission.PAID]:
            return Response(
                {"error": "Status inválido. Use 'withdraw_available' ou 'paid'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
        
        # Atualizar status
        update_data = {'release_status': new_status}
        
        if new_status == Commission.PAID:
            update_data['paid_at'] = now()
            update_data['paid_by'] = request.user
        
        updated_count = commissions.update(**update_data)
        
        status_label = "saque liberado" if new_status == Commission.WITHDRAW_AVAILABLE else "pago"
        
        return Response({
            "message": f"{updated_count} comissões atualizadas para '{status_label}'",
            "updated_count": updated_count,
            "new_status": new_status
        })

