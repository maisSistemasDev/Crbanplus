import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { DataTable } from '../../ui/DataTable';
import { Button } from '../../ui/Button';
import { PageHeader } from '../../ui/PageHeader';
import { DynamicForm } from '../../forms/DynamicForm';
import { Modal } from '../../ui/Modal';
import { Badge } from '../../ui/Badge';
import type { FormFieldDef, PaginatedResponse } from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { Plus, Search, Trash2, Pencil } from 'lucide-react';
import toast from 'react-hot-toast';
import { extractErrorMessage } from '../../../../lib/api/errors';

interface CrudPageProps {
  title: string;
  endpoint: string;
  formFieldsEndpoint: string;
  columns: Column<Record<string, unknown>>[];
  keyField?: string;
  createLabel?: string;
  searchPlaceholder?: string;
  customActions?: React.ReactNode;
  filterBar?: React.ReactNode;
  extraParams?: Record<string, string>;
  selectable?: boolean;
  bulkDeleteEndpoint?: string;
  renderForm?: (props: {
    item: Record<string, unknown> | null;
    onSubmit: (values: Record<string, any>) => Promise<void>;
    onClose: () => void;
    saving: boolean;
  }) => React.ReactNode;
  filterFormFields?: (fields: FormFieldDef[], item: Record<string, unknown> | null) => FormFieldDef[];
  getEditModalTitle?: (item: Record<string, unknown>) => string;
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
  filterBar,
  extraParams,
  selectable = false,
  bulkDeleteEndpoint,
  renderForm,
  filterFormFields,
  getEditModalTitle,
}: CrudPageProps) {
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editItem, setEditItem] = useState<Record<string, unknown> | null>(null);
  const [formFields, setFormFields] = useState<FormFieldDef[]>([]);
  const [saving, setSaving] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);

  // Reset para página 1 quando os filtros externos mudam
  useEffect(() => {
    setCurrentPage(1);
  }, [extraParams]);

  // Debounce da busca (evita refetch a cada tecla)
  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput);
      setCurrentPage(1);
    }, 400);
    return () => clearTimeout(t);
  }, [searchInput]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
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
    } catch (err) {
      setFetchError(extractErrorMessage(err));
      setData([]);
      setTotalItems(0);
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
    } catch (err) {
      toast.error(extractErrorMessage(err));
    }
  }

  function buildSubmitPayload(values: Record<string, any>) {
    const fileFieldNames = new Set(
      formFields.filter((f) => f.type === 'file').map((f) => f.name),
    );
    const hasFiles = Object.values(values).some((v) => v instanceof File);

    if (hasFiles) {
      const formData = new FormData();
      Object.entries(values).forEach(([key, val]) => {
        if (val === null || val === undefined) return;
        if (fileFieldNames.has(key) && typeof val === 'string') return;
        if (val instanceof File) {
          formData.append(key, val);
        } else if (typeof val === 'boolean') {
          formData.append(key, val ? 'true' : 'false');
        } else if (typeof val === 'object') {
          formData.append(key, JSON.stringify(val));
        } else {
          formData.append(key, String(val));
        }
      });
      return { formData };
    }

    const json: Record<string, any> = {};
    Object.entries(values).forEach(([key, val]) => {
      if (val === null || val === undefined) return;
      if (fileFieldNames.has(key)) return;
      if (val instanceof File) return;
      // Mantém arrays/objetos aninhados (ex.: commission_ranges)
      json[key] = val;
    });
    return { json };
  }

  async function handleSubmit(values: Record<string, any>) {
    setSaving(true);
    try {
      const payload = buildSubmitPayload(values);
      if (editItem) {
        const url = `${endpoint}${editItem[keyField]}/`;
        if ('formData' in payload) {
          await api.upload(url, payload.formData, 'PATCH');
        } else {
          await api.patch(url, payload.json);
        }
        toast.success('Atualizado com sucesso!');
      } else {
        if ('formData' in payload) {
          await api.upload(endpoint, payload.formData);
        } else {
          await api.post(endpoint, payload.json);
        }
        toast.success('Criado com sucesso!');
      }
      setModalOpen(false);
      setEditItem(null);
      fetchData();
    } catch (err) {
      toast.error(extractErrorMessage(err));
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
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setBulkDeleting(false);
    }
  }

  return (
    <div>
      <PageHeader
        title={title}
        actions={
          <>
            {customActions}
            <Button onClick={() => openForm()}>
              <Plus size={16} />
              {createLabel}
            </Button>
          </>
        }
      />

      <div className="mb-4 flex items-center gap-3 flex-wrap">
        <div className="relative max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder={searchPlaceholder}
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-sm border border-gray-200 rounded-md outline-none focus:border-[var(--color-primary)]"
          />
        </div>
        {filterBar}
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

      {fetchError && (
        <div className="mb-3 flex items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          <span>{fetchError}</span>
          <Button size="sm" variant="secondary" onClick={() => fetchData()}>
            Tentar novamente
          </Button>
        </div>
      )}

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
        rowActions={
          selectable
            ? (item) => (
                <button
                  type="button"
                  onClick={() => openForm(item)}
                  className="inline-flex items-center justify-center w-8 h-8 rounded text-gray-500 hover:text-[var(--color-primary)] hover:bg-gray-100 transition-colors"
                  title="Editar"
                >
                  <Pencil size={16} />
                </button>
              )
            : undefined
        }
      />

      <Modal
        isOpen={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setEditItem(null);
        }}
        title={
          editItem
            ? (getEditModalTitle?.(editItem) ?? `Editar ${title.slice(0, -1)}`)
            : createLabel
        }
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
            fields={filterFormFields ? filterFormFields(formFields, editItem) : formFields}
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
