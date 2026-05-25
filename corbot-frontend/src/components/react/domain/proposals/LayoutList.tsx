import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { DataTable } from '../../ui/DataTable';
import { Button } from '../../ui/Button';
import { Badge } from '../../ui/Badge';
import { formatDate } from '../../../../lib/utils/format';
import type { Layout, PaginatedResponse } from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { Plus, Search } from 'lucide-react';

const columns: Column<Record<string, unknown>>[] = [
  { key: 'name', header: 'Nome', sortable: true },
  { key: 'bank_name', header: 'Banco', sortable: true },
  {
    key: 'map_fields',
    header: 'Campos',
    render: (item) => {
      const fields = item.map_fields as unknown[];
      return <span className="text-gray-500">{fields?.length || 0} campos</span>;
    },
  },
  {
    key: 'created_at',
    header: 'Criado em',
    render: (item) => formatDate(item.created_at as string),
  },
];

export function LayoutList() {
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
      const res = await api.get<PaginatedResponse<Layout> | Layout[]>(`${ENDPOINTS.LAYOUTS}?${params}`);
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
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Layouts de Importacao</h1>
        <a href="/proposals/layouts/create">
          <Button>
            <Plus size={16} />
            Novo Layout
          </Button>
        </a>
      </div>

      <div className="mb-4">
        <div className="relative max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar layout..."
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
        keyExtractor={(item) => item.id as string}
        emptyMessage="Nenhum layout encontrado"
      />
    </div>
  );
}
