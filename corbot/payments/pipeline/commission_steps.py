"""
Steps específicos para pipeline de geração de comissões.
"""
import logging
from typing import Any, Dict, List
from core.base.pipeline import Step
from proposals.models import Proposal
from payments.models import Commission, CommissionConfig, CommissionGroup, CommissionRules, CommissionRulesByUser, CommissionGroupByCompany
from core.models import User
from bank.models import Table
from decimal import Decimal

logger = logging.getLogger(__name__)


def _find_range(table, value: Decimal):
    """Retorna a CommissionRange que cobre o valor, ou None se a tabela não tiver faixas.
    Faixas com min_value=0 e max_value=0 são desconsideradas."""
    return table.commission_ranges.exclude(
        min_value=0, max_value=0
    ).filter(
        min_value__lte=value, max_value__gte=value
    ).first()


def _get_user_rule(commission_group, table, value: Decimal):
    """Busca CommissionRulesByUser: tenta por faixa primeiro, depois por tabela."""
    range_obj = _find_range(table, value)
    if range_obj:
        rule = commission_group.commission_rules.filter(commission_range=range_obj).first()
        if rule:
            return rule
    return commission_group.commission_rules.filter(table=table, commission_range__isnull=True).first()


def _get_company_rule(commission_group_company, table, value: Decimal):
    """Busca CommissionRules no grupo por empresa: tenta por faixa primeiro, depois por tabela."""
    range_obj = _find_range(table, value)
    if range_obj:
        rule = commission_group_company.comission_rules.filter(commission_range=range_obj).first()
        if rule:
            return rule
    return commission_group_company.comission_rules.filter(table=table, commission_range__isnull=True).first()


def _get_promotora_rule(commission_group, table, value: Decimal):
    """Busca CommissionRules no grupo promotora: tenta por faixa primeiro, depois por tabela."""
    range_obj = _find_range(table, value)
    if range_obj:
        rule = commission_group.promotora_rules.filter(commission_range=range_obj).first()
        if rule:
            return rule
    return commission_group.promotora_rules.filter(table=table, commission_range__isnull=True).first()


def convert_uuids_to_strings(obj):
    """
    Converte recursivamente objetos UUID para strings em dicionários e listas.
    """
    import uuid
    from decimal import Decimal
    from datetime import datetime, date

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
    elif isinstance(obj, date):
        return obj.isoformat()
    else:
        return obj


class GetProposalsStep(Step):
    """Step para buscar todas as propostas."""

    def __init__(self, batch_id: str | None = None):
        self.name = "GetProposals"
        self.description = "Busca todas as propostas do sistema"
        self.function = self._get_proposals
        self.batch_id = batch_id

    def _get_proposals(self) -> List[Proposal]:
        """Retorna todas as propostas que não foram liberadas."""
        queryset = Proposal.objects.filter(release_date__isnull=True)
        if self.batch_id:
            queryset = queryset.filter(batch_id=self.batch_id)
        return list(queryset)

    def run(self) -> List[Proposal]:
        """Override para não precisar de argumentos."""
        return self.function()


class CalculateCommissionStep(Step):
    """Step para calcular comissões de uma proposta."""

    def __init__(self, proposal: Proposal):
        self.name = "CalculateCommission"
        self.description = "Calcula as comissões para uma proposta específica"
        self.function = self._calculate_commission
        self.proposal = proposal

    def run(self) -> Dict[str, Any]:
        """Override para não precisar de argumentos."""
        return self.function()

    def _calculate_commission(self) -> Dict[str, Any]:
        """Calcula as comissões para uma proposta."""
        value: Decimal = self.proposal.amount
        table: Table|None = self.proposal.table
        user: User|None = self.proposal.seller

        if(not table):
            raise Exception("Não há tabela para a proposta")

        if(not user):
            raise Exception("Não há vendedor para a proposta")

        # Taxa base da tabela para o valor da proposta (considera faixas de comissionamento)
        table_rate: Decimal = table.get_commission_rate_for_amount(value)

        company = user.company
        commission_group_company = CommissionGroupByCompany.objects.filter(companies__id=company.id, is_active=True).first()
        commission_group_user = None
        if user.role == User.VENDEDOR:
            commission_group_user = CommissionGroup.objects.filter(sellers__id=user.id, is_active=True).first()
        elif user.role == User.LIDER:
            commission_group_user = CommissionGroup.objects.filter(leaders__id=user.id, is_active=True).first()
        elif user.role == User.EMPRESA_ADMIN:
            # Corban (empresa_admin) pode ser membro de um grupo promotora via sellers
            commission_group_user = CommissionGroup.objects.filter(sellers__id=user.id, is_active=True).first()

        response = {
            'commission_seller': 0,
            'commission_leader': 0,
            'commission_company': 0,
            'percentage_seller': 0,
            'percentage_leader': 0,
            'percentage_company': 0,
            'commission_group_company_config': None,
            'commission_group_user_config': None,
            'table_config': None,
            'proposal': self.proposal,
            'seller_is_leader': user.role == User.LIDER,
            'seller_is_gerente': user.role == User.GERENTE,
            'seller_is_empresa_admin': user.role == User.EMPRESA_ADMIN,
        }
        logger.info(f"Calculando comissão para a proposta {self.proposal.id}")

        # ──────────────────────────────────────────────────────────────────────
        # Grupo da Promotora (company=None): taxa única → empresa do corban
        # A promotora define quanto paga ao corban; o corban distribui internamente.
        # ──────────────────────────────────────────────────────────────────────
        if commission_group_user and commission_group_user.company is None:
            promotora_rule = _get_promotora_rule(commission_group_user, table, value)
            rate = promotora_rule.commission_rate if promotora_rule else table_rate
            response['commission_company'] = rate * value / 100
            response['percentage_company'] = rate
            response['table_config'] = table.get_config()
            response['commission_group_user_config'] = commission_group_user.get_config()
            logger.info(
                f"Grupo promotora: taxa {rate}% → empresa {company.id}"
            )
            return response

        # ──────────────────────────────────────────────────────────────────────
        # Fluxo normal: grupo corban (company=user.company) ou sem grupo
        # ──────────────────────────────────────────────────────────────────────
        # calculando a comissão do vendedor
        if user.role == User.VENDEDOR:
            if not commission_group_user:
                logger.debug(f"Não há grupo de comissão para o vendedor {user.id}")
                # Se não houver grupo de comissão para o vendedor,
                # usa o grupo da empresa e paga somente a comissão da empresa
                company_rule = _get_company_rule(commission_group_company, table, value) if commission_group_company else None
                if(not company_rule):
                    logger.debug(f"Não há regra de comissão para a tabela {table.id}")
                    response['commission_company'] = table_rate * value / 100
                    response['percentage_company'] = table_rate
                    logger.debug(f"Comissão da empresa: {response['commission_company']}")
                    logger.debug(f"Porcentagem da empresa: {response['percentage_company']}")
                    response['table_config'] = table.get_config()
                else:
                    logger.debug(f"Há regra de comissão para a tabela {table.id}")
                    response['commission_company'] = company_rule.commission_rate * value / 100
                    response['percentage_company'] = company_rule.commission_rate
                    response['commission_group_company_config'] = commission_group_company.get_config()
                    response['table_config'] = table.get_config()
            else:
                # Se houver grupo de comissão para o vendedor,
                # usa o grupo de comissão do vendedor e paga a comissão do vendedor e da empresa
                rule = _get_user_rule(commission_group_user, table, value)
                if rule:
                    logger.debug(f"Há regra de comissão para a tabela {table.id}")
                    # Se houver regra para a tabela, paga a comissão para o vendedor e a comissão da empresa
                    company_rule = _get_company_rule(commission_group_company, table, value) if commission_group_company else None
                    response['commission_seller'] = rule.seller_commission_rate * value / 100
                    response['percentage_seller'] = rule.seller_commission_rate
                    response['commission_group_user_config'] = commission_group_user.get_config()
                    response['table_config'] = table.get_config()
                    if(company_rule):
                        logger.debug(f"Há regra de comissão para a tabela {table.id}")
                        response['commission_company'] = (company_rule.commission_rate - (rule.seller_commission_rate + rule.leader_commission_rate)) * value / 100
                        response['commission_group_company_config'] = commission_group_company.get_config()
                    else:
                        logger.debug(f"Não há regra de comissão para a tabela {table.id}")
                        response['commission_company'] = (table_rate - (rule.seller_commission_rate + rule.leader_commission_rate)) * value / 100
                        response['commission_group_company_config'] = table.get_config()
                else:
                    company_rule = _get_company_rule(commission_group_company, table, value) if commission_group_company else None
                    if(company_rule):
                        logger.debug(f"Há regra de comissão para a tabela {table.id}")
                        response['commission_company'] = company_rule.commission_rate * value / 100
                        response['percentage_company'] = company_rule.commission_rate
                        response['table_config'] = table.get_config()
                        response['commission_group_company_config'] = commission_group_company.get_config()
                    else:
                        logger.debug(f"Não há regra de comissão para a tabela {table.id}")
                        response['commission_company'] = table_rate * value / 100
                        response['percentage_company'] = table_rate
                        response['table_config'] = table.get_config()
                # Se houver líder, paga a comissão do líder
                leader = user.leader
                if leader:
                    logger.debug(f"Há líder para a proposta {self.proposal.id}")
                    # Se não houver regra para a tabela, paga a comissão da empresa
                    if(not rule):
                        logger.debug(f"Não há regra de comissão para a tabela {table.id}")
                        company_rule = _get_company_rule(commission_group_company, table, value) if commission_group_company else None
                        if(company_rule):
                            response['commission_company'] = company_rule.commission_rate * value / 100
                            response['percentage_company'] = company_rule.commission_rate
                            response['table_config'] = table.get_config()
                            response['commission_group_company_config'] = commission_group_company.get_config()
                        else:
                            logger.debug(f"Não há regra de comissão para a tabela {table.id}")
                            response['commission_company'] = table_rate * value / 100
                            response['percentage_company'] = table_rate
                            response['table_config'] = table.get_config()
                    else:
                        logger.debug(f"Há regra de comissão para a tabela {table.id}")
                        # Se houver regra para a tabela, paga a comissão para o líder
                        company_rule = _get_company_rule(commission_group_company, table, value) if commission_group_company else None
                        response['commission_leader'] = rule.leader_commission_rate * value / 100
                        response['percentage_leader'] = rule.leader_commission_rate
                        if company_rule:
                            logger.debug(f"Há regra de comissão para a tabela {table.id}")
                            response['commission_company'] = (company_rule.commission_rate - (rule.leader_commission_rate + rule.seller_commission_rate)) * value / 100
                            response['percentage_company'] = company_rule.commission_rate - (rule.leader_commission_rate + rule.seller_commission_rate)
                            response['commission_group_company_config'] = commission_group_company.get_config()
                        else:
                            logger.debug(f"Não há regra de comissão para a tabela {table.id}")
                            response['commission_company'] = (table_rate - (rule.leader_commission_rate + rule.seller_commission_rate)) * value / 100
                            response['percentage_company'] = table_rate - (rule.leader_commission_rate + rule.seller_commission_rate)
                        response['table_config'] = table.get_config()
                        response['commission_group_user_config'] = commission_group_user.get_config()

        elif(user.role == User.LIDER):
            logger.info(f"Calculando comissão para o líder {user.id}")
            rule = _get_user_rule(commission_group_user, table, value) if commission_group_user else None
            if(not rule):
                logger.debug(f"Não há regra de comissão para a tabela {table.id}")
                company_rule = _get_company_rule(commission_group_company, table, value) if commission_group_company else None
                if(company_rule):
                    logger.debug(f"Há regra de comissão para a tabela {table.id}")
                    response['commission_company'] = company_rule.commission_rate * value / 100
                    response['percentage_company'] = company_rule.commission_rate
                    response['table_config'] = table.get_config()
                    response['commission_group_company_config'] = commission_group_company.get_config()
                else:
                    logger.debug(f"Não há regra de comissão para a tabela {table.id}")
                    response['commission_company'] = table_rate * value / 100
                    response['percentage_company'] = table_rate
                    response['table_config'] = table.get_config()
            else:
                logger.debug(f"Há regra de comissão para a tabela {table.id}")
                company_rule = _get_company_rule(commission_group_company, table, value) if commission_group_company else None
                response['commission_leader'] = (rule.leader_commission_rate + rule.seller_commission_rate) * value / 100
                response['percentage_leader'] = rule.leader_commission_rate + rule.seller_commission_rate
                if company_rule:
                    response['commission_company'] = (company_rule.commission_rate - (rule.leader_commission_rate + rule.seller_commission_rate)) * value / 100
                    response['percentage_company'] = company_rule.commission_rate - (rule.leader_commission_rate + rule.seller_commission_rate)
                    response['commission_group_company_config'] = commission_group_company.get_config()
                else:
                    response['commission_company'] = (table_rate - (rule.leader_commission_rate + rule.seller_commission_rate)) * value / 100
                    response['percentage_company'] = table_rate - (rule.leader_commission_rate + rule.seller_commission_rate)
                response['table_config'] = table.get_config()
                response['commission_group_user_config'] = commission_group_user.get_config()

        elif(user.role == User.GERENTE):
            logger.info(f"Calculando comissão para o gerente {user.id}")
            company_rule = _get_company_rule(commission_group_company, table, value) if commission_group_company else None
            rate = company_rule.commission_rate if company_rule else table_rate
            # Gerente trabalhando sozinho: recebe a comissão inteira como "seller"
            response['commission_seller'] = rate * value / 100
            response['percentage_seller'] = rate
            response['table_config'] = table.get_config()
            if company_rule:
                response['commission_group_company_config'] = commission_group_company.get_config()

        elif(user.role == User.EMPRESA_ADMIN):
            logger.info(f"Calculando comissão para o empresa_admin {user.id}")
            company_rule = _get_company_rule(commission_group_company, table, value) if commission_group_company else None
            rate = company_rule.commission_rate if company_rule else table_rate
            # Empresa admin trabalhando sozinho: recebe a comissão inteira como "seller"
            response['commission_seller'] = rate * value / 100
            response['percentage_seller'] = rate
            response['table_config'] = table.get_config()
            if company_rule:
                response['commission_group_company_config'] = commission_group_company.get_config()

        return response


class ConvertUUIdsStep(Step):
    """Step para converter UUIDs para strings."""

    def __init__(self, proposal: Proposal):
        self.name = "ConvertUUIDs"
        self.description = "Converte UUIDs para strings nos dados de configuração"
        self.function = self._convert_uuids
        self.proposal = proposal
        self.data = None

    def run(self) -> Dict[str, Any]:
        """Override para não precisar de argumentos."""
        return self.function()

    def _convert_uuids(self) -> Dict[str, Any]:
        """Converte UUIDs para strings."""
        if self.data is None:
            return {}

        self.data['user_config'] = convert_uuids_to_strings(self.data['commission_group_user_config']) if self.data.get('commission_group_user_config') else None
        self.data['table_config'] = convert_uuids_to_strings(self.data['table_config']) if self.data.get('table_config') else None
        self.data['company_config'] = convert_uuids_to_strings(self.data['commission_group_company_config']) if self.data.get('commission_group_company_config') else None
        return self.data


class CreateCommissionConfigStep(Step):
    """Step para criar CommissionConfig."""

    def __init__(self, proposal: Proposal):
        self.name = "CreateCommissionConfig"
        self.description = "Cria e salva a configuração de comissão"
        self.function = self._create_commission_config
        self.proposal = proposal
        self.data = None

    def run(self) -> Dict[str, Any]:
        """Override para não precisar de argumentos."""
        return self.function()

    def _create_commission_config(self) -> Dict[str, Any]:
        """Cria a configuração de comissão."""
        if self.data is None:
            return {}

        commission_config = CommissionConfig(
            commision_group_user_config=self.data.get('user_config'),
            table_config=self.data.get('table_config'),
            commision_group_company_config=self.data.get('company_config')
        )
        commission_config.save()
        self.data['commission_config'] = commission_config
        return self.data


class CreateSellerCommissionStep(Step):
    """Step para criar comissão do vendedor."""

    def __init__(self, proposal: Proposal):
        self.name = "CreateSellerCommission"
        self.description = "Cria a comissão do vendedor"
        self.function = self._create_seller_commission
        self.proposal = proposal
        self.data = None

    def run(self) -> Dict[str, Any]:
        """Override para não precisar de argumentos."""
        return self.function()

    def _create_seller_commission(self) -> Dict[str, Any]:
        """Cria a comissão do vendedor/pessoa que vendeu."""
        if self.data is None:
            return {}

        proposal = self.data['proposal']
        commission_config = self.data['commission_config']

        if self.data.get('commission_seller', 0) > 0:
            # Determinar o role da comissão baseado no role do seller
            seller_role = proposal.seller.role
            if seller_role in (User.GERENTE, User.EMPRESA_ADMIN):
                # Gerente/Empresa admin trabalhando sozinho — comissão vai como EMPRESA
                commission_role = Commission.EMPRESA
            elif seller_role == User.LIDER:
                commission_role = Commission.LIDER
            else:
                commission_role = Commission.VENDEDOR

            commission = Commission(
                proposal=proposal,
                user=proposal.seller,
                company=proposal.company,
                role=commission_role,
                value=self.data['commission_seller'],
                percentage=self.data['percentage_seller'],
                commission_config=commission_config
            )
            commission.save()
            self.data['seller_commission'] = commission
        return self.data


class CreateLeaderCommissionStep(Step):
    """Step para criar comissão do lider."""

    def __init__(self, proposal: Proposal):
        self.name = "CreateLeaderCommission"
        self.description = "Cria a comissão do líder se existir"
        self.function = self._create_leader_commission
        self.proposal = proposal
        self.data = None

    def run(self) -> Dict[str, Any]:
        """Override para não precisar de argumentos."""
        return self.function()

    def _create_leader_commission(self) -> Dict[str, Any]:
        """Cria a comissão do líder se existir."""
        if self.data is None:
            return {}

        proposal = self.data['proposal']
        commission_config = self.data['commission_config']

        if self.data.get('commission_leader', 0) > 0:
            # Se o seller É o líder, a comissão vai para ele mesmo
            if self.data.get('seller_is_leader'):
                leader_user = proposal.seller
            elif proposal.seller.leader:
                leader_user = proposal.seller.leader
            else:
                return self.data

            commission = Commission(
                proposal=proposal,
                user=leader_user,
                company=proposal.company,
                role=Commission.LIDER,
                value=self.data['commission_leader'],
                percentage=self.data['percentage_leader'],
                commission_config=commission_config
            )
            commission.save()
            self.data['leader_commission'] = commission

        return self.data


class CreateCompanyCommissionStep(Step):
    """Step para criar comissão da empresa."""

    def __init__(self, proposal: Proposal):
        self.name = "CreateCompanyCommission"
        self.description = "Cria a comissão da empresa"
        self.function = self._create_company_commission
        self.proposal = proposal
        self.data = None

    def run(self) -> Dict[str, Any]:
        """Override para não precisar de argumentos."""
        return self.function()

    def _create_company_commission(self) -> Dict[str, Any]:
        """Cria a comissão da empresa."""
        if self.data is None:
            return {}

        proposal = self.data['proposal']
        commission_config = self.data['commission_config']

        if self.data.get('commission_company', 0) > 0:
            commission = Commission(
                proposal=proposal,
                user=proposal.seller,
                company=proposal.company,
                role=Commission.EMPRESA,
                value=self.data['commission_company'],
                percentage=self.data['percentage_company'],
                commission_config=commission_config
            )
            commission.save()
            self.data['company_commission'] = commission
        return self.data
