import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { DataTable } from '../../ui/DataTable';
import { Button } from '../../ui/Button';
import { PageHeader } from '../../ui/PageHeader';
import { formatDate } from '../../../../lib/utils/format';
import { extractErrorMessage } from '../../../../lib/api/errors';
import type { Layout, PaginatedResponse } from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { Plus, Search, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

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

function LayoutBulkDeleteButton({
  selectedKeys,
  onDeleted,
}: {
  selectedKeys: Set<string>;
  onDeleted: () => void;
}) {
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    if (selectedKeys.size === 0) return;
    if (!window.confirm(`Deseja excluir ${selectedKeys.size} layout(s) selecionado(s)? Esta ação não pode ser desfeita.`)) return;
    setDeleting(true);
    try {
      await api.delete(ENDPOINTS.LAYOUTS_BULK_DELETE, { ids: [...selectedKeys] });
      toast.success(`${selectedKeys.size} layout(s) excluído(s) com sucesso!`);
      onDeleted();
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Button variant="danger" size="sm" onClick={handleDelete} disabled={deleting}>
      <Trash2 size={16} />
      {deleting ? 'Excluindo...' : `Excluir ${selectedKeys.size} selecionado(s)`}
    </Button>
  );
}

export function LayoutList() {
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

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
      <PageHeader
        title="Layouts de importação"
        actions={
          <a href="/proposals/layouts/create">
            <Button size="sm">
              <Plus size={16} />
              Novo layout
            </Button>
          </a>
        }
      />

      <div className="mb-4 flex items-center gap-3 flex-wrap">
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
        {selectedKeys.size > 0 && (
          <LayoutBulkDeleteButton
            selectedKeys={selectedKeys}
            onDeleted={() => { setSelectedKeys(new Set()); fetchData(); }}
          />
        )}
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
        selectable
        selectedKeys={selectedKeys}
        onSelectionChange={setSelectedKeys}
      />
    </div>
  );
}
