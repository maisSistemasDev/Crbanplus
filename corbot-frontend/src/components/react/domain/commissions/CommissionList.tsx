import { useState, useEffect, useCallback, useMemo } from 'react';
import { useStore } from '@nanostores/react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { DataTable } from '../../ui/DataTable';
import { Badge } from '../../ui/Badge';
import { Button } from '../../ui/Button';
import { PageHeader } from '../../ui/PageHeader';
import { MultiValueFilter } from '../../ui/MultiValueFilter';
import { SearchSelect } from '../../ui/SearchSelect';
import { formatCurrency, formatDate } from '../../../../lib/utils/format';
import { ReleaseModal } from './ReleaseModal';
import { CommissionDetailModal } from './CommissionDetailModal';
import { DebitDetailModal } from './DebitDetailModal';
import { isPromotoraAdmin } from '../../../../lib/utils/roles';
import { $currentUser } from '../../../../lib/stores/auth';
import type {
  Commission,
  CommissionRow,
  CommissionTotals,
  ConsolidatedCommissionGroup,
  ConsolidatedCommissionResponse,
  PaginatedResponse,
} from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { Search, CheckSquare, Square, Unlock, Filter, Undo2, Layers } from 'lucide-react';

const ROLE_FILTER_OPTIONS = [
  { value: 'vendedor', label: 'Vendedor' },
  { value: 'lider', label: 'Lider' },
  { value: 'empresa', label: 'Empresa' },
];

const DEBIT_FILTER_OPTIONS = [
  { value: 'with_debit', label: 'Com débito' },
  { value: 'without_debit', label: 'Sem débito' },
  { value: 'zeroed', label: 'Zerados' },
];

const STATUS_FILTER_OPTIONS = [
  { value: 'not_released', label: 'Não liberado' },
  { value: 'pending_manual_payment', label: 'Aguardando pagamento' },
  { value: 'withdraw_available', label: 'Saque liberado' },
  { value: 'paid', label: 'Pago' },
  { value: 'sinistro', label: 'Sinistro' },
];

const DATE_PRESET_OPTIONS = [
  { value: 'today', label: 'Hoje' },
  { value: 'last7', label: 'Ultimos 7 dias' },
  { value: 'last30', label: 'Ultimos 30 dias' },
  { value: 'thisMonth', label: 'Este mes' },
  { value: 'custom', label: 'Selecionar periodo' },
];

function formatDateInput(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function resolveDateRange(preset: DateRangePreset, customBegin: string, customEnd: string) {
  const today = new Date();

  if (preset === 'custom') {
    return { begin: customBegin, end: customEnd };
  }

  if (preset === 'today') {
    const value = formatDateInput(today);
    return { begin: value, end: value };
  }

  if (preset === 'last7') {
    const begin = new Date(today);
    begin.setDate(today.getDate() - 6);
    return { begin: formatDateInput(begin), end: formatDateInput(today) };
  }

  if (preset === 'last30') {
    const begin = new Date(today);
    begin.setDate(today.getDate() - 29);
    return { begin: formatDateInput(begin), end: formatDateInput(today) };
  }

  if (preset === 'thisMonth') {
    const begin = new Date(today.getFullYear(), today.getMonth(), 1);
    return { begin: formatDateInput(begin), end: formatDateInput(today) };
  }

  return { begin: '', end: '' };
}

const ROLE_MAP: Record<string, string> = {
  vendedor: 'Vendedor',
  lider: 'Lider',
  empresa: 'Empresa',
};

const STATUS_MAP: Record<string, { label: string; variant: 'default' | 'success' | 'warning' | 'error' | 'info' }> = {
  not_released: { label: 'Não liberado', variant: 'default' },
  withdraw_available: { label: 'Saque liberado', variant: 'success' },
  pending_manual_payment: { label: 'Aguardando pagamento', variant: 'warning' },
  paid: { label: 'Pago', variant: 'info' },
  sinistro: { label: 'Sinistro', variant: 'error' },
};

function isSelectableStatus(status?: string) {
  return !status || status === 'not_released' || status === 'pending_manual_payment' || status === 'paid';
}

interface FilterOptions {
  banks: Array<{ id: string; name: string }>;
  companies: Array<{ id: string; name: string }>;
  sellers: Array<{ id: number; first_name: string; last_name: string }>;
  agreements: Array<{ id: string; name: string }>;
  tables: Array<{ id: string; name_in_bank: string }>;
}

interface DetailModalState {
  title: string;
  subtitle?: string;
  items: CommissionRow[];
}

interface DebitModalState {
  title: string;
  commissionIds: number[];
}

export function CommissionList() {
  const currentUser = useStore($currentUser);
  const canManageCommissions = isPromotoraAdmin(currentUser?.role ?? null, currentUser?.company ?? null);

  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [consolidatedRows, setConsolidatedRows] = useState<ConsolidatedCommissionGroup[]>([]);
  const [totals, setTotals] = useState<CommissionTotals | null>(null);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [releaseModalOpen, setReleaseModalOpen] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [consolidated, setConsolidated] = useState(false);
  const [debitFilter, setDebitFilter] = useState('');
  const [detailModal, setDetailModal] = useState<DetailModalState | null>(null);
  const [debitModal, setDebitModal] = useState<DebitModalState | null>(null);

  // Novos filtros
  const [bankFilter, setBankFilter] = useState('');
  const [companyFilter, setCompanyFilter] = useState('');
  const [sellerFilter, setSellerFilter] = useState('');
  const [agreementFilter, setAgreementFilter] = useState('');
  const [tableFilter, setTableFilter] = useState('');
  const [clientCpfFilter, setClientCpfFilter] = useState('');
  const [contractFilter, setContractFilter] = useState('');
  const [matriculaFilter, setMatriculaFilter] = useState('');
  const [commissionStatusFilter, setCommissionStatusFilter] = useState('');
  const [dateRangePreset, setDateRangePreset] = useState<DateRangePreset>('');
  const [customBeginDateFilter, setCustomBeginDateFilter] = useState('');
  const [customEndDateFilter, setCustomEndDateFilter] = useState('');

  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    banks: [],
    companies: [],
    sellers: [],
    agreements: [],
    tables: [],
  });

  const bankOptions = useMemo(
    () => filterOptions.banks.map((bank) => ({ value: bank.id, label: bank.name })),
    [filterOptions.banks],
  );
  const companyOptions = useMemo(
    () => filterOptions.companies.map((company) => ({ value: company.id, label: company.name })),
    [filterOptions.companies],
  );
  const sellerOptions = useMemo(
    () =>
      filterOptions.sellers.map((seller) => ({
        value: String(seller.id),
        label: `${seller.first_name} ${seller.last_name}`.trim(),
      })),
    [filterOptions.sellers],
  );
  const agreementOptions = useMemo(
    () => filterOptions.agreements.map((agreement) => ({ value: agreement.id, label: agreement.name })),
    [filterOptions.agreements],
  );
  const tableOptions = useMemo(
    () => filterOptions.tables.map((table) => ({ value: table.id, label: table.name_in_bank })),
    [filterOptions.tables],
  );

  // Comissões da listagem atual (já filtrada pelo backend) que podem ser liberadas.
  const selectableIds = useMemo(() => {
    if (consolidated) {
      return consolidatedRows.flatMap((group) =>
        group.items.filter((item) => isSelectableStatus(item.release_status)).map((item) => item.id),
      );
    }
    return data
      .filter((item) => isSelectableStatus(item.release_status as string))
      .map((item) => Number(item.id));
  }, [consolidated, consolidatedRows, data]);

  const allFilteredSelected = selectableIds.length > 0 && selectedIds.length === selectableIds.length;

  const handleSelectRow = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  // No consolidado a seleção é por recebedor: marca ou desmarca o grupo inteiro.
  const handleSelectGroup = (group: ConsolidatedCommissionGroup) => {
    const ids = group.items.filter((item) => isSelectableStatus(item.release_status)).map((item) => item.id);
    const allSelected = ids.length > 0 && ids.every((id) => selectedIds.includes(id));
    setSelectedIds((prev) =>
      allSelected ? prev.filter((id) => !ids.includes(id)) : [...new Set([...prev, ...ids])]
    );
  };

  const handleSelectAll = () => {
    setSelectedIds(allFilteredSelected ? [] : selectableIds);
  };

  const fetchFilterOptions = useCallback(async () => {
    try {
      const [banks, companies, sellers, tables] = await Promise.all([
        api.get(ENDPOINTS.BANKS),
        api.get(`${ENDPOINTS.COMPANIES}?page_size=500`),
        api.get(ENDPOINTS.SELLERS),
        api.get('/tables/'),
      ]);

      setFilterOptions((prev) => ({
        ...prev,
        banks: banks.results || banks,
        companies: companies.results || companies,
        sellers: sellers.results || sellers,
        tables: tables.results || tables,
      }));
    } catch (error) {
      console.error('Error fetching filter options:', error);
    }
  }, []);

  useEffect(() => {
    const url = bankFilter
      ? `${ENDPOINTS.AGREEMENTS}?bank=${encodeURIComponent(bankFilter)}`
      : ENDPOINTS.AGREEMENTS;
    api
      .get<{ id: string; name: string }[] | { results: { id: string; name: string }[] }>(url)
      .then((res) => {
        const list = Array.isArray(res) ? res : res.results || [];
        setFilterOptions((prev) => ({ ...prev, agreements: list }));
        setAgreementFilter((current) =>
          current && list.some((item) => item.id === current) ? current : '',
        );
      })
      .catch(() => setFilterOptions((prev) => ({ ...prev, agreements: [] })));
  }, [bankFilter]);

  const detailedColumns: Column<Record<string, unknown>>[] = [
    ...(canManageCommissions ? [{
      key: 'select',
      header: '',
      render: (item: Record<string, unknown>) => {
        const id = Number(item.id);
        const isSelected = selectedIds.includes(id);
        const releaseStatus = item.release_status as string;
        const canSelect = isSelectableStatus(releaseStatus);

        return (
          <button
            onClick={() => canSelect && handleSelectRow(id)}
            disabled={!canSelect}
            className="flex items-center justify-center w-full disabled:cursor-not-allowed disabled:opacity-30"
          >
            {isSelected ? (
              <CheckSquare size={18} className="text-[var(--color-primary)]" />
            ) : (
              <Square size={18} className="text-gray-400" />
            )}
          </button>
        );
      },
    }] : []),
    {
      key: 'proposal',
      header: 'Proposta',
      render: (item) => {
        const row = item.row as CommissionRow | undefined;
        return (
          <div>
            <span className="font-mono text-xs text-gray-600">
              {row?.contract_number || String(item.proposal || '').slice(0, 8)}
            </span>
            {row?.client_name && <div className="text-xs text-gray-400">{row.client_name}</div>}
          </div>
        );
      },
    },
    {
      key: 'user_details',
      header: 'Recebedor',
      render: (item) => {
        const recipient = item.recipient as { name?: string; type?: string } | null;
        const user = item.user_details as Record<string, unknown> | null;
        const userName = user ? `${user.first_name || ''} ${user.last_name || ''}`.trim() : '';
        // Quem recebe é o corban nas comissões de empresa; o usuário é secundário.
        const isCompany = recipient?.type === 'company';
        const name = recipient?.name || userName || (item.company_name as string) || '-';
        return (
          <div>
            <span>{name}</span>
            {isCompany && (
              <span className="block text-xs text-gray-400">
                {userName ? `Corban · ${userName}` : 'Corban'}
              </span>
            )}
          </div>
        );
      },
    },
    {
      key: 'role',
      header: 'Tipo',
      render: (item) => (
        <Badge variant="default">{ROLE_MAP[item.role as string] || (item.role as string)}</Badge>
      ),
    },
    {
      key: 'percentage',
      header: 'Taxa',
      render: (item) => `${item.percentage}%`,
    },
    {
      key: 'total_value',
      header: 'Comissão',
      render: (item) => {
        const row = item.row as CommissionRow | undefined;
        const value = Number(item.total_value ?? item.value ?? 0);
        return (
          <button
            onClick={() =>
              setDetailModal({
                title: 'Detalhe da comissão',
                subtitle: row?.contract_number ? `Proposta ${row.contract_number}` : undefined,
                items: row ? [row] : [],
              })
            }
            className="font-medium text-green-600 underline decoration-dotted hover:text-green-700"
          >
            {formatCurrency(value)}
          </button>
        );
      },
    },
    {
      key: 'debit_value',
      header: 'Débito',
      render: (item) => {
        const debit = Number(item.debit_value ?? 0);
        if (debit <= 0) return <span className="text-gray-400">-</span>;
        return (
          <button
            onClick={() =>
              setDebitModal({ title: 'Débitos da comissão', commissionIds: [Number(item.id)] })
            }
            className="font-medium text-red-600 underline decoration-dotted hover:text-red-700"
          >
            - {formatCurrency(debit)}
          </button>
        );
      },
    },
    {
      key: 'net_value',
      header: 'Total',
      render: (item) => {
        if (item.is_zeroed) return <Badge variant="warning">Zerado</Badge>;
        return (
          <span className="font-semibold text-gray-900">
            {formatCurrency(Number(item.net_value ?? item.value ?? 0))}
          </span>
        );
      },
    },
    {
      key: 'release_status',
      header: 'Status',
      render: (item) => {
        const status = (item.release_status as string) || 'not_released';
        const statusInfo = STATUS_MAP[status] || { label: status, variant: 'default' as const };
        return <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>;
      },
    },
    {
      key: 'created_at',
      header: 'Data',
      sortable: true,
      render: (item) => formatDate(item.created_at as string),
    },
  ];

  const consolidatedColumns: Column<Record<string, unknown>>[] = [
    ...(canManageCommissions ? [{
      key: 'select',
      header: '',
      render: (item: Record<string, unknown>) => {
        const group = item as unknown as ConsolidatedCommissionGroup;
        const ids = group.items
          .filter((row) => isSelectableStatus(row.release_status))
          .map((row) => row.id);
        const allSelected = ids.length > 0 && ids.every((id) => selectedIds.includes(id));

        return (
          <button
            onClick={() => ids.length > 0 && handleSelectGroup(group)}
            disabled={ids.length === 0}
            className="flex items-center justify-center w-full disabled:cursor-not-allowed disabled:opacity-30"
          >
            {allSelected ? (
              <CheckSquare size={18} className="text-[var(--color-primary)]" />
            ) : (
              <Square size={18} className="text-gray-400" />
            )}
          </button>
        );
      },
    }] : []),
    {
      key: 'recipient',
      header: 'Recebedor',
      render: (item) => {
        const group = item as unknown as ConsolidatedCommissionGroup;
        return (
          <div>
            <span className="font-medium text-gray-900">{group.recipient.name}</span>
            <div className="text-xs text-gray-400">
              {group.recipient.type === 'company' ? 'Corban' : 'Usuário'}
              {group.recipient.document ? ` · ${group.recipient.document}` : ''}
            </div>
          </div>
        );
      },
    },
    {
      key: 'release_status',
      header: 'Status',
      render: (item) => {
        const group = item as unknown as ConsolidatedCommissionGroup;
        const statusInfo = STATUS_MAP[group.release_status];
        return (
          <Badge variant={statusInfo?.variant || 'default'}>
            {statusInfo?.label || group.release_status_display}
          </Badge>
        );
      },
    },
    {
      key: 'roles',
      header: 'Tipos',
      render: (item) => {
        const group = item as unknown as ConsolidatedCommissionGroup;
        return <span className="text-xs text-gray-600">{group.roles.join(', ') || '-'}</span>;
      },
    },
    {
      key: 'commissions_count',
      header: 'Propostas',
      render: (item) => {
        const group = item as unknown as ConsolidatedCommissionGroup;
        return <span className="text-sm">{group.commissions_count}</span>;
      },
    },
    {
      key: 'total_value',
      header: 'Comissão',
      render: (item) => {
        const group = item as unknown as ConsolidatedCommissionGroup;
        return (
          <button
            onClick={() =>
              setDetailModal({
                title: `Comissões de ${group.recipient.name}`,
                subtitle: `${group.commissions_count} proposta(s) em "${
                  STATUS_MAP[group.release_status]?.label || group.release_status_display
                }"`,
                items: group.items,
              })
            }
            className="font-medium text-green-600 underline decoration-dotted hover:text-green-700"
          >
            {formatCurrency(Number(group.total_value || 0))}
          </button>
        );
      },
    },
    {
      key: 'debit_value',
      header: 'Débito',
      render: (item) => {
        const group = item as unknown as ConsolidatedCommissionGroup;
        const debit = Number(group.debit_value || 0);
        if (debit <= 0) return <span className="text-gray-400">-</span>;
        return (
          <button
            onClick={() =>
              setDebitModal({
                title: `Débitos de ${group.recipient.name}`,
                commissionIds: group.commission_ids,
              })
            }
            className="font-medium text-red-600 underline decoration-dotted hover:text-red-700"
          >
            - {formatCurrency(debit)}
          </button>
        );
      },
    },
    {
      key: 'net_value',
      header: 'Total',
      render: (item) => {
        const group = item as unknown as ConsolidatedCommissionGroup;
        if (group.is_zeroed) return <Badge variant="warning">Zerado</Badge>;
        return (
          <span className="font-semibold text-gray-900">{formatCurrency(Number(group.net_value || 0))}</span>
        );
      },
    },
  ];

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const dateRange = resolveDateRange(dateRangePreset, customBeginDateFilter, customEndDateFilter);
      const params = new URLSearchParams({ page: String(currentPage) });
      if (search) params.set('search', search);
      if (roleFilter) params.set('role', roleFilter);
      if (bankFilter) params.set('bank', bankFilter);
      if (companyFilter) params.set('company', companyFilter);
      if (sellerFilter) params.set('user', sellerFilter);
      if (agreementFilter) params.set('agreement', agreementFilter);
      if (tableFilter) params.set('table', tableFilter);
      if (clientCpfFilter) params.set('client_documents', clientCpfFilter);
      if (contractFilter) params.set('contract_numbers', contractFilter);
      if (matriculaFilter) params.set('matricula', matriculaFilter);
      if (commissionStatusFilter) params.set('release_status', commissionStatusFilter);
      if (debitFilter) params.set('debit_filter', debitFilter);
      if (dateRange.begin) params.set('begin_date', dateRange.begin);
      if (dateRange.end) params.set('end_date', dateRange.end);

      if (consolidated) {
        const res = await api.get<ConsolidatedCommissionResponse>(
          `${ENDPOINTS.COMMISSIONS_CONSOLIDATED}?${params}`
        );
        setConsolidatedRows(res.results || []);
        setTotals(res.totals || null);
        setTotalItems((res.results || []).length);
        setData([]);
        return;
      }

      const res = await api.get<PaginatedResponse<Commission> | Commission[]>(
        `${ENDPOINTS.COMMISSIONS}?${params}`
      );

      const items = Array.isArray(res) ? res : res.results;
      setConsolidatedRows([]);
      setData(items as unknown as Record<string, unknown>[]);
      setTotalItems(Array.isArray(res) ? res.length : res.count);
      setTotals(
        items.reduce(
          (acc, item) => ({
            total_value: String(Number(acc.total_value) + Number(item.total_value ?? item.value ?? 0)),
            debit_value: String(Number(acc.debit_value) + Number(item.debit_value ?? 0)),
            net_value: String(Number(acc.net_value) + Number(item.net_value ?? item.value ?? 0)),
            commissions_count: acc.commissions_count + 1,
            zeroed_count: acc.zeroed_count + (item.is_zeroed ? 1 : 0),
          }),
          { total_value: '0', debit_value: '0', net_value: '0', commissions_count: 0, zeroed_count: 0 } as CommissionTotals,
        ),
      );
    } catch (error) {
      console.error('Error fetching commissions:', error);
      setData([]);
      setConsolidatedRows([]);
      setTotals(null);
      setTotalItems(0);
    } finally {
      setLoading(false);
    }
  }, [
    currentPage,
    search,
    roleFilter,
    bankFilter,
    companyFilter,
    sellerFilter,
    agreementFilter,
    tableFilter,
    clientCpfFilter,
    contractFilter,
    matriculaFilter,
    commissionStatusFilter,
    debitFilter,
    consolidated,
    dateRangePreset,
    customBeginDateFilter,
    customEndDateFilter,
  ]);

  useEffect(() => {
    fetchFilterOptions();
  }, [fetchFilterOptions]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setCurrentPage(1);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // A seleção nunca pode conter comissões fora do filtro atual.
  useEffect(() => {
    setSelectedIds((prev) => {
      const next = prev.filter((id) => selectableIds.includes(id));
      return next.length === prev.length ? prev : next;
    });
  }, [selectableIds]);

  const handleReleaseSuccess = () => {
    setSelectedIds([]);
    fetchData();
  };

  const selectedCommissions = useMemo(() => {
    if (consolidated) {
      return consolidatedRows
        .flatMap((group) => group.items)
        .filter((item) => selectedIds.includes(item.id))
        .map((item) => ({ id: item.id, release_status: item.release_status }));
    }
    return data
      .filter((item) => selectedIds.includes(Number(item.id)))
      .map((item) => ({ id: Number(item.id), release_status: item.release_status as string }));
  }, [consolidated, consolidatedRows, data, selectedIds]);

  return (
    <div>
      <PageHeader
        title="Comissões"
        actions={
          canManageCommissions ? (
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => setReleaseModalOpen(true)}
                disabled={selectedIds.length === 0}
                variant="secondary"
                icon={<Undo2 size={16} />}
              >
                Cancelar pagamento
              </Button>
              <Button
                size="sm"
                onClick={() => setReleaseModalOpen(true)}
                disabled={selectedIds.length === 0}
                variant="primary"
                icon={<Unlock size={16} />}
              >
                Liberar ({selectedIds.length})
              </Button>
            </div>
          ) : undefined
        }
      />

      <div className="space-y-4 mb-4">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por cliente, CPF, contrato ou vendedor..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
            />
          </div>
          <button
            onClick={() => {
              setConsolidated((prev) => !prev);
              setCurrentPage(1);
            }}
            className={`flex items-center gap-2 whitespace-nowrap rounded-lg border px-3 py-2 text-sm ${
              consolidated
                ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/10 text-[var(--color-primary)]'
                : 'border-gray-200 hover:bg-gray-50'
            }`}
          >
            <Layers size={16} />
            Consolidado
          </button>
          <Button
            onClick={() => setShowFilters(!showFilters)}
            variant="secondary"
            icon={<Filter size={16} />}
          >
            {showFilters ? 'Ocultar' : 'Filtros'}
          </Button>
          {canManageCommissions && selectableIds.length > 0 && (
            <button
              onClick={handleSelectAll}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 flex items-center gap-2 whitespace-nowrap"
            >
              {allFilteredSelected ? (
                <>
                  <CheckSquare size={16} className="text-[var(--color-primary)]" />
                  Desmarcar Todos
                </>
              ) : (
                <>
                  <Square size={16} />
                  Selecionar Todos ({selectableIds.length})
                </>
              )}
            </button>
          )}
        </div>

        {totals && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div className="rounded-lg border border-gray-200 bg-white p-3">
              <p className="text-xs text-gray-500">Comissão</p>
              <p className="text-lg font-semibold text-green-600">
                {formatCurrency(Number(totals.total_value))}
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-3">
              <p className="text-xs text-gray-500">Débito</p>
              <p className="text-lg font-semibold text-red-600">
                {formatCurrency(Number(totals.debit_value))}
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-3">
              <p className="text-xs text-gray-500">Total a pagar</p>
              <p className="text-lg font-semibold text-gray-900">
                {formatCurrency(Number(totals.net_value))}
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-3">
              <p className="text-xs text-gray-500">Zerados</p>
              <p className="text-lg font-semibold text-gray-900">{totals.zeroed_count}</p>
            </div>
          </div>
        )}

        {showFilters && (
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3 bg-gray-50 p-4 rounded-lg border border-gray-200">
            <SearchSelect
              placeholder="Todos os tipos"
              allowEmpty
              value={roleFilter}
              options={ROLE_FILTER_OPTIONS}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setCurrentPage(1);
              }}
            />

            <SearchSelect
              placeholder="Com e sem débito"
              allowEmpty
              value={debitFilter}
              options={DEBIT_FILTER_OPTIONS}
              onChange={(e) => {
                setDebitFilter(e.target.value);
                setCurrentPage(1);
              }}
            />

            <SearchSelect
              placeholder="Todos os Bancos"
              allowEmpty
              value={bankFilter}
              options={bankOptions}
              onChange={(e) => {
                setBankFilter(e.target.value);
                setCurrentPage(1);
              }}
            />

            <SearchSelect
              placeholder="Todos os Corbans"
              allowEmpty
              value={companyFilter}
              options={companyOptions}
              onChange={(e) => {
                setCompanyFilter(e.target.value);
                setCurrentPage(1);
              }}
            />

            <SearchSelect
              placeholder="Todos os Vendedores"
              allowEmpty
              value={sellerFilter}
              options={sellerOptions}
              onChange={(e) => {
                setSellerFilter(e.target.value);
                setCurrentPage(1);
              }}
            />

            <SearchSelect
              placeholder="Todos os Convênios"
              allowEmpty
              value={agreementFilter}
              options={agreementOptions}
              onChange={(e) => {
                setAgreementFilter(e.target.value);
                setCurrentPage(1);
              }}
            />

            <SearchSelect
              placeholder="Todas as Tabelas"
              allowEmpty
              value={tableFilter}
              options={tableOptions}
              onChange={(e) => {
                setTableFilter(e.target.value);
                setCurrentPage(1);
              }}
            />

            <MultiValueFilter
              placeholder="Matrícula"
              addLabel="+ Matrícula"
              value={matriculaFilter}
              onChange={(value) => {
                setMatriculaFilter(value);
                setCurrentPage(1);
              }}
            />

            <MultiValueFilter
              placeholder="CPF do Cliente"
              addLabel="+ CPF"
              value={clientCpfFilter}
              onChange={(value) => {
                setClientCpfFilter(value);
                setCurrentPage(1);
              }}
            />

            <MultiValueFilter
              placeholder="Cód. da proposta"
              addLabel="+ Cód. da proposta"
              value={contractFilter}
              onChange={(value) => {
                setContractFilter(value);
                setCurrentPage(1);
              }}
            />

            <SearchSelect
              placeholder="Todos os status"
              allowEmpty
              value={commissionStatusFilter}
              options={STATUS_FILTER_OPTIONS}
              onChange={(e) => {
                setCommissionStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
            />

            <div className="lg:col-span-2 space-y-2 rounded-lg border border-gray-200 bg-white p-3">
              <p className="text-xs font-medium text-gray-500">Periodo</p>
              <SearchSelect
                placeholder="Qualquer data"
                allowEmpty
                value={dateRangePreset}
                options={DATE_PRESET_OPTIONS}
                onChange={(e) => {
                  setDateRangePreset(e.target.value as DateRangePreset);
                  setCurrentPage(1);
                }}
              />

              {dateRangePreset === 'custom' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <input
                    type="date"
                    value={customBeginDateFilter}
                    onChange={(e) => {
                      setCustomBeginDateFilter(e.target.value);
                      setCurrentPage(1);
                    }}
                    className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
                  />
                  <input
                    type="date"
                    value={customEndDateFilter}
                    onChange={(e) => {
                      setCustomEndDateFilter(e.target.value);
                      setCurrentPage(1);
                    }}
                    className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
                  />
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <DataTable
        columns={consolidated ? consolidatedColumns : detailedColumns}
        data={consolidated ? (consolidatedRows as unknown as Record<string, unknown>[]) : data}
        loading={loading}
        totalItems={totalItems}
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        keyExtractor={(item) => String(consolidated ? item.key : item.id)}
        emptyMessage="Nenhuma comissão encontrada"
      />

      <ReleaseModal
        isOpen={releaseModalOpen}
        onClose={() => setReleaseModalOpen(false)}
        selectedIds={selectedIds}
        selectedCommissions={selectedCommissions}
        defaultConsolidated={consolidated}
        onSuccess={handleReleaseSuccess}
      />

      <CommissionDetailModal
        isOpen={detailModal !== null}
        onClose={() => setDetailModal(null)}
        title={detailModal?.title || ''}
        subtitle={detailModal?.subtitle}
        items={detailModal?.items || []}
      />

      <DebitDetailModal
        isOpen={debitModal !== null}
        onClose={() => setDebitModal(null)}
        title={debitModal?.title}
        commissionIds={debitModal?.commissionIds || []}
      />
    </div>
  );
}
