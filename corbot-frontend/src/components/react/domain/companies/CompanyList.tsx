import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { DataTable } from '../../ui/DataTable';
import { Button } from '../../ui/Button';
import { Badge } from '../../ui/Badge';
import type { Company, PaginatedResponse } from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { Plus, Search } from 'lucide-react';

export function CompanyList() {
  const [data, setData] = useState<Company[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(currentPage) });
      if (search) params.set('search', search);
      const res = await api.get<PaginatedResponse<Company> | Company[]>(`${ENDPOINTS.COMPANIES}?${params}`);
      if (Array.isArray(res)) {
        setData(res);
        setTotalItems(res.length);
      } else {
        setData(res.results);
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

  const columns: Column<Company>[] = [
    {
      key: 'name',
      header: 'Nome',
      sortable: true,
      render: (item) => (
        <div className="flex items-center gap-3">
          {item.logo && (
            <img src={item.logo} alt="" className="h-8 w-8 rounded-full object-cover" />
          )}
          <span className="font-medium text-gray-900">{item.name}</span>
        </div>
      ),
    },
    { key: 'trading_name', header: 'Nome Fantasia', sortable: true },
    { key: 'cnpj', header: 'CNPJ' },
    { key: 'city', header: 'Cidade' },
    { key: 'state', header: 'UF', className: 'w-16' },
    {
      key: 'primary_color',
      header: 'Cor',
      render: (item) => (
        <div className="flex items-center gap-2">
          <div className="h-5 w-5 rounded-full border border-gray-200" style={{ backgroundColor: item.primary_color }} />
          <span className="text-xs text-gray-500">{item.primary_color}</span>
        </div>
      ),
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (item) => (
        <Badge variant={item.is_active ? 'success' : 'error'}>
          {item.is_active ? 'Ativa' : 'Inativa'}
        </Badge>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Corbans</h1>
        <a href="/companies/create">
          <Button>
            <Plus size={16} />
            Novo Corban
          </Button>
        </a>
      </div>

      <div className="mb-4">
        <div className="relative max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar por nome ou CNPJ..."
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
        data={data as unknown as Record<string, unknown>[]}
        loading={loading}
        totalItems={totalItems}
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        onRowClick={(item) => (window.location.href = `${window.location.origin}/companies/${(item as unknown as Company).id}`)}
        keyExtractor={(item) => (item as unknown as Company).id}
        emptyMessage="Nenhum corban encontrado"
      />
    </div>
  );
}
