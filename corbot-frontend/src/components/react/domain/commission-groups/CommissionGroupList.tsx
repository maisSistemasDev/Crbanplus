import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { DataTable } from '../../ui/DataTable';
import { Button } from '../../ui/Button';
import { PageHeader } from '../../ui/PageHeader';
import { Badge } from '../../ui/Badge';
import { Modal } from '../../ui/Modal';
import { formatDate } from '../../../../lib/utils/format';
import type { CommissionGroup, PaginatedResponse } from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { Plus, Search, Users, Trash2, PowerOff, Power } from 'lucide-react';
import toast from 'react-hot-toast';
import { CommissionGroupForm } from './CommissionGroupForm';
import { SuggestionsBanner } from '../ai-agent/SuggestionsBanner';

export function CommissionGroupList() {
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(currentPage), scope: 'promotora' });
      if (search) params.set('search', search);
      const res = await api.get<PaginatedResponse<CommissionGroup> | CommissionGroup[]>(`${ENDPOINTS.COMMISSION_GROUPS}?${params}`);
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

  async function handleToggleActive(item: Record<string, unknown>, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await api.patch(`${ENDPOINTS.COMMISSION_GROUPS}${item.id}/`, { is_active: !item.is_active });
      toast.success(item.is_active ? 'Grupo inativado' : 'Grupo ativado');
      fetchData();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    }
  }

  async function handleDelete(item: Record<string, unknown>, e: React.MouseEvent) {
    e.stopPropagation();
    if (!window.confirm(`Excluir o grupo "${item.name}"? Esta ação não pode ser desfeita.`)) return;
    try {
      await api.delete(`${ENDPOINTS.COMMISSION_GROUPS}${item.id}/`);
      toast.success('Grupo excluído');
      fetchData();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    }
  }

  const columns: Column<Record<string, unknown>>[] = [
    {
      key: 'name',
      header: 'Nome',
      sortable: true,
      render: (item) => (
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color as string }} />
          <span className="font-medium text-gray-900">{item.name as string}</span>
        </div>
      ),
    },
    {
      key: 'description',
      header: 'Descricao',
      render: (item) => (
        <span className="text-gray-500 truncate max-w-xs block">
          {(item.description as string) || '-'}
        </span>
      ),
    },
    {
      key: 'sellers',
      header: 'Membros',
      render: (item) => {
        const sellers = (item.sellers as number[]) || [];
        const leaders = (item.leaders as number[]) || [];
        return (
          <span className="flex items-center gap-1 text-gray-500">
            <Users size={14} />
            {sellers.length + leaders.length}
          </span>
        );
      },
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (item) => (
        <Badge variant={item.is_active ? 'success' : 'error'}>
          {item.is_active ? 'Ativo' : 'Inativo'}
        </Badge>
      ),
    },
    {
      key: 'created_at',
      header: 'Criado em',
      render: (item) => formatDate(item.created_at as string),
    },
    {
      key: 'actions',
      header: '',
      render: (item) => (
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <button
            title={item.is_active ? 'Inativar' : 'Ativar'}
            onClick={(e) => handleToggleActive(item, e)}
            className="p-1 rounded hover:bg-gray-100 text-gray-500 hover:text-yellow-600"
          >
            {item.is_active ? <PowerOff size={15} /> : <Power size={15} />}
          </button>
          <button
            title="Excluir"
            onClick={(e) => handleDelete(item, e)}
            className="p-1 rounded hover:bg-gray-100 text-gray-500 hover:text-red-600"
          >
            <Trash2 size={15} />
          </button>
        </div>
      ),
    },
  ];

  async function openCreate() {
    setModalOpen(true);
  }

  async function handleSubmit(values: Record<string, any>) {
    setSaving(true);
    try {
      await api.post(ENDPOINTS.COMMISSION_GROUPS, values);
      toast.success('Grupo criado com sucesso!');
      setModalOpen(false);
      fetchData();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <SuggestionsBanner />
      <PageHeader
        title="Grupos da Promotora"
        subtitle="Grupos sem Corban vinculado. Para equipes de um Corban, use Equipes → Por Corban."
        actions={
          <Button onClick={openCreate} data-tour="create-group-btn">
            <Plus size={16} />
            Nova equipe
          </Button>
        }
      />

      <div className="mb-4">
        <div className="relative max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar equipe..."
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
        onRowClick={(item) => (window.location.href = `${window.location.origin}/commission-groups/${item.id}`)}
        keyExtractor={(item) => String(item.id)}
        emptyMessage="Nenhuma equipe encontrada"
      />

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Nova Equipe">
        <CommissionGroupForm
          forcedType="promotora"
          onSubmit={handleSubmit}
          loading={saving}
          onCancel={() => setModalOpen(false)}
        />
      </Modal>
    </div>
  );
}
