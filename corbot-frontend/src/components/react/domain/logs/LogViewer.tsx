import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { DataTable } from '../../ui/DataTable';
import { PageHeader } from '../../ui/PageHeader';
import { formatDate } from '../../../../lib/utils/format';
import type { PaginatedResponse } from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { Search } from 'lucide-react';

interface LogEntry {
  id: number;
  user: number;
  user_name: string;
  action: string;
  model: string;
  object_id: string;
  details: string;
  ip_address: string;
  created_at: string;
}

interface LogViewerProps {
  title: string;
  endpoint: string;
}

const columns: Column<Record<string, unknown>>[] = [
  {
    key: 'created_at',
    header: 'Data',
    sortable: true,
    render: (item) => formatDate(item.created_at as string),
  },
  { key: 'user_name', header: 'Usuario' },
  { key: 'action', header: 'Acao' },
  { key: 'model', header: 'Modelo' },
  {
    key: 'details',
    header: 'Detalhes',
    render: (item) => (
      <span className="text-gray-500 truncate max-w-xs block text-xs">
        {(item.details as string) || '-'}
      </span>
    ),
  },
  {
    key: 'ip_address',
    header: 'IP',
    render: (item) => (
      <span className="font-mono text-xs text-gray-400">{item.ip_address as string}</span>
    ),
  },
];

export function LogViewer({ title, endpoint }: LogViewerProps) {
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
      const res = await api.get<PaginatedResponse<LogEntry> | LogEntry[]>(`${endpoint}?${params}`);
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
  }, [endpoint, currentPage, search]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div>
      <PageHeader title={title} />

      <div className="mb-4">
        <div className="relative max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar nos logs..."
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
        keyExtractor={(item) => String(item.id)}
        emptyMessage="Nenhum log encontrado"
      />
    </div>
  );
}
