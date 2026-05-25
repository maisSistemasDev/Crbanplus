"""
Views relacionadas a operações com comissões.
"""
import logging
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.db.models import Q, Sum
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from core.base_views import BaseApiView
from core.permissions import IsGerente, IsAdmin, IsAdminOrGerente
from core.models import User
from payments.models import Commission, Payment
from payments.serializers import CommissionSerializer, CommissionMirrorSerializer
from payments.pipeline.commission_pipeline import GenerateCommissionsPipeline
from core.utils import UserInstance

logger = logging.getLogger(__name__)

def convert_uuids_to_strings(obj):
    """
    Converte recursivamente objetos UUID para strings em dicionários e listas.
    """
    if isinstance(obj, dict):
        return {key: convert_uuids_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_uuids_to_strings(item) for item in obj]
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj


class CommissionListCreateView(BaseApiView):
    """
    API endpoint para listar e criar comissões.
    """
    def get_permissions(self):
        permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get(self, request, format=None):
        """
        Lista as comissões.
        """
        begin_date = request.GET.get('begin_date') or datetime.now() - timedelta(days=30)
        end_date = request.GET.get('end_date') or datetime.now()
        client_document = request.GET.get('client_document')
        client_name = request.GET.get('client_name')
        commissions = Commission.objects.filter(created_at__range=[begin_date, end_date])
        if request.user.role == User.VENDEDOR:
            commissions = commissions.filter(
                user=request.user,
                release_status__in=[Commission.WITHDRAW_AVAILABLE, Commission.PENDING_MANUAL_PAYMENT]
            )
        elif request.user.role == User.LIDER:
            commissions = commissions.filter(
                Q(user=request.user) | Q(user__leader=request.user),
                release_status__in=[Commission.WITHDRAW_AVAILABLE, Commission.PENDING_MANUAL_PAYMENT]
            )
        elif request.user.role == User.GERENTE:
            commissions = commissions.filter(
                user=request.user,
                release_status__in=[Commission.WITHDRAW_AVAILABLE, Commission.PENDING_MANUAL_PAYMENT]
            )
        elif request.user.role == User.EMPRESA_ADMIN:
            commissions = commissions.filter(company=request.user.company)
        elif(request.user.role != User.ADMIN):
            return Response({"detail": "Você não tem permissão para acessar esta página."}, status=status.HTTP_403_FORBIDDEN)
        
        if(client_document):
            commissions = commissions.filter(proposal__client_document=client_document)
        if(client_name):
            commissions = commissions.filter(proposal__client_name=client_name)
        if(request.GET.get('user')):
            commissions = commissions.filter(user_id=request.GET.get('user'))
        if(request.GET.get('company')):
            commissions = commissions.filter(company_id=request.GET.get('company'))
        if(request.GET.get('role')):
            commissions = commissions.filter(role=request.GET.get('role'))
        if(request.GET.get('payment_id')):
            commissions = commissions.filter(payment_id=request.GET.get('payment_id'))
        if(request.GET.get('proposal_id')):
            commissions = commissions.filter(proposal_id=request.GET.get('proposal_id'))
        if(request.GET.get('status')):
            commissions = commissions.filter(payment__status=request.GET.get('status'))
        serializer = CommissionSerializer(commissions, many=True)
        return Response(serializer.data)

    def patch(self, request, format=None):
        """
        Libera as comissões para pagamento.
        """
        user = request.user
        if(user.role != User.ADMIN):
            return Response({"detail": "Você não tem permissão para acessar esta página."}, status=status.HTTP_403_FORBIDDEN)

        commission_ids = request.data.get('commission_ids')
        new_status = request.data.get('status')
        if new_status not in [Payment.APPROVED, Payment.REJECTED, Payment.PAID]:
            return Response({"detail": "Status inválido."}, status=status.HTTP_400_BAD_REQUEST)

        commissions = Commission.objects.filter(id__in=commission_ids, released=False)

        payments = []
        for commission in commissions:
            commission.released = True
            commission.released_at = now()
            commission.released_by = request.user
            if(commission.user not in [payment.user for payment in payments]):
                payment = Payment(
                    user=commission.user,
                    total_amount=commission.value,
                    status=new_status,
                    approved_by=request.user,
                    approved_at=now()
                )
                payment.save()
                payments.append(payment)
                commission.payment = payment
            else:
                payment = next((p for p in payments if p.user == commission.user), None)
                payment.total_amount += commission.value
                payment.save()
            commission.save()
        return Response({"detail": "Comissões liberadas com sucesso"}, status=status.HTTP_200_OK)

class CommissionMirrorView(BaseApiView):
    """
    API endpoint para criar e baixar um espelho de comissões.
    """
    def get_permissions(self):
        permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def post(self, request, format=None):
        """
        Cria e baixa um espelho de comissões.
        """
        # Verifica se é para download ou apenas visualização
        download = request.data.get('download', False)
        
        # Obtém os IDs das comissões
        commission_ids = request.data.get('commission_ids')
        if not commission_ids:
            return Response(
                {"detail": "É necessário informar os commission_ids."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Valida se é uma lista ou converte se for string
        try:
            if isinstance(commission_ids, str):
                commission_ids_list = commission_ids.split(',')
            elif isinstance(commission_ids, list):
                commission_ids_list = commission_ids
            else:
                raise ValueError("Formato inválido")
                
            commissions = Commission.objects.filter(id__in=commission_ids_list)
        except Exception as e:
            return Response(
                {"detail": "Formato inválido para commission_ids. Use uma lista ou string separada por vírgulas."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not commissions.exists():
            return Response(
                {"detail": "Nenhuma comissão encontrada com os IDs fornecidos."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar permissões do usuário para as comissões
        user = UserInstance(request.user)
        if not user.is_superuser and user.role != User.ADMIN:
            # Filtra as comissões baseado no papel do usuário
            if user.role == User.GERENTE:
                commissions = commissions.filter(
                    company=user.company
                )
            elif user.role == User.LIDER:
                commissions = commissions.filter(
                    Q(user__leader=user) | Q(user=user)
                )
            elif user.role == User.VENDEDOR:
                commissions = commissions.filter(user=user)
            else:
                return Response(
                    {"detail": "Você não tem permissão para acessar esta página."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if not commissions.exists():
                return Response({"detail": "Nenhuma comissão encontrada com os IDs fornecidos."}, status=status.HTTP_404_NOT_FOUND)
        
        # Agrupa as comissões por proposta
        proposals_data = {}
        for commission in commissions:
            proposal_id = commission.proposal.id 
            if proposal_id not in proposals_data:
                proposals_data[proposal_id] = {
                    'proposal': commission.proposal,
                    'commissions': []
                }
            proposals_data[proposal_id]['commissions'].append(commission)
        
        # Debug: Verificar dados carregados
        logger.debug(f"Total de propostas agrupadas: {len(proposals_data)}")
        for proposal_id, data in proposals_data.items():
            logger.debug(f"Proposta {proposal_id}: {len(data['commissions'])} comissões")
            for commission in data['commissions']:
                logger.debug(f"  - ID: {commission.id}, Role: {commission.role}, Value: {commission.value}, Percentage: {commission.percentage}")
        
        # Cria os objetos de espelho para serialização
        mirror_data = []
        for proposal_id, data in proposals_data.items():
            mirror_obj = type('CommissionMirror', (), {
                'proposal': data['proposal'],
                'commissions': data['commissions']
            })()
            mirror_data.append(mirror_obj)
        
        # Serializa os dados
        serializer = CommissionMirrorSerializer(mirror_data, many=True)
        
        if download:
            # Cria um workbook Excel
            wb = Workbook()
            
            # Remove a planilha padrão
            wb.remove(wb.active)
            
            # Cria planilha principal
            ws_main = wb.create_sheet(title="Espelho de Comissões")
            
            # Estilos
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            subheader_font = Font(bold=True, color="000000")
            subheader_fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
            center_alignment = Alignment(horizontal="center", vertical="center")
            currency_format = '_-R$ * #,##0.00_-;-R$ * #,##0.00_-;_-R$ * "-"_-;_-@_-'
            percentage_format = '0.00%'
            
            # Cabeçalho principal
            ws_main.merge_cells('A1:L1')
            ws_main['A1'] = "ESPELHO DE COMISSÕES"
            ws_main['A1'].font = Font(bold=True, size=16)
            ws_main['A1'].alignment = center_alignment
            ws_main['A1'].fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
            ws_main['A1'].font = Font(bold=True, size=16, color="FFFFFF")
            
            # Informações gerais
            row = 3
            ws_main[f'A{row}'] = f"Gerado em: {now().strftime('%d/%m/%Y %H:%M:%S')}"
            ws_main[f'A{row}'].font = Font(bold=True)
            row += 1
            ws_main[f'A{row}'] = f"Usuário: {user.name}"
            ws_main[f'A{row}'].font = Font(bold=True)
            row += 1
            if user.company:
                ws_main[f'A{row}'] = f"Empresa: {user.company.name}"
                ws_main[f'A{row}'].font = Font(bold=True)
                row += 1
            ws_main[f'A{row}'] = f"Total de registros: {len(mirror_data)}"
            ws_main[f'A{row}'].font = Font(bold=True)
            
            row += 2
            
            # Cabeçalho da tabela
            headers = [
                'Proposta ID', 'Cliente', 'Documento', 'Valor Proposta', 
                'Banco', 'Tabela', 'Vendedor', 'Líder', 'Empresa',
                'Comissão Vendedor', '% Vendedor', 'Comissão Líder', 
                '% Líder', 'Comissão Empresa', '% Empresa'
            ]
            
            for col, header in enumerate(headers, 1):
                cell = ws_main.cell(row=row, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_alignment
            
            row += 1
            
            # Dados das comissões
            for mirror_item in mirror_data:
                proposal = mirror_item.proposal
                commissions_list = mirror_item.commissions
                
                # Debug: vamos verificar se há comissões
                logger.debug(f"Proposta {proposal.id}: {len(commissions_list)} comissões")
                for c in commissions_list:
                    logger.debug(f"  - Role: {c.role}, Value: {c.value}, Percentage: {c.percentage}")
                
                # Organiza as comissões por tipo - usando as constantes corretas do modelo Commission
                seller_commission = next((c for c in commissions_list if c.role == Commission.VENDEDOR), None)
                leader_commission = next((c for c in commissions_list if c.role == Commission.LIDER), None)
                company_commission = next((c for c in commissions_list if c.role == Commission.EMPRESA), None)
                
                logger.debug(f"Seller: {seller_commission}, Leader: {leader_commission}, Company: {company_commission}")
                
                # Dados da linha
                data_row = [
                    str(proposal.id),
                    proposal.client_name or '',
                    proposal.client_document or '',
                    float(proposal.amount) if proposal.amount else 0,
                    proposal.bank.name if proposal.bank else '',
                    proposal.table.name_in_bank if proposal.table else '',
                    seller_commission.user.get_full_name() if seller_commission and seller_commission.user else '',
                    leader_commission.user.get_full_name() if leader_commission and leader_commission.user else '',
                    company_commission.company.name if company_commission and company_commission.company else '',
                    float(seller_commission.value) if seller_commission and seller_commission.value else 0,
                    float(seller_commission.percentage) / 100 if seller_commission and seller_commission.percentage else 0,
                    float(leader_commission.value) if leader_commission and leader_commission.value else 0,
                    float(leader_commission.percentage) / 100 if leader_commission and leader_commission.percentage else 0,
                    float(company_commission.value) if company_commission and company_commission.value else 0,
                    float(company_commission.percentage) / 100 if company_commission and company_commission.percentage else 0
                ]
                
                for col, value in enumerate(data_row, 1):
                    cell = ws_main.cell(row=row, column=col, value=value)
                    
                    # Formatação específica por coluna
                    if col == 4:  # Valor Proposta
                        cell.number_format = currency_format
                    elif col in [10, 12, 14]:  # Valores de comissão
                        cell.number_format = currency_format
                    elif col in [11, 13, 15]:  # Percentuais
                        cell.number_format = percentage_format
                    
                    # Alinhamento
                    if col in [1, 2, 3, 5, 6, 7, 8, 9]:  # Texto
                        cell.alignment = Alignment(horizontal="left")
                    else:  # Números
                        cell.alignment = Alignment(horizontal="right")
                
                row += 1
            
            # Linha de totais
            total_row = row
            ws_main[f'A{total_row}'] = "TOTAIS"
            ws_main[f'A{total_row}'].font = subheader_font
            ws_main[f'A{total_row}'].fill = subheader_fill
            
            # Fórmulas para somar os totais
            ws_main[f'D{total_row}'] = f'=SUM(D{row-len(mirror_data)}:D{row-1})'  # Total propostas
            ws_main[f'J{total_row}'] = f'=SUM(J{row-len(mirror_data)}:J{row-1})'  # Total comissão vendedor
            ws_main[f'L{total_row}'] = f'=SUM(L{row-len(mirror_data)}:L{row-1})'  # Total comissão líder
            ws_main[f'N{total_row}'] = f'=SUM(N{row-len(mirror_data)}:N{row-1})'  # Total comissão empresa
            
            # Formatação dos totais
            for col in [4, 10, 12, 14]:
                ws_main.cell(row=total_row, column=col).number_format = currency_format
                ws_main.cell(row=total_row, column=col).font = subheader_font
                ws_main.cell(row=total_row, column=col).fill = subheader_fill
            
            # Ajusta largura das colunas
            column_widths = {
                'A': 12, 'B': 25, 'C': 18, 'D': 15, 'E': 20, 'F': 20,
                'G': 25, 'H': 25, 'I': 25, 'J': 18, 'K': 12, 'L': 18,
                'M': 12, 'N': 18, 'O': 12
            }
            
            for col, width in column_widths.items():
                ws_main.column_dimensions[col].width = width
            
            # Cria uma segunda planilha com resumo por usuário
            ws_summary = wb.create_sheet(title="Resumo por Usuário")
            
            # Cabeçalho do resumo
            ws_summary['A1'] = "RESUMO POR USUÁRIO"
            ws_summary['A1'].font = Font(bold=True, size=14)
            ws_summary.merge_cells('A1:D1')
            
            row = 3
            summary_headers = ['Usuário', 'Função', 'Total Comissões', 'Valor Total']
            for col, header in enumerate(summary_headers, 1):
                cell = ws_summary.cell(row=row, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_alignment
            
            # Agrupa comissões por usuário
            user_summary = {}
            for mirror_item in mirror_data:
                for commission in mirror_item.commissions:
                    if commission.user:
                        user_key = (commission.user.id, commission.user.get_full_name(), commission.get_role_display())
                        if user_key not in user_summary:
                            user_summary[user_key] = {'count': 0, 'total': 0}
                        user_summary[user_key]['count'] += 1
                        user_summary[user_key]['total'] += float(commission.value)
            
            row += 1
            for (user_id, user_name, role), data in user_summary.items():
                ws_summary.cell(row=row, column=1, value=user_name)
                ws_summary.cell(row=row, column=2, value=role)
                ws_summary.cell(row=row, column=3, value=data['count'])
                ws_summary.cell(row=row, column=4, value=data['total']).number_format = currency_format
                row += 1
            
            # Ajusta largura das colunas do resumo
            ws_summary.column_dimensions['A'].width = 30
            ws_summary.column_dimensions['B'].width = 15
            ws_summary.column_dimensions['C'].width = 18
            ws_summary.column_dimensions['D'].width = 18
            
            # Cria uma terceira planilha com lote de pagamentos
            ws_batch = wb.create_sheet(title="Lote de Pagamentos")
            
            # Cabeçalho do lote de pagamentos
            ws_batch['A1'] = "LOTE DE PAGAMENTOS"
            ws_batch['A1'].font = Font(bold=True, size=14)
            ws_batch.merge_cells('A1:I1')
            ws_batch['A1'].alignment = center_alignment
            ws_batch['A1'].fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
            ws_batch['A1'].font = Font(bold=True, size=14, color="FFFFFF")
            
            row = 3
            batch_headers = [
                'Cod', 'Tipo de Chave', 'Chave PIX', 'CPF ou CNPJ (opcional)', 
                'Valor', 'Email (opcional)', 'ID integração (opcional)', 
                'Descrição Pix (opcional)', 'Data de agendamento (opcional)'
            ]
            
            for col, header in enumerate(batch_headers, 1):
                cell = ws_batch.cell(row=row, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_alignment
            
            row += 1
            
            # Dados do lote de pagamentos - agrupa por usuário
            batch_data = {}
            for mirror_item in mirror_data:
                for commission in mirror_item.commissions:
                    commission_user = UserInstance(commission.user)
                    if commission_user and commission.value > 0:
                        user_key = commission_user.user.id
                        if user_key not in batch_data:
                            batch_data[user_key] = {
                                'user': commission_user,
                                'total_value': 0,
                                'commissions': []
                            }
                        batch_data[user_key]['total_value'] += float(commission.value)
                        batch_data[user_key]['commissions'].append(commission)
            
            # Gera uma linha para cada usuário com valor total
            cod_counter = 1
            for user_id, data in batch_data.items():
                user: UserInstance = data['user']
                total_value = data['total_value']
                
                # Dados da linha do lote
                batch_row = [
                    cod_counter,  # Cod
                    'EMAIL',  # Tipo de Chave (padrão EMAIL)
                    user.email if user.email else '',  # Chave PIX (email do usuário)
                    user.cpf if user.cpf else '',  # CPF ou CNPJ
                    total_value,  # Valor
                    user.email if user.email else '',  # Email
                    f'USER_{user.user.id}',  # ID integração
                    f'Pagamento comissões - {user.name}',  # Descrição Pix
                    ''  # Data de agendamento (vazio)
                ]
                
                for col, value in enumerate(batch_row, 1):
                    cell = ws_batch.cell(row=row, column=col, value=value)
                    
                    # Formatação específica por coluna
                    if col == 5:  # Valor
                        cell.number_format = currency_format
                    
                    # Alinhamento
                    if col in [1, 5]:  # Números
                        cell.alignment = Alignment(horizontal="right")
                    else:  # Texto
                        cell.alignment = Alignment(horizontal="left")
                
                row += 1
                cod_counter += 1
            
            # Ajusta largura das colunas do lote
            batch_column_widths = {
                'A': 8, 'B': 15, 'C': 30, 'D': 18, 'E': 15, 
                'F': 30, 'G': 18, 'H': 35, 'I': 20
            }
            
            for col, width in batch_column_widths.items():
                ws_batch.column_dimensions[col].width = width
            
            # Prepara a resposta
            from io import BytesIO
            excel_buffer = BytesIO()
            wb.save(excel_buffer)
            excel_buffer.seek(0)
            
            response = HttpResponse(
                excel_buffer.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="espelho_comissoes_{now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
            
            # Registra a ação de download
            self.log_info(
                request=request,
                action='download_commission_mirror',
                message=f'Usuário fez download do espelho de comissões em XLSX',
                data={
                    'commission_ids': commission_ids_list,
                    'total_records': len(mirror_data),
                    'download': True,
                    'format': 'xlsx'
                }
            )
            
            return response
        else:
            # Para visualização, retorna JSON normal
            self.log_info(
                request=request,
                action='view_commission_mirror',
                message=f'Usuário visualizou o espelho de comissões',
                data={
                    'commission_ids': commission_ids_list,
                    'total_records': len(mirror_data),
                    'download': False
                }
            )
            
            return Response({
                'espelho_comissoes': serializer.data,
                'total_registros': len(mirror_data),
                'gerado_em': now().isoformat(),
                'usuario': request.user.get_full_name()
            })


class CommissionDetailView(BaseApiView):
    """
    API endpoint para recuperar, atualizar e excluir uma comissão específica.
    """
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            permission_classes = [IsAdminOrGerente]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_object(self, pk):
        commission = get_object_or_404(Commission, pk=pk)
        user = self.request.user

        # Verificar se o usuário tem permissão para acessar esta comissão
        if user.role == User.ADMIN:
            return commission
        elif user.role == User.GERENTE and commission.user and commission.user.company != user.company:
            self.permission_denied(self.request)
        elif user.role == User.LIDER and commission.user and commission.user.leader != user and commission.user != user:
            self.permission_denied(self.request)
        elif user.role == User.VENDEDOR and commission.user != user:
            self.permission_denied(self.request)
        elif user.role not in [User.ADMIN, User.GERENTE, User.LIDER, User.VENDEDOR]:
            self.permission_denied(self.request)
            
        return commission
    
    def get(self, request, pk, format=None):
        """
        Recupera os detalhes de uma comissão específica.
        """
        commission = self.get_object(pk)
        serializer = CommissionSerializer(commission)
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='view_comission',
            message=f'Usuário visualizou os detalhes da comissão para a proposta {commission.proposal}',
            data={'comission_id': commission.id}
        )
        
        return Response(serializer.data)
    
    def put(self, request, pk, format=None):
        """
        Atualiza uma comissão específica.
        """
        commission = self.get_object(pk)
        
        # Impedir a edição de comissões pagas
        if commission.payment and commission.payment.status == 'paid':
            return Response(
                {"detail": "Não é possível editar uma comissão já paga."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Captura os dados antes da atualização
        old_data = CommissionSerializer(commission).data
        
        serializer = CommissionSerializer(commission, data=request.data)
        if serializer.is_valid():
            updated_commission = serializer.save()  
            
            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,    
                instance=updated_commission,
                data_before=old_data,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='update_comission',
                message=f'Usuário atualizou a comissão para a proposta {updated_commission.proposal}',
                data={'comission_id': updated_commission.id}
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk, format=None):
        """
        Atualiza parcialmente uma comissão específica.
        """
        commission = self.get_object(pk)
        
        # Impedir a edição de comissões pagas
        if commission.payment and commission.payment.status == 'paid':
            return Response(
                {"detail": "Não é possível editar uma comissão já paga."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Captura os dados antes da atualização
        old_data = CommissionSerializer(commission).data
        
        serializer = CommissionSerializer(commission, data=request.data, partial=True)
        if serializer.is_valid():
            updated_commission = serializer.save()
            
            # Registra a auditoria usando o método da classe base
            self.audit_update(
                request=request,
                instance=updated_commission,
                data_before=old_data,
                data_after=serializer.data
            )
            
            # Registra a ação usando o método da classe base
            self.log_info(
                request=request,
                action='partial_update_comission',
                message=f'Usuário atualizou parcialmente a comissão para a proposta {updated_commission.proposal}',
                data={'comission_id': updated_commission.id, 'fields_updated': list(request.data.keys())}
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk, format=None):
        """
        Exclui uma comissão específica.
        """
        commission = self.get_object(pk)
        
        # Impedir a exclusão de comissões pagas
        if commission.payment and commission.payment.status == 'paid':
            return Response(
                {"detail": "Não é possível excluir uma comissão já paga."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Captura os dados antes da exclusão
        old_data = CommissionSerializer(commission).data
        
        # Registra a auditoria usando o método da classe base
        self.audit_delete(
            request=request,
            instance=commission,
            data_before=old_data
        )
        
        # Registra a ação usando o método da classe base
        self.log_info(
            request=request,
            action='delete_comission',
            message=f'Usuário excluiu a comissão para a proposta {commission.proposal}',
            data={'comission_id': commission.id, 'proposal_id': commission.proposal.id}
        )
        
        commission.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GenerateComissionsView(BaseApiView):
    """
    API endpoint para listar e criar comissões.
    """
    def get_permissions(self):
        permission_classes = [IsAdmin]
        return [permission() for permission in permission_classes]

    def post(self, request, format=None):
        """
        Cria comissões usando a pipeline de geração de comissões.
        """
        try:
            batch_id = request.data.get('batch_id')
            # Instanciar e executar a pipeline
            pipeline = GenerateCommissionsPipeline(batch_id=batch_id)
            result = pipeline.run()
            
            # Verificar se a pipeline foi executada com sucesso
            if result['success']:
                return Response({
                    "detail": "Comissões criadas com sucesso",
                    "statistics": {
                        "total_proposals": result['total_proposals'],
                        "processed_proposals": result['processed_proposals'],
                        "created_commissions": result['created_commissions']
                    }
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "detail": "Erro ao criar comissões",
                    "errors": result['errors'],
                    "statistics": {
                        "total_proposals": result['total_proposals'],
                        "processed_proposals": result['processed_proposals'],
                        "created_commissions": result['created_commissions']
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                "detail": f"Erro interno ao executar pipeline: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CommissionBalanceView(BaseApiView):
    """
    Retorna o saldo de comissão disponível para saque do usuário autenticado.
    Mostra apenas comissões com status 'withdraw_available' (liberadas para saque).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        # Apenas comissões com status 'withdraw_available' são contabilizadas como disponíveis
        available = Commission.objects.filter(
            user=user, 
            release_status=Commission.WITHDRAW_AVAILABLE
        ).aggregate(total=Sum('value'))['total'] or Decimal('0')

        # Comissões aguardando pagamento manual
        pending = Commission.objects.filter(
            user=user, 
            release_status=Commission.PENDING_MANUAL_PAYMENT
        ).aggregate(total=Sum('value'))['total'] or Decimal('0')

        return Response({
            'available': float(available),
            'pending': float(pending),
        })
    
