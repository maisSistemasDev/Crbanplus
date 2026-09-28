"""
Índices em memória para o preview de lote (evita N+1 e Table.objects.all() por valor).
"""
from bank.models import Table, Agreement, normalize_name_compact
from bank_access.models import BankAccess
from proposals.models import StatusPayment


def normalize_value(value):
    return str(value).lower().strip()


class BatchPreviewMatcher:
    """Resolve valores do arquivo contra entidades do sistema com uma carga única."""

    def __init__(self, bank):
        self.bank = bank
        self._tables = list(
            Table.objects.filter(bank=bank).select_related('agreement').prefetch_related('commission_ranges')
        )
        self._agreements = list(Agreement.objects.all())
        self._bank_accesses = list(
            BankAccess.objects.filter(bank=bank, is_active=True).select_related('user')
        )
        self._statuses = list(StatusPayment.objects.filter(bank=bank))

        self._table_by_alias = {}
        self._table_by_compact = {}
        for table in self._tables:
            compact = normalize_name_compact(table.name_in_bank or '')
            if compact:
                self._table_by_compact.setdefault(compact, []).append(table)
            for alias in table.alias or []:
                self._table_by_alias.setdefault(normalize_value(alias), table)
                alias_compact = normalize_name_compact(str(alias))
                if alias_compact:
                    self._table_by_compact.setdefault(alias_compact, []).append(table)

        self._agreement_by_alias = {}
        for agreement in self._agreements:
            for alias in agreement.alias or []:
                self._agreement_by_alias.setdefault(normalize_value(alias), agreement)

        self._access_by_alias = {}
        for access in self._bank_accesses:
            for alias in access.alias or []:
                self._access_by_alias.setdefault(normalize_value(alias), access)

        self._status_by_name = {}
        self._status_by_alias = {}
        for sp in self._statuses:
            if sp.name:
                self._status_by_name[normalize_value(sp.name)] = sp
            for alias in sp.alias or []:
                self._status_by_alias[normalize_value(alias)] = sp

    def match_tables(self, value):
        """Todas as tabelas do banco que batem com o nome do arquivo."""
        for candidate in self._name_candidates(value):
            hits = self._match_tables_one(candidate)
            if hits:
                return hits
        return []

    def _name_candidates(self, value):
        raw = str(value or '').strip()
        if not raw:
            return []
        candidates = [raw]
        if ' - ' in raw:
            left = raw.split(' - ', 1)[0].strip()
            if left and left not in candidates:
                candidates.append(left)
        return candidates

    def _match_tables_one(self, value):
        v = normalize_value(value)
        compact = normalize_name_compact(value)
        hits = []
        seen = set()

        def add(table):
            if table.id not in seen:
                seen.add(table.id)
                hits.append(table)

        if compact:
            for table in self._table_by_compact.get(compact, []):
                add(table)
        hit = self._table_by_alias.get(v)
        if hit:
            add(hit)
        if hits:
            return hits

        for table in self._tables:
            name = table.name_in_bank
            if name and v and len(v) >= 5 and (v in normalize_value(name) or normalize_value(name) in v):
                add(table)
                continue
            name_compact = normalize_name_compact(name or '')
            if compact and name_compact and len(compact) >= 5 and (
                compact in name_compact or name_compact in compact
            ):
                add(table)
        return hits

    def match_table(self, value):
        tables = self.match_tables(value)
        return tables[0] if tables else None

    def match_agreement(self, value):
        v = normalize_value(value)
        hit = self._agreement_by_alias.get(v)
        if hit:
            return hit
        for agreement in self._agreements:
            name = agreement.name
            if name and v in normalize_value(name):
                return agreement
        for agreement in self._agreements:
            if v in (agreement.alias or []):
                return agreement
        return None

    def match_user(self, value):
        access = self.match_access(value)
        return access.user if access else None

    def match_access(self, value):
        from bank_access.services import login_values_match

        login_type = getattr(self.bank, 'access_login_type', None)
        for access in self._bank_accesses:
            if login_values_match(value, access.username, login_type):
                return access
            for alias in access.alias or []:
                if login_values_match(value, alias, login_type):
                    return access
        return None

    def match_status(self, value):
        v = normalize_value(value)
        hit = self._status_by_name.get(v) or self._status_by_alias.get(v)
        if hit:
            return hit
        for sp in self._statuses:
            if not sp.alias:
                continue
            if v in [normalize_value(a) for a in sp.alias]:
                return sp
        return None
