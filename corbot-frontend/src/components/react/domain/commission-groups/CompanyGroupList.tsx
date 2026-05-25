import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { DataTable } from '../../ui/DataTable';
import { Button } from '../../ui/Button';
import { Badge } from '../../ui/Badge';
import { DynamicForm } from '../../forms/DynamicForm';
import { Modal } from '../../ui/Modal';
import { formatDate } from '../../../../lib/utils/format';
import type { CommissionGroupByCompany, PaginatedResponse, FormFieldDef } from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { Plus, Search, Building, Trash2, PowerOff, Power } from 'lucide-react';
import toast from 'react-hot-toast';

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
    key: 'companies',
    header: 'Corbans',
    render: (item) => {
      const companies = (item.companies as unknown[]) || [];
      return (
        <span className="flex items-center gap-1 text-gray-500">
          <Building size={14} />
          {companies.length}
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
];

export function CompanyGroupList() {
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [formFields, setFormFields] = useState<FormFieldDef[]>([]);
  const [saving, setSaving] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(currentPage) });
      if (search) params.set('search', search);
      const res = await api.get<PaginatedResponse<CommissionGroupByCompany> | CommissionGroupByCompany[]>(`${ENDPOINTS.COMMISSION_GROUPS_BY_COMPANY}?${params}`);
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
      await api.patch(`${ENDPOINTS.COMMISSION_GROUPS_BY_COMPANY}${item.id}/`, { is_active: !item.is_active });
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
      await api.delete(`${ENDPOINTS.COMMISSION_GROUPS_BY_COMPANY}${item.id}/`);
      toast.success('Grupo excluído');
      fetchData();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    }
  }

  const columnsWithActions: Column<Record<string, unknown>>[] = [
    ...columns,
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
    try {
      const fields = await api.get<FormFieldDef[]>(ENDPOINTS.FORM_FIELDS_COMMISSION_GROUPS);
      setFormFields(Array.isArray(fields) ? fields : []);
      setModalOpen(true);
    } catch (error) {
      toast.error(extractErrorMessage(error));
    }
  }

  async function handleSubmit(values: Record<string, any>) {
    setSaving(true);
    try {
      await api.post(ENDPOINTS.COMMISSION_GROUPS_BY_COMPANY, values);
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
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Equipes por Empresa</h1>
        <Button onClick={openCreate}>
          <Plus size={16} />
          Nova Equipe
        </Button>
      </div>

      <div className="mb-4">
        <div className="relative max-w-sm">
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
      </div>

      <DataTable
        columns={columnsWithActions}
        data={data}
        loading={loading}
        totalItems={totalItems}
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        onRowClick={(item) => (window.location.href = `${window.location.origin}/commission-groups/by-company/${item.id}`)}
        keyExtractor={(item) => String(item.id)}
        emptyMessage="Nenhuma equipe encontrada"
      />

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Nova Equipe por Empresa">
        <DynamicForm
          fields={formFields}
          onSubmit={handleSubmit}
          loading={saving}
          submitLabel="Criar"
        />
      </Modal>
    </div>
  );
}
