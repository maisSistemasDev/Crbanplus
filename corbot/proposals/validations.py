from proposals.models import Proposal, Layout, Agreement, Table, Bank, LayoutField, StatusPayment
from bank_access.models import BankAccess
from django.db.models import Q
from typing import Callable
import hashlib
from .utils import extract_emails, convert_value, parse_brazilian_date
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
        self._matcher = None

    def _get_matcher(self):
        if self._matcher is None:
            from .preview_matcher import BatchPreviewMatcher
            bank = getattr(self.proposal, 'bank', None) or self.layout.bank
            self._matcher = BatchPreviewMatcher(bank)
        return self._matcher
    def _ensure_valid_date(self, date_value, field_name="data"):
        """
        Garante que um valor de data seja convertido para um objeto date Python válido
        para uso com Django ORM, evitando problemas com pandas Timestamp
        """
        if date_value is None:
            return None

        try:
            parsed = parse_brazilian_date(date_value)
            if parsed is None:
                raise Exception(f'Formato de data inválido para {field_name}: {date_value}')
            return parsed
        except Exception as e:
            raise Exception(f'Erro ao processar {field_name}: {e}')

    def _get_field_value(self, proposal_data: dict, field: LayoutField):
        """Busca valor pelo header_name/nome do campo (CSV/ETL), com fallback posicional legado."""
        if not field:
            return None

        if isinstance(proposal_data, dict):
            for key in (field.header_name, field.name):
                if key and key in proposal_data:
                    return proposal_data[key]

            # Fallback legado: dict com valores na ordem das colunas do arquivo
            values = list(proposal_data.values())
            if field.index < len(values):
                return values[field.index]

        if isinstance(proposal_data, (list, tuple)) and field.index < len(proposal_data):
            return proposal_data[field.index]

        return None

    def _require_field_value(self, proposal_data: dict, field: LayoutField, field_name: str):
        value = self._get_field_value(proposal_data, field)
        if value is None:
            raise Exception(
                f'Campo obrigatório "{field_name}" ausente no arquivo '
                f'(header esperado: "{field.header_name}")'
            )
        if isinstance(value, str) and value.strip().lower() in ('', 'nan', 'none'):
            raise Exception(
                f'Campo obrigatório "{field_name}" vazio '
                f'(header: "{field.header_name}")'
            )
        if pd.isna(value):
            raise Exception(
                f'Campo obrigatório "{field_name}" inválido '
                f'(header: "{field.header_name}")'
            )
        return value
        
    def construct_proposal(self, proposal_data:dict):
        try:
            self.proposal.original_data = proposal_data
            
            required_fields = ['disbursement_date', 'amount', 'client_document', 'contract_number', 'client_name', 'agreement', 'table']
            
            for field_name in required_fields:
                field_mapping = self.layout.map_fields.filter(name=field_name).first()
                if not field_mapping:
                    raise Exception(f'Campo obrigatório "{field_name}" não encontrado no mapeamento do layout')
                self._require_field_value(proposal_data, field_mapping, field_name)
            
            disbursement_field = self.layout.map_fields.filter(name='disbursement_date').first()
            disbursement_value = self._get_field_value(proposal_data, disbursement_field)
            self.proposal.disbursement_date = convert_value(disbursement_value, 'date')
            amount_field = self.layout.map_fields.filter(name='amount').first()
            amount_value = self._get_field_value(proposal_data, amount_field)
            self.proposal.amount = convert_value(amount_value, amount_field.data_type)
            
            client_doc_field = self.layout.map_fields.filter(name='client_document').first()
            client_doc_value = self._get_field_value(proposal_data, client_doc_field)
            self.proposal.client_document = convert_value(client_doc_value, client_doc_field.data_type)
            
            contract_field = self.layout.map_fields.filter(name='contract_number').first()
            contract_value = self._get_field_value(proposal_data, contract_field)
            self.proposal.contract_number = convert_value(contract_value, contract_field.data_type)
            
            client_name_field = self.layout.map_fields.filter(name='client_name').first()
            client_name_value = self._get_field_value(proposal_data, client_name_field)
            self.proposal.client_name = convert_value(client_name_value, client_name_field.data_type)

            # Validar que o layout tem um banco associado e atribuir ANTES de usar
            if not self.layout.bank:
                raise Exception('Layout não possui um banco associado. Configure o banco para este layout.')
            self.proposal.bank = self.layout.bank

            # Agora posso obter o status (que precisa do banco)
            status_field = self.layout.map_fields.filter(name='status').first()
            status_value = self._get_field_value(proposal_data, status_field)
            self.proposal.status = self.get_status(status_value)
            
            agreement_field = self.layout.map_fields.filter(name='agreement').first()
            agreement_value = self._get_field_value(proposal_data, agreement_field)
            self.proposal.agreement = self.get_agreement(agreement_value)
            
            table_field = self.layout.map_fields.filter(name='table').first()
            table_value = self._get_field_value(proposal_data, table_field)
            self.proposal.table = self.get_table(self.proposal.amount, table_value)
            
            # Resolução de digitador / acesso bancário
            digitador_field = self.layout.map_fields.filter(name='digitador').first()
            digitador_value = self._get_field_value(proposal_data, digitador_field)
            bank_access_field = self.layout.map_fields.filter(name='bank_access').first()
            bank_access_value = self._get_field_value(proposal_data, bank_access_field)

            # Pelo menos um dos dois campos deve estar mapeado
            if not digitador_field and not bank_access_field:
                raise Exception(
                    'Layout deve possuir pelo menos um dos campos mapeados: "Digitador" ou "Acessos".'
                )

            # Se o campo não estiver mapeado, seu valor pode ser None
            if digitador_field:
                self.proposal.digitador = convert_value(digitador_value, digitador_field.data_type) if digitador_value is not None else None
            if bank_access_field and bank_access_value is not None:
                bank = self.proposal.bank or self.layout.bank
                from bank_access.services import resolve_bank_access
                bank_access = resolve_bank_access(bank, bank_access_value)
                if not bank_access:
                    raise Exception(
                        f'❌ Acesso bancário não mapeado: "{bank_access_value}" - '
                        f'Cadastre o acesso ou mapeie na resolução de valores'
                    )
                self.proposal.bank_access = bank_access
                # Se houver usuário vinculado ao acesso, preenche o vendedor
                if bank_access.user:
                    self.proposal.seller = bank_access.user
                    self.proposal.company = bank_access.user.company
                else:
                    # Quando só existe acesso sem usuário, exige o nome do digitador
                    if not self.proposal.digitador:
                        raise Exception(
                            f'❌ Acesso bancário "{bank_access_value}" não possui usuário vinculado. '
                            f'Mapeie também o campo "Digitador" para prosseguir.'
                        )

            # Fallback de empresa quando não resolvemos via acesso bancário
            if not self.proposal.company and self.proposal.seller:
                self.proposal.company = self.proposal.seller.company

            self.proposal.status = 'pending'
            self.proposal.uploaded_at = datetime.now()
            
            return self.proposal
        except Exception as e:
            raise Exception(f'Erro ao construir proposta: {e}')
        
    def get_table(self, amount:float, name_in_bank:str):
        try:
            tables = self._get_matcher().match_tables(name_in_bank)

            if not tables:
                bank_name = getattr(getattr(self.layout, 'bank', None), 'name', None) or 'este banco'
                raise Exception(
                    f'Tabela não encontrada: {name_in_bank} '
                    f'(não há tabela cadastrada/vinculada com esse nome em {bank_name})'
                )

            valid_tables = [t for t in tables if t.covers_amount(amount)]

            if not valid_tables:
                raise Exception(f'Nenhuma tabela válida encontrada para o valor {amount}: {name_in_bank}')

            # Vigência = data de INÍCIO (a tabela vale a partir desta data).
            # Escolhe a mais recente que já começou na data de desembolso.
            disbursement = self.proposal.disbursement_date
            started = [
                t for t in valid_tables
                if t.is_active and t.vigency_date and disbursement and t.vigency_date <= disbursement
            ]
            pool = started or valid_tables
            max_vigency_date = max(t.vigency_date for t in pool)
            return next(t for t in pool if t.vigency_date == max_vigency_date)

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
        """Mantido para compatibilidade; prefira resolve_bank_access com banco."""
        if not login or login == 'nan':
            raise Exception(
                f'❌ Vendedor não mapeado: "{login}" - '
                f'Realize o mapeamento na resolução de valores'
            )

        bank = getattr(self.proposal, 'bank', None) or self.layout.bank
        from bank_access.services import resolve_bank_access
        access = resolve_bank_access(bank, login)
        if access and access.user:
            return access.user

        raise Exception(
            f'❌ Vendedor não mapeado: "{login}" - '
            f'Realize o mapeamento na resolução de valores'
        )

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
                self.last_error = str(e)
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
        

