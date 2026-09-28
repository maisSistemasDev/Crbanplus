import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { DataTable } from '../../ui/DataTable';
import { Button } from '../../ui/Button';
import { PageHeader } from '../../ui/PageHeader';
import { Badge } from '../../ui/Badge';
import { formatDate } from '../../../../lib/utils/format';
import type { ProposalBatch, PaginatedResponse } from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { Upload, Search } from 'lucide-react';

const STATUS_MAP: Record<string, { label: string; variant: 'default' | 'success' | 'warning' | 'error' | 'info' }> = {
  pending: { label: 'Pendente', variant: 'warning' },
  processing: { label: 'Processando', variant: 'info' },
  completed: { label: 'Concluído', variant: 'success' },
  failed: { label: 'Falhou', variant: 'error' },
  partial: { label: 'Parcial', variant: 'warning' },
};

const columns: Column<Record<string, unknown>>[] = [
  {
    key: 'id',
    header: 'ID',
    render: (item) => (
      <span className="text-xs font-mono text-gray-500">
        {(item.id as string).slice(0, 8)}...
      </span>
    ),
  },
  { key: 'bank_name', header: 'Banco', sortable: true },
  { key: 'layout_name', header: 'Layout' },
  {
    key: 'status',
    header: 'Status',
    render: (item) => {
      const s = STATUS_MAP[(item.status as string)] || { label: item.status, variant: 'default' as const };
      return <Badge variant={s.variant}>{s.label}</Badge>;
    },
  },
  {
    key: 'total_rows',
    header: 'Propostas',
    render: (item) => (
      <span>
        <span className="text-green-600">{item.processed_rows as number}</span>
        {' / '}
        <span>{item.total_rows as number}</span>
        {(item.errored_rows as number) > 0 && (
          <span className="text-red-500 ml-1">({item.errored_rows} erros)</span>
        )}
      </span>
    ),
  },
  {
    key: 'created_at',
    header: 'Data',
    sortable: true,
    render: (item) => formatDate(item.created_at as string),
  },
];

export function BatchList() {
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(currentPage) });
      if (search) params.set('search', search);
      const res = await api.get<PaginatedResponse<ProposalBatch> | ProposalBatch[]>(`${ENDPOINTS.BATCHES}?${params}`);
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
  }, [currentPage, search]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div>
      <PageHeader
        title="Lotes de propostas"
        actions={
          <a href="/proposals/batches/upload">
            <Button size="sm">
              <Upload size={16} />
              Enviar lote
            </Button>
          </a>
        }
      />

      <div className="mb-4">
        <div className="relative max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar lote..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
          />
        </div>
      </div>

      <DataTable
        columns={columns}
        data={data}
        loading={loading}
        totalItems={totalItems}
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        onRowClick={(item) => (window.location.href = `${window.location.origin}/proposals/batches/${item.id}`)}
        keyExtractor={(item) => item.id as string}
        emptyMessage="Nenhum lote encontrado"
      />
    </div>
  );
}
