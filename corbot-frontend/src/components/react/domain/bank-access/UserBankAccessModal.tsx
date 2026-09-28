import { useState, useEffect, useCallback } from 'react';
import { useStore } from '@nanostores/react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { $currentUser } from '../../../../lib/stores/auth';
import { Modal } from '../../ui/Modal';
import { DataTable } from '../../ui/DataTable';
import { Button } from '../../ui/Button';
import { Badge } from '../../ui/Badge';
import { DynamicForm } from '../../forms/DynamicForm';
import type { BankAccess, FormFieldDef, PaginatedResponse, User } from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { buildBankAccessFormFields, defaultBankAccessValues } from './formFields';
import { Plus, Pencil } from 'lucide-react';
import toast from 'react-hot-toast';

interface UserBankAccessModalProps {
  user: User | null;
  onClose: () => void;
}

const MANAGE_ROLES = new Set(['admin', 'empresa_admin', 'gerente']);

const listColumns: Column<BankAccess>[] = [
  {
    key: 'bank_name',
    header: 'Banco',
    sortable: true,
  },
  {
    key: 'username',
    header: 'Login',
    render: (item) => (
      <span className="font-mono text-xs">{item.username}</span>
    ),
  },
  {
    key: 'is_master',
    header: 'Master',
    render: (item) => (
      <Badge variant={item.is_master ? 'warning' : 'default'}>
        {item.is_master ? 'Corban' : 'Equipe'}
      </Badge>
    ),
  },
  {
    key: 'notes',
    header: 'Obs.',
    render: (item) => item.notes || '-',
  },
  {
    key: 'link',
    header: 'Link',
    render: (item) => {
      if (!item.link) return '-';
      return (
        <a
          href={item.link}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 text-xs underline"
          onClick={(e) => e.stopPropagation()}
        >
          Abrir
        </a>
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
];

export function UserBankAccessModal({ user, onClose }: UserBankAccessModalProps) {
  const currentUser = useStore($currentUser);
  const canManage = MANAGE_ROLES.has(currentUser?.role ?? '');

  const [accesses, setAccesses] = useState<BankAccess[]>([]);
  const [loading, setLoading] = useState(true);
  const [formFields, setFormFields] = useState<FormFieldDef[]>([]);
  const [editAccess, setEditAccess] = useState<BankAccess | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const fetchAccesses = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({
        user: String(user.id),
        page_size: '100',
      });
      const res = await api.get<PaginatedResponse<BankAccess> | BankAccess[]>(
        `${ENDPOINTS.BANK_ACCESSES}?${params}`,
      );
      if (Array.isArray(res)) {
        setAccesses(res);
      } else {
        setAccesses(res.results ?? []);
      }
    } catch (err) {
      toast.error(extractErrorMessage(err));
      setAccesses([]);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (!user) return;
    fetchAccesses();
    api.get<FormFieldDef[]>(ENDPOINTS.FORM_FIELDS_BANK_ACCESS)
      .then((fields) => setFormFields(Array.isArray(fields) ? fields : []))
      .catch(() => {});
  }, [user, fetchAccesses]);

  async function handleSubmit(values: Record<string, unknown>) {
    if (!user) return;
    setSaving(true);
    try {
      const payload: Record<string, unknown> = { ...values, user: user.id };
      if (editAccess && !payload.password) {
        delete payload.password;
      }
      if (user.role === 'empresa_admin') {
        payload.is_master = true;
      }
      if (editAccess) {
        await api.patch(`${ENDPOINTS.BANK_ACCESSES}${editAccess.id}/`, payload);
        toast.success('Acesso atualizado!');
      } else {
        await api.post(ENDPOINTS.BANK_ACCESSES, payload);
        toast.success('Acesso criado!');
      }
      setFormOpen(false);
      setEditAccess(null);
      fetchAccesses();
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  function openCreateForm() {
    setEditAccess(null);
    setFormOpen(true);
  }

  function openEditForm(access: BankAccess) {
    setEditAccess(access);
    setFormOpen(true);
  }

  if (!user) return null;

  const userLabel = `${user.first_name} ${user.last_name}`.trim() || user.cpf;
  const isEdit = !!editAccess;
  const formFieldsForUser = buildBankAccessFormFields(formFields, {
    isEdit,
    hideUser: true,
    targetUserRole: user.role,
  });

  return (
    <>
      <Modal
        isOpen
        onClose={onClose}
        title={`Acessos — ${userLabel}`}
        size="xl"
        scrollBody
      >
        <div className="space-y-4">
          {canManage && (
            <div className="flex justify-end">
              <Button size="sm" onClick={openCreateForm}>
                <Plus size={16} />
                Novo acesso
              </Button>
            </div>
          )}

          <DataTable
            columns={listColumns as Column<Record<string, unknown>>[]}
            data={accesses as unknown as Record<string, unknown>[]}
            loading={loading}
            emptyMessage="Nenhum acesso cadastrado para este usuário"
            keyExtractor={(item) => (item as unknown as BankAccess).id}
            onRowClick={
              canManage
                ? (item) => openEditForm(item as unknown as BankAccess)
                : undefined
            }
            rowActions={
              canManage
                ? (item) => (
                    <button
                      type="button"
                      onClick={() => openEditForm(item as unknown as BankAccess)}
                      className="inline-flex items-center justify-center w-8 h-8 rounded text-gray-500 hover:text-[var(--color-primary)] hover:bg-gray-100 transition-colors"
                      title="Editar acesso"
                    >
                      <Pencil size={16} />
                    </button>
                  )
                : undefined
            }
          />
        </div>
      </Modal>

      <Modal
        isOpen={formOpen}
        onClose={() => {
          setFormOpen(false);
          setEditAccess(null);
        }}
        title={isEdit ? (editAccess?.bank_name ?? 'Editar acesso') : 'Novo acesso'}
        size="lg"
      >
        {formFields.length > 0 && (
          <DynamicForm
            key={editAccess?.id ?? 'new'}
            fields={formFieldsForUser}
            initialValues={
              editAccess
                ? { ...editAccess, password: '' }
                : defaultBankAccessValues(user.role)
            }
            onSubmit={handleSubmit}
            loading={saving}
            submitLabel={editAccess ? 'Atualizar' : 'Criar'}
          />
        )}
      </Modal>
    </>
  );
}
