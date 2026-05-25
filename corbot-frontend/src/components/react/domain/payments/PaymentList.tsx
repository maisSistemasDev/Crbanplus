import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { DataTable } from '../../ui/DataTable';
import { Badge } from '../../ui/Badge';
import { formatCurrency, formatDate, formatCPF } from '../../../../lib/utils/format';
import type { Payment, PaginatedResponse } from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { Search } from 'lucide-react';

const STATUS_MAP: Record<string, { label: string; variant: 'default' | 'success' | 'warning' | 'error' | 'info' }> = {
  pending: { label: 'Pendente', variant: 'warning' },
  approved: { label: 'Aprovado', variant: 'info' },
  paid: { label: 'Pago', variant: 'success' },
  rejected: { label: 'Rejeitado', variant: 'error' },
};

const columns: Column<Record<string, unknown>>[] = [
  {
    key: 'user_details',
    header: 'Usuario',
    render: (item) => {
      const d = item.user_details as Record<string, unknown> | null;
      return d ? (
        <div>
          <p className="font-medium text-gray-900">{d.first_name} {d.last_name}</p>
          <p className="text-xs text-gray-400">{formatCPF(d.cpf as string)}</p>
        </div>
      ) : '-';
    },
  },
  {
    key: 'total_amount',
    header: 'Valor',
    sortable: true,
    render: (item) => (
      <span className="font-medium text-green-600">{formatCurrency(Number(item.total_amount))}</span>
    ),
  },
  {
    key: 'status',
    header: 'Status',
    render: (item) => {
      const s = STATUS_MAP[item.status as string] || { label: item.status, variant: 'default' as const };
      return <Badge variant={s.variant}>{s.label}</Badge>;
    },
  },
  { key: 'payment_method', header: 'Metodo' },
  {
    key: 'created_at',
    header: 'Data',
    sortable: true,
    render: (item) => formatDate(item.created_at as string),
  },
];

export function PaymentList() {
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(currentPage) });
      if (search) params.set('search', search);
      if (statusFilter) params.set('status', statusFilter);
      const res = await api.get<PaginatedResponse<Payment> | Payment[]>(`${ENDPOINTS.PAYMENTS}?${params}`);
      if (Array.isArray(res)) {
        setData(res as unknown as Record<string, unknown>[]);
        setTotalItems(res.length);
      } else {
        setData(res.results as unknown as Record<string, unknown>[]);
        setTotalItems(res.count);
      }
    } catch {
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [currentPage, search, statusFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Pagamentos</h1>
      </div>

      <div className="flex gap-3 mb-4">
        <div className="relative max-w-sm flex-1">
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
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setCurrentPage(1);
          }}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
        >
          <option value="">Todos os status</option>
          <option value="pending">Pendente</option>
          <option value="approved">Aprovado</option>
          <option value="paid">Pago</option>
          <option value="rejected">Rejeitado</option>
        </select>
      </div>

      <DataTable
        columns={columns}
        data={data}
        loading={loading}
        totalItems={totalItems}
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        keyExtractor={(item) => String(item.id)}
        emptyMessage="Nenhum pagamento encontrado"
      />
    </div>
  );
}
