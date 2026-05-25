"""
Views para importação e exportação de CSV de grupos de comissionamento.
"""
from decimal import Decimal
from rest_framework.response import Response
from rest_framework import status, permissions
from django.http import HttpResponse
import csv
import io
import logging

from core.base_views import BaseApiView
from core.permissions import IsAdminOrGerenteOrLider
from core.models import User
from payments.models import CommissionGroup, CommissionGroupByCompany, CommissionRulesByUser
from bank.models import Bank, Table, normalize_name

logger = logging.getLogger(__name__)


class CommissionGroupExportCSVView(BaseApiView):
    """
    API endpoint para exportar template CSV para criar/editar regras de comissionamento.
    Exporta todas as tabelas disponíveis com campos para preencher as comissões.
    """
    permission_classes = [IsAdminOrGerenteOrLider]

    def get(self, request, format=None):
        """
        Gera um CSV com todas as tabelas para configurar comissões do grupo.
        Formato: banco;convenio;tabela;comissao_lider;comissao_vendedor
        """
        try:
            user = request.user
            
            # Buscar tabelas disponíveis baseado no papel do usuário
            if user.role == User.ADMIN:
                # Admin pode ver todas as tabelas
                tables = Table.objects.filter(is_active=True).select_related('bank', 'agreement')
            elif user.role in [User.GERENTE, User.EMPRESA_ADMIN, User.LIDER]:
                # Gerente/Líder vê apenas tabelas do CommissionGroupByCompany da sua empresa
                company_group = CommissionGroupByCompany.objects.filter(
                    companies=user.company,
                    is_active=True
                ).first()
                
                if not company_group:
                    return Response(
                        {"detail": "Empresa não possui grupo de comissionamento configurado pela promotora."},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Pegar apenas as tabelas que estão nas regras da promotora
                table_ids = company_group.comission_rules.values_list('table_id', flat=True)
                tables = Table.objects.filter(id__in=table_ids, is_active=True).select_related('bank', 'agreement')
            else:
                return Response(
                    {"detail": "Usuário não tem permissão para exportar CSV."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="template_grupo_comissionamento.csv"'
            
            # Adicionar BOM para UTF-8
            response.write('\ufeff')
            
            writer = csv.writer(response, delimiter=';')
            
            # Cabeçalho
            writer.writerow([
                'banco',
                'convenio',
                'tabela',
                'comissao_lider',
                'comissao_vendedor'
            ])
            
            # Dados das tabelas (com comissões vazias para preencher)
            for table in tables.order_by('bank__name', 'agreement__name', 'name_in_bank'):
                writer.writerow([
                    table.bank.name,
                    table.agreement.name,
                    table.name_in_bank or '',
                    '',  # comissao_lider - para preencher
                    ''   # comissao_vendedor - para preencher
                ])
            
            # Registrar ação
            self.log_info(
                request=request,
                action='export_commission_group_csv',
                message=f'Usuário exportou template CSV com {tables.count()} tabelas',
                data={'tables_count': tables.count()}
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Erro ao exportar CSV: {str(e)}")
            return Response(
                {"detail": f"Erro ao exportar CSV: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CommissionGroupImportCSVView(BaseApiView):
    """
    API endpoint para importar regras de comissionamento via CSV.
    Cria ou atualiza as regras de um grupo de comissionamento.
    """
    permission_classes = [IsAdminOrGerenteOrLider]

    def post(self, request, group_id=None, format=None):
        """
        Importa regras de comissionamento de um CSV para um grupo específico.
        Formato esperado: banco;convenio;tabela;comissao_lider;comissao_vendedor
        """
        file = request.FILES.get('file')
        
        if not file:
            return Response({"detail": "Arquivo não encontrado."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not group_id:
            return Response({"detail": "ID do grupo não informado."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Buscar grupo de comissionamento
            try:
                group = CommissionGroup.objects.get(id=group_id)
            except CommissionGroup.DoesNotExist:
                return Response({"detail": "Grupo de comissionamento não encontrado."}, status=status.HTTP_404_NOT_FOUND)
            
            # Verificar permissão do usuário
            user = request.user
            if user.role not in [User.ADMIN, User.GERENTE, User.EMPRESA_ADMIN, User.LIDER]:
                return Response({"detail": "Sem permissão."}, status=status.HTTP_403_FORBIDDEN)
            
            if user.role != User.ADMIN and group.company != user.company:
                return Response({"detail": "Grupo pertence a outra empresa."}, status=status.HTTP_403_FORBIDDEN)
            
            # Decodificar arquivo
            file_data = file.read().decode('utf-8')
            io_string = io.StringIO(file_data)
            reader = csv.reader(io_string, delimiter=';')
            
            created_rules = []
            updated_rules = []
            errors = []
            line_number = 0
            
            for row in reader:
                line_number += 1
                
                # Pular cabeçalho
                if line_number == 1 and any(header in row[0].lower() for header in ['banco', 'convenio', 'tabela']):
                    continue
                
                try:
                    # Validar linha
                    if len(row) < 5:
                        errors.append(f"Linha {line_number}: Dados insuficientes (esperado 5 campos, encontrado {len(row)})")
                        continue
                    
                    # Normalizar nomes
                    bank_name_normalized = normalize_name(row[0].strip())
                    agreement_name_normalized = normalize_name(row[1].strip())
                    table_name_normalized = normalize_name(row[2].strip())
                    
                    if not all([bank_name_normalized, agreement_name_normalized, table_name_normalized]):
                        errors.append(f"Linha {line_number}: Banco, convênio ou tabela vazio")
                        continue
                    
                    # Buscar banco
                    bank = Bank.objects.filter(name__iexact=bank_name_normalized).first()
                    if not bank:
                        errors.append(f"Linha {line_number}: Banco '{row[0]}' não encontrado")
                        continue
                    
                    # Buscar convênio
                    agreement = bank.agreements.filter(name__iexact=agreement_name_normalized).first()
                    if not agreement:
                        errors.append(f"Linha {line_number}: Convênio '{row[1]}' não encontrado no banco '{bank.name}'")
                        continue
                    
                    # Buscar tabela
                    table = Table.objects.filter(
                        bank=bank,
                        agreement=agreement,
                        name_in_bank__iexact=table_name_normalized
                    ).first()
                    
                    if not table:
                        errors.append(f"Linha {line_number}: Tabela '{row[2]}' não encontrada")
                        continue
                    
                    # Processar comissões
                    try:
                        leader_rate = Decimal(row[3].strip().replace(',', '.')) if row[3].strip() else Decimal('0')
                        seller_rate = Decimal(row[4].strip().replace(',', '.')) if row[4].strip() else Decimal('0')
                    except (ValueError, Exception) as e:
                        errors.append(f"Linha {line_number}: Erro nos valores de comissão - {str(e)}")
                        continue
                    
                    # Validar limites (se não for admin)
                    if user.role != User.ADMIN:
                        company_group = CommissionGroupByCompany.objects.filter(
                            companies=group.company,
                            is_active=True
                        ).first()
                        
                        if company_group:
                            max_rule = company_group.comission_rules.filter(table=table).first()
                            if max_rule and (leader_rate + seller_rate) > max_rule.commission_rate:
                                errors.append(
                                    f"Linha {line_number}: Soma das comissões ({leader_rate + seller_rate}%) "
                                    f"excede o limite da promotora ({max_rule.commission_rate}%) para tabela '{table.name_in_bank}'"
                                )
                                continue
                    
                    # Buscar ou criar regra
                    rule = CommissionRulesByUser.objects.filter(
                        bank=bank,
                        table=table
                    ).first()
                    
                    if rule and rule in group.commission_rules.all():
                        # Atualizar regra existente
                        rule.leader_commission_rate = leader_rate
                        rule.seller_commission_rate = seller_rate
                        rule.save()
                        
                        updated_rules.append({
                            'bank': bank.name,
                            'table': table.name_in_bank,
                            'leader_rate': float(leader_rate),
                            'seller_rate': float(seller_rate)
                        })
                    else:
                        # Criar nova regra
                        rule = CommissionRulesByUser.objects.create(
                            bank=bank,
                            table=table,
                            leader_commission_rate=leader_rate,
                            seller_commission_rate=seller_rate
                        )
                        group.commission_rules.add(rule)
                        
                        created_rules.append({
                            'bank': bank.name,
                            'table': table.name_in_bank,
                            'leader_rate': float(leader_rate),
                            'seller_rate': float(seller_rate)
                        })
                
                except Exception as e:
                    logger.error(f"Erro na linha {line_number}: {str(e)}")
                    errors.append(f"Linha {line_number}: Erro inesperado - {str(e)}")
                    continue
            
            # Preparar resposta
            response_data = {
                "created_count": len(created_rules),
                "updated_count": len(updated_rules),
                "created_rules": created_rules,
                "updated_rules": updated_rules,
                "errors_count": len(errors),
                "errors": errors
            }
            
            if errors:
                if created_rules or updated_rules:
                    response_data["detail"] = f"Processo concluído com {len(created_rules)} regras criadas, {len(updated_rules)} atualizadas e {len(errors)} erros."
                    return Response(response_data, status=status.HTTP_207_MULTI_STATUS)
                else:
                    response_data["detail"] = "Nenhuma regra foi criada/atualizada devido aos erros encontrados."
                    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
            else:
                response_data["detail"] = f"Processo concluído: {len(created_rules)} regras criadas, {len(updated_rules)} atualizadas."
                
                # Registrar ação
                self.log_info(
                    request=request,
                    action='import_commission_group_csv',
                    message=f'Usuário importou regras via CSV para grupo {group.name}: {len(created_rules)} criadas, {len(updated_rules)} atualizadas',
                    data={'group_id': group_id, 'created_count': len(created_rules), 'updated_count': len(updated_rules)}
                )
                
                return Response(response_data, status=status.HTTP_201_CREATED)
        
        except UnicodeDecodeError:
            return Response(
                {"detail": "Erro ao decodificar arquivo. Certifique-se de que o arquivo está codificado em UTF-8."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erro ao processar arquivo: {str(e)}")
            return Response(
                {"detail": f"Erro ao processar arquivo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
