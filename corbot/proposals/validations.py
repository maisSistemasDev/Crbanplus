from proposals.models import Proposal, Layout, Agreement, Table, Bank, LayoutField, StatusPayment
from bank_access.models import BankAccess
from django.db.models import Q
from typing import Callable
import hashlib
from .utils import extract_emails, convert_value
from datetime import datetime
import pandas as pd

class LayoutValidation:
    def __init__(self, layout:Layout):
        self.layout = layout
        self.proposal = Proposal()
        self.Bank = Bank
        self.Agreement = Agreement
        self.Table = Table
        self.BankAccess = BankAccess
        self.StatusPayment = StatusPayment
    def _ensure_valid_date(self, date_value, field_name="data"):
        """
        Garante que um valor de data seja convertido para um objeto date Python válido
        para uso com Django ORM, evitando problemas com pandas Timestamp
        """
        if date_value is None:
            return None
            
        try:
            if isinstance(date_value, pd.Timestamp):
                return date_value.to_pydatetime().date()
            elif isinstance(date_value, datetime):
                return date_value.date()
            elif isinstance(date_value, str):
                # Tentar diferentes formatos de string
                try:
                    return datetime.strptime(date_value, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        return pd.to_datetime(date_value).date()
                    except Exception:
                        raise Exception(f'Formato de data inválido para {field_name}: {date_value}')
            else:
                # Se já for um objeto date válido, retorna como está
                return date_value
        except Exception as e:
            raise Exception(f'Erro ao processar {field_name}: {e}')
        
    def construct_proposal(self, proposal_data:dict):
        try:
            self.proposal.original_data = proposal_data
            values = list(proposal_data.values())
            
            # Verificação de segurança para campos obrigatórios
            required_fields = ['disbursement_date', 'amount', 'client_document', 'contract_number', 'client_name', 'agreement', 'table', 'seller']
            
            for field_name in required_fields:
                field_mapping = self.layout.map_fields.filter(name=field_name).first()
                if not field_mapping:
                    raise Exception(f'Campo obrigatório "{field_name}" não encontrado no mapeamento do layout')
                
                if field_mapping.index >= len(values):
                    raise Exception(f'Índice do campo "{field_name}" ({field_mapping.index}) excede o número de valores disponíveis ({len(values)})')
            
            # Conversão dos campos com verificação de tipos
            disbursement_field = self.layout.map_fields.filter(name='disbursement_date').first()
            disbursement_value = values[disbursement_field.index]
            self.proposal.disbursement_date = convert_value(disbursement_value, 'date')
            amount_field = self.layout.map_fields.filter(name='amount').first()
            amount_value = values[amount_field.index]
            self.proposal.amount = convert_value(amount_value, amount_field.data_type)
            
            client_doc_field = self.layout.map_fields.filter(name='client_document').first()
            client_doc_value = values[client_doc_field.index]
            self.proposal.client_document = convert_value(client_doc_value, client_doc_field.data_type)
            
            contract_field = self.layout.map_fields.filter(name='contract_number').first()
            contract_value = values[contract_field.index]
            self.proposal.contract_number = convert_value(contract_value, contract_field.data_type)
            
            client_name_field = self.layout.map_fields.filter(name='client_name').first()
            client_name_value = values[client_name_field.index]
            self.proposal.client_name = convert_value(client_name_value, client_name_field.data_type)

            # Validar que o layout tem um banco associado e atribuir ANTES de usar
            if not self.layout.bank:
                raise Exception('Layout não possui um banco associado. Configure o banco para este layout.')
            self.proposal.bank = self.layout.bank

            # Agora posso obter o status (que precisa do banco)
            status_field = self.layout.map_fields.filter(name='status').first()
            status_value = values[status_field.index]
            self.proposal.status = self.get_status(status_value)
            
            agreement_field = self.layout.map_fields.filter(name='agreement').first()
            agreement_value = values[agreement_field.index]
            self.proposal.agreement = self.get_agreement(agreement_value)
            
            table_field = self.layout.map_fields.filter(name='table').first()
            table_value = values[table_field.index]
            self.proposal.table = self.get_table(self.proposal.amount, table_value)
            
            seller_field = self.layout.map_fields.filter(name='seller').first()
            seller_value = values[seller_field.index]
            self.proposal.seller = self.get_user(seller_value)
            
            self.proposal.company = self.proposal.seller.company
            self.proposal.status = 'pending'
            self.proposal.uploaded_at = datetime.now()
            
            return self.proposal
        except Exception as e:
            raise Exception(f'Erro ao construir proposta: {e}')
        
    def get_table(self, amount:float, name_in_bank:str):
        try:
            # 1. Buscar tabela pelo nome exato
            tables = Table.objects.filter(name_in_bank=name_in_bank)

            # 2. Se não existir, buscar em todas e procurar nos aliases em Python
            if not tables.exists():
                all_tables = Table.objects.all()
                matched_tables = []
                name_lower = name_in_bank.lower().strip()
                for table in all_tables:
                    if isinstance(table.alias, list):
                        for alias in table.alias:
                            if name_lower == str(alias).lower().strip():
                                matched_tables.append(table)
                                break
                tables = matched_tables

            if not tables:
                raise Exception(f'Tabela não encontrada: {name_in_bank}')

            # 3. Filtrar tabelas válidas pelo valor — verifica faixas (CommissionRange)
            #    e faz fallback para campos legados se não houver faixas.
            from decimal import Decimal
            amount_decimal = Decimal(str(amount))

            def _table_covers_amount(table):
                # Ignora faixas com min=0 e max=0 (placeholders sem valor definido)
                ranges = list(table.commission_ranges.exclude(
                    min_value=0, max_value=0
                ).order_by('min_value'))
                if ranges:
                    return any(cr.min_value <= amount_decimal <= cr.max_value for cr in ranges)
                # fallback legado
                if table.min_value is None and table.max_value is None:
                    return True
                min_v = table.min_value or Decimal('0')
                max_v = table.max_value or Decimal('0')
                return (min_v <= amount_decimal <= max_v) or (max_v == 0 and min_v == 0)

            valid_tables = [t for t in tables if _table_covers_amount(t)]

            if not valid_tables:
                raise Exception(f'Nenhuma tabela válida encontrada para o valor {amount}: {name_in_bank}')

            # 4. Aplicar lógica de vigência
            # Filtrar apenas tabelas ativas e com vigência <= data de desembolso
            active_tables = [t for t in valid_tables if t.is_active and t.vigency_date <= self.proposal.disbursement_date]

            if not active_tables:
                active_tables = valid_tables

            # Encontrar a tabela com maior vigência
            max_vigency_date = max(t.vigency_date for t in active_tables)
            max_vigency_tables = [t for t in active_tables if t.vigency_date == max_vigency_date]

            # Se há apenas uma tabela com a maior vigência, retorna ela
            if len(max_vigency_tables) == 1:
                return max_vigency_tables[0]

            # Se há múltiplas tabelas com a mesma vigência máxima, retorna a primeira
            return max_vigency_tables[0]

        except Exception as e:
            raise Exception(f'Erro ao buscar tabela: {e}')
        
    def get_agreement(self, name):
        name = name.lower().strip()
        if not name:
            raise Exception(f'Convênio não encontrado: {name}')

        # Buscar por nome exato
        agreement = Agreement.objects.filter(name__icontains=name).first()
        if agreement:
            return agreement

        # Buscar em aliases (em Python, compatível com SQLite)
        all_agreements = Agreement.objects.all()
        for agreement in all_agreements:
            if isinstance(agreement.alias, list):
                for alias in agreement.alias:
                    if name == str(alias).lower().strip():
                        return agreement

        raise Exception(f'❌ Convênio não encontrado: "{name}"')
        
    def get_user(self, login):
        if not login or login == 'nan':
            raise Exception(f'❌ Vendedor não mapeado: "{login}" - Realize o mapeamento na resolução de valores')

        value = str(login).strip()
        emails = extract_emails(value)
        value = emails[0].lower() if len(emails) > 0 else value.lower()

        # Buscar por username exato
        bank_access = BankAccess.objects.filter(username=value).first()
        if bank_access:
            return bank_access.user

        # Buscar por username contendo o email
        bank_access = BankAccess.objects.filter(username__icontains=value).first()
        if bank_access:
            return bank_access.user

        # Buscar em aliases (em Python, compatível com SQLite)
        # Compara tanto o alias completo quanto o email extraído do alias
        all_accesses = BankAccess.objects.all()
        for access in all_accesses:
            if isinstance(access.alias, list):
                for alias in access.alias:
                    alias_str = str(alias).lower().strip()
                    if value == alias_str:
                        return access.user
                    # Extrai email do alias (ex: "email@dom.com (Nome)") e compara
                    alias_emails = extract_emails(alias_str)
                    if alias_emails and value == alias_emails[0].lower():
                        return access.user

        raise Exception(f'❌ Vendedor não mapeado: "{login}" - Realize o mapeamento na resolução de valores')

    def get_status(self, name):
        if not self.proposal.bank:
            raise Exception('Banco não foi definido na proposta. Verifique se o layout possui um banco associado.')

        status = self.StatusPayment.objects.filter(bank=self.proposal.bank, alias__contains=name).first()
        if status:
            return status
        else:
            raise Exception(f'❌ Status não encontrado: "{name}" para o banco {self.proposal.bank.name}')

class ProposalValidation:
    def __init__(self, proposal:dict, layout:Layout):
        self.proposal_data = proposal
        self.layout = layout
        self.last_error = None
        self.proposal:Proposal|None = None
        self.pipeline = [
            self.construct_proposal,
            self.validate_proposal_duplicated,
        ]
    
    def validate_proposal(self):
        for func in self.pipeline:
            try:
                func()
            except Exception as e:
                self.last_error = e
                return False
        return True
        
    def _hash(self):
        hash_string = str(self.proposal.disbursement_date) + str(self.proposal.amount) + str(self.proposal.client_document)
        Proposal.objects.filter(id=self.proposal.id).update(hash=hashlib.sha256(hash_string.encode()).hexdigest())
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    @property
    def is_duplicated(self):
        existing_proposal = (Proposal.objects.filter(hash=self._hash()).exists() 
                             or 
                             Proposal.objects.filter(contract_number=self.proposal.contract_number).exists())
        if existing_proposal:
            return True
        self.proposal.hash = self._hash()
        return False
    
    def validate_proposal_duplicated(self):
        if self.is_duplicated:
            raise Exception("Proposta duplicada - Hash: " + self._hash())
        return True
    
    def construct_proposal(self):  
        self.proposal = LayoutValidation(self.layout).construct_proposal(self.proposal_data)
        

