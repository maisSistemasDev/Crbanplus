import { useState, useEffect, useCallback } from 'react';
import { useStore } from '@nanostores/react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { DataTable } from '../../ui/DataTable';
import { Badge } from '../../ui/Badge';
import { Button } from '../../ui/Button';
import { formatCurrency, formatDate } from '../../../../lib/utils/format';
import { ReleaseModal } from './ReleaseModal';
import { isPromotoraAdmin } from '../../../../lib/utils/roles';
import { $currentUser } from '../../../../lib/stores/auth';
import type { Commission, PaginatedResponse } from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { Search, CheckSquare, Square, Unlock, Filter } from 'lucide-react';

const ROLE_MAP: Record<string, string> = {
  vendedor: 'Vendedor',
  lider: 'Lider',
  empresa: 'Empresa',
};

const STATUS_MAP: Record<string, { label: string; variant: 'default' | 'success' | 'warning' | 'danger' | 'secondary' }> = {
  not_released: { label: 'Não liberado', variant: 'secondary' },
  withdraw_available: { label: 'Saque liberado', variant: 'success' },
  pending_manual_payment: { label: 'Aguardando pagamento', variant: 'warning' },
  paid: { label: 'Pago', variant: 'default' },
};

interface FilterOptions {
  banks: Array<{ id: string; name: string }>;
  companies: Array<{ id: string; name: string }>;
  sellers: Array<{ id: number; first_name: string; last_name: string }>;
  agreements: Array<{ id: string; name: string }>;
  tables: Array<{ id: string; name_in_bank: string }>;
}

export function CommissionList() {
  const currentUser = useStore($currentUser);
  const canManageCommissions = isPromotoraAdmin(currentUser?.role ?? null, currentUser?.company ?? null);
  
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [releaseModalOpen, setReleaseModalOpen] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  
  // Novos filtros
  const [bankFilter, setBankFilter] = useState('');
  const [companyFilter, setCompanyFilter] = useState('');
  const [sellerFilter, setSellerFilter] = useState('');
  const [agreementFilter, setAgreementFilter] = useState('');
  const [tableFilter, setTableFilter] = useState('');
  const [clientCpfFilter, setClientCpfFilter] = useState('');
  const [contractFilter, setContractFilter] = useState('');
  
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    banks: [],
    companies: [],
    sellers: [],
    agreements: [],
    tables: [],
  });

  const handleSelectRow = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    if (selectedIds.length === data.length && data.length > 0) {
      setSelectedIds([]);
    } else {
      // Selecionar apenas comissões não liberadas ou aguardando pagamento
      const selectableIds = data
        .filter((item) => {
          const status = item.release_status as string;
          return !status || status === 'not_released' || status === 'pending_manual_payment';
        })
        .map((item) => Number(item.id));
      setSelectedIds(selectableIds);
    }
  };

  const fetchFilterOptions = useCallback(async () => {
    try {
      const [banks, companies, sellers, agreements, tables] = await Promise.all([
        api.get(ENDPOINTS.BANKS),
        api.get(ENDPOINTS.COMPANIES),
        api.get(ENDPOINTS.SELLERS),
        api.get('/agreements/'),
        api.get('/tables/'),
      ]);
      
      setFilterOptions({
        banks: banks.results || banks,
        companies: companies.results || companies,
        sellers: sellers.results || sellers,
        agreements: agreements.results || agreements,
        tables: tables.results || tables,
      });
    } catch (error) {
      console.error('Error fetching filter options:', error);
    }
  }, []);

  const columns: Column<Record<string, unknown>>[] = [
    ...(canManageCommissions ? [{
      key: 'select',
      header: '',
      render: (item: Record<string, unknown>) => {
        const id = Number(item.id);
        const isSelected = selectedIds.includes(id);
        const releaseStatus = item.release_status as string;
        const canSelect = !releaseStatus || releaseStatus === 'not_released' || releaseStatus === 'pending_manual_payment';

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
      render: (item) => (
        <span className="font-mono text-xs text-gray-500">
          {String(item.proposal || '').slice(0, 8)}...
        </span>
      ),
    },
    {
      key: 'user_details',
      header: 'Usuario',
      render: (item) => {
        const d = item.user_details as Record<string, unknown> | null;
        return d ? `${d.first_name || ''} ${d.last_name || ''}`.trim() || '-' : '-';
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
      key: 'value',
      header: 'Valor',
      render: (item) => (
        <span className="font-medium text-green-600">{formatCurrency(Number(item.value))}</span>
      ),
    },
    {
      key: 'release_status',
      header: 'Status',
      render: (item) => {
        const status = (item.release_status as string) || 'not_released';
        const statusInfo = STATUS_MAP[status] || { label: status, variant: 'secondary' as const };
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

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(currentPage) });
      if (search) params.set('search', search);
      if (roleFilter) params.set('role', roleFilter);
      if (bankFilter) params.set('bank', bankFilter);
      if (companyFilter) params.set('company', companyFilter);
      if (sellerFilter) params.set('user', sellerFilter);
      if (agreementFilter) params.set('agreement', agreementFilter);
      if (tableFilter) params.set('table', tableFilter);
      if (clientCpfFilter) params.set('client_document', clientCpfFilter);
      if (contractFilter) params.set('proposal_id', contractFilter);
      
      const res = await api.get<PaginatedResponse<Commission> | Commission[]>(
        `${ENDPOINTS.COMMISSIONS}?${params}`
      );
      
      if (Array.isArray(res)) {
        setData(res as unknown as Record<string, unknown>[]);
        setTotalItems(res.length);
      } else {
        setData(res.results as unknown as Record<string, unknown>[]);
        setTotalItems(res.count);
      }
    } catch (error) {
      console.error('Error fetching commissions:', error);
      setData([]);
      setTotalItems(0);
    } finally {
      setLoading(false);
    }
  }, [currentPage, search, roleFilter, bankFilter, companyFilter, sellerFilter, agreementFilter, tableFilter, clientCpfFilter, contractFilter]);

  useEffect(() => {
    fetchFilterOptions();
  }, [fetchFilterOptions]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleReleaseSuccess = () => {
    setSelectedIds([]);
    fetchData();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Comissões</h1>
        {canManageCommissions && (
          <Button
            onClick={() => setReleaseModalOpen(true)}
            disabled={selectedIds.length === 0}
            variant="primary"
            icon={<Unlock size={16} />}
          >
            Liberar Comissões ({selectedIds.length})
          </Button>
        )}
      </div>

      <div className="space-y-4 mb-4">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
            />
          </div>
          <Button
            onClick={() => setShowFilters(!showFilters)}
            variant="secondary"
            icon={<Filter size={16} />}
          >
            {showFilters ? 'Ocultar' : 'Filtros'}
          </Button>
          {canManageCommissions && data.length > 0 && (
            <button
              onClick={handleSelectAll}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 flex items-center gap-2"
            >
              {selectedIds.length === data.filter(item => {
                const status = item.release_status as string;
                return !status || status === 'not_released' || status === 'pending_manual_payment';
              }).length && selectedIds.length > 0 ? (
                <>
                  <CheckSquare size={16} className="text-[var(--color-primary)]" />
                  Desmarcar Todos
                </>
              ) : (
                <>
                  <Square size={16} />
                  Selecionar Todos
                </>
              )}
            </button>
          )}
        </div>

        {showFilters && (
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3 bg-gray-50 p-4 rounded-lg border border-gray-200">
            <select
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
            >
              <option value="">Todos os tipos</option>
              <option value="vendedor">Vendedor</option>
              <option value="lider">Lider</option>
              <option value="empresa">Empresa</option>
            </select>

            <select
              value={bankFilter}
              onChange={(e) => {
                setBankFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
            >
              <option value="">Todos os Bancos</option>
              {filterOptions.banks.map((bank) => (
                <option key={bank.id} value={bank.id}>
                  {bank.name}
                </option>
              ))}
            </select>

            <select
              value={companyFilter}
              onChange={(e) => {
                setCompanyFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
            >
              <option value="">Todos os Corbans</option>
              {filterOptions.companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>

            <select
              value={sellerFilter}
              onChange={(e) => {
                setSellerFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
            >
              <option value="">Todos os Vendedores</option>
              {filterOptions.sellers.map((seller) => (
                <option key={seller.id} value={seller.id}>
                  {seller.first_name} {seller.last_name}
                </option>
              ))}
            </select>

            <select
              value={agreementFilter}
              onChange={(e) => {
                setAgreementFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
            >
              <option value="">Todos os Convênios</option>
              {filterOptions.agreements.map((agreement) => (
                <option key={agreement.id} value={agreement.id}>
                  {agreement.name}
                </option>
              ))}
            </select>

            <select
              value={tableFilter}
              onChange={(e) => {
                setTableFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
            >
              <option value="">Todas as Tabelas</option>
              {filterOptions.tables.map((table) => (
                <option key={table.id} value={table.id}>
                  {table.name_in_bank}
                </option>
              ))}
            </select>

            <input
              type="text"
              placeholder="CPF do Cliente"
              value={clientCpfFilter}
              onChange={(e) => {
                setClientCpfFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
            />

            <input
              type="text"
              placeholder="Número do Contrato"
              value={contractFilter}
              onChange={(e) => {
                setContractFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
            />
          </div>
        )}
      </div>

      <DataTable
        columns={columns}
        data={data}
        loading={loading}
        totalItems={totalItems}
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        keyExtractor={(item) => String(item.id)}
        emptyMessage="Nenhuma comissão encontrada"
      />

      <ReleaseModal
        isOpen={releaseModalOpen}
        onClose={() => setReleaseModalOpen(false)}
        selectedIds={selectedIds}
        selectedCommissions={data.filter(item => selectedIds.includes(Number(item.id))).map(item => ({
          id: Number(item.id),
          release_status: item.release_status as string
        }))}
        onSuccess={handleReleaseSuccess}
      />
    </div>
  );
}
