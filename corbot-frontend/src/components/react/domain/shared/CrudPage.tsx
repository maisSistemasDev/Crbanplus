import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { DataTable } from '../../ui/DataTable';
import { Button } from '../../ui/Button';
import { DynamicForm } from '../../forms/DynamicForm';
import { Modal } from '../../ui/Modal';
import { Badge } from '../../ui/Badge';
import type { FormFieldDef, PaginatedResponse } from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { Plus, Search, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

interface CrudPageProps {
  title: string;
  endpoint: string;
  formFieldsEndpoint: string;
  columns: Column<Record<string, unknown>>[];
  keyField?: string;
  createLabel?: string;
  searchPlaceholder?: string;
  customActions?: React.ReactNode;
  extraParams?: Record<string, string>;
  selectable?: boolean;
  bulkDeleteEndpoint?: string;
  renderForm?: (props: {
    item: Record<string, unknown> | null;
    onSubmit: (values: Record<string, any>) => Promise<void>;
    onClose: () => void;
    saving: boolean;
  }) => React.ReactNode;
}

export function CrudPage({
  title,
  endpoint,
  formFieldsEndpoint,
  columns,
  keyField = 'id',
  createLabel = 'Novo',
  searchPlaceholder = 'Buscar...',
  customActions,
  extraParams,
  selectable = false,
  bulkDeleteEndpoint,
  renderForm,
}: CrudPageProps) {
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editItem, setEditItem] = useState<Record<string, unknown> | null>(null);
  const [formFields, setFormFields] = useState<FormFieldDef[]>([]);
  const [saving, setSaving] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(currentPage) });
      if (search) params.set('search', search);
      if (extraParams) {
        Object.entries(extraParams).forEach(([k, v]) => { if (v) params.set(k, v); });
      }
      const res = await api.get<PaginatedResponse<Record<string, unknown>> | Record<string, unknown>[]>(`${endpoint}?${params}`);
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
      setSelectedKeys(new Set());
    }
  }, [endpoint, currentPage, search, extraParams]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function openForm(item?: Record<string, unknown>) {
    if (renderForm) {
      setEditItem(item || null);
      setModalOpen(true);
      return;
    }
    try {
      const fields = await api.get<FormFieldDef[]>(formFieldsEndpoint);
      setFormFields(Array.isArray(fields) ? fields : []);
      setEditItem(item || null);
      setModalOpen(true);
    } catch {
      toast.error('Erro ao carregar formulario');
    }
  }

  async function handleSubmit(values: Record<string, any>) {
    setSaving(true);
    try {
      if (editItem) {
        await api.patch(`${endpoint}${editItem[keyField]}/`, values);
        toast.success('Atualizado com sucesso!');
      } else {
        await api.post(endpoint, values);
        toast.success('Criado com sucesso!');
      }
      setModalOpen(false);
      setEditItem(null);
      fetchData();
    } catch {
      toast.error('Erro ao salvar');
    } finally {
      setSaving(false);
    }
  }

  async function handleBulkDelete() {
    if (!bulkDeleteEndpoint || selectedKeys.size === 0) return;
    if (!window.confirm(`Deseja excluir ${selectedKeys.size} tabela(s) selecionada(s)? Esta ação não pode ser desfeita.`)) return;
    setBulkDeleting(true);
    try {
      await api.delete(bulkDeleteEndpoint, { ids: [...selectedKeys] });
      toast.success(`${selectedKeys.size} tabela(s) excluída(s) com sucesso!`);
      fetchData();
    } catch {
      toast.error('Erro ao excluir tabelas');
    } finally {
      setBulkDeleting(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        <div className="flex items-center gap-2">
          {customActions}
          <Button onClick={() => openForm()}>
            <Plus size={16} />
            {createLabel}
          </Button>
        </div>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <div className="relative max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder={searchPlaceholder}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
          />
        </div>
        {selectable && selectedKeys.size > 0 && (
          <Button
            variant="danger"
            size="sm"
            onClick={handleBulkDelete}
            disabled={bulkDeleting}
          >
            <Trash2 size={16} />
            {bulkDeleting ? 'Excluindo...' : `Excluir ${selectedKeys.size} selecionado(s)`}
          </Button>
        )}
      </div>

      <DataTable
        columns={columns}
        data={data}
        loading={loading}
        totalItems={totalItems}
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        onRowClick={selectable ? undefined : (item) => openForm(item)}
        keyExtractor={(item) => item[keyField] as string}
        emptyMessage="Nenhum item encontrado"
        selectable={selectable}
        selectedKeys={selectedKeys}
        onSelectionChange={setSelectedKeys}
      />

      <Modal
        isOpen={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setEditItem(null);
        }}
        title={editItem ? `Editar ${title.slice(0, -1)}` : `${createLabel}`}
        size="xl"
      >
        {renderForm ? (
          renderForm({
            item: editItem,
            onSubmit: handleSubmit,
            onClose: () => { setModalOpen(false); setEditItem(null); },
            saving,
          })
        ) : (
          <DynamicForm
            fields={formFields}
            initialValues={editItem ? (editItem as Record<string, any>) : {}}
            onSubmit={handleSubmit}
            loading={saving}
            submitLabel={editItem ? 'Atualizar' : 'Criar'}
          />
        )}
      </Modal>
    </div>
  );
}
