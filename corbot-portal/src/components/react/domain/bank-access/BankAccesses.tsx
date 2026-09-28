import { useEffect, useMemo, useState } from 'react';
import { useStore } from '@nanostores/react';
import toast from 'react-hot-toast';
import { Landmark, Plus, Pencil, Trash2, Search, X, ExternalLink } from 'lucide-react';
import { api } from '../../../../lib/api/client';
import { fetchAllPaginated } from '../../../../lib/api/pagination';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { $currentUser } from '../../../../lib/stores/auth';
import type { Bank, BankAccess, PaginatedResponse, User } from '../../../../lib/api/types';
import { PageHeader } from '../../ui/PageHeader';
import { Button } from '../../ui/Button';
import { Badge } from '../../ui/Badge';
import { EmptyState } from '../../ui/EmptyState';
import { SectionSpinner } from '../../ui/Spinner';
import { SearchSelect } from '../../ui/SearchSelect';

const PAGE_SIZE = 15;

type FormState = {
  id?: string;
  bank: string;
  user: string;
  username: string;
  password: string;
  is_master: boolean;
  is_active: boolean;
  notes: string;
  link: string;
};

const EMPTY_FORM: FormState = {
  bank: '',
  user: '',
  username: '',
  password: '',
  is_master: false,
  is_active: true,
  notes: '',
  link: '',
};

export function BankAccesses() {
  const currentUser = useStore($currentUser);
  const canManage =
    currentUser?.role === 'admin' ||
    currentUser?.role === 'empresa_admin' ||
    currentUser?.role === 'gerente';

  const [accesses, setAccesses] = useState<BankAccess[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [bankFilter, setBankFilter] = useState('');
  const [banks, setBanks] = useState<Bank[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Bank[]>(ENDPOINTS.BANKS)
      .then((res) => setBanks(Array.isArray(res) ? res : []))
      .catch(() => {});
    if (canManage) {
      fetchAllPaginated<User>(ENDPOINTS.USERS)
        .then(setUsers)
        .catch(() => {});
    }
  }, [canManage]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError('');
      try {
        const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
        if (search) params.set('search', search);
        if (bankFilter) params.set('bank', bankFilter);
        const res = await api.get<PaginatedResponse<BankAccess>>(`${ENDPOINTS.BANK_ACCESSES}?${params}`);
        if (cancelled) return;
        setAccesses(res.results);
        setCount(res.count);
      } catch (err) {
        if (!cancelled) setError(extractErrorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [page, search, bankFilter]);

  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));

  const userOptions = useMemo(
    () => users.map((u) => ({ id: u.id, label: `${u.first_name} ${u.last_name}` })),
    [users],
  );

  const bankOptions = useMemo(() => banks.map((b) => ({ value: b.id, label: b.name })), [banks]);
  const userSelectOptions = useMemo(
    () => userOptions.map((u) => ({ value: String(u.id), label: u.label })),
    [userOptions],
  );

  function openCreateModal() {
    setForm(EMPTY_FORM);
    setModalOpen(true);
  }

  function openEditModal(access: BankAccess) {
    setForm({
      id: access.id,
      bank: access.bank,
      user: String(access.user),
      username: access.username,
      password: '',
      is_master: access.is_master,
      is_active: access.is_active,
      notes: access.notes || '',
      link: access.link || '',
    });
    setModalOpen(true);
  }

  async function refreshList() {
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
    if (search) params.set('search', search);
    if (bankFilter) params.set('bank', bankFilter);
    const res = await api.get<PaginatedResponse<BankAccess>>(`${ENDPOINTS.BANK_ACCESSES}?${params}`);
    setAccesses(res.results);
    setCount(res.count);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.bank || !form.user || !form.username || (!form.id && !form.password)) {
      toast.error('Preencha banco, usuário, login e senha.');
      return;
    }
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        bank: form.bank,
        user: Number(form.user),
        username: form.username,
        is_master: form.is_master,
        is_active: form.is_active,
        notes: form.notes || null,
        link: form.link || null,
      };
      if (form.password) payload.password = form.password;

      if (form.id) {
        await api.patch(ENDPOINTS.BANK_ACCESS_DETAIL(form.id), payload);
        toast.success('Acesso atualizado com sucesso!');
      } else {
        await api.post(ENDPOINTS.BANK_ACCESSES, payload);
        toast.success('Acesso criado com sucesso!');
      }
      setModalOpen(false);
      await refreshList();
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(access: BankAccess) {
    if (!window.confirm(`Excluir o acesso "${access.username}" (${access.bank_name})?`)) return;
    setDeletingId(access.id);
    try {
      await api.delete(ENDPOINTS.BANK_ACCESS_DETAIL(access.id));
      toast.success('Acesso excluído.');
      await refreshList();
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Acessos bancários"
        subtitle="Logins e senhas dos sistemas dos bancos parceiros"
        actions={
          canManage ? (
            <Button size="sm" icon={<Plus size={16} />} onClick={openCreateModal}>
              Novo acesso
            </Button>
          ) : undefined
        }
      />

      <div className="card">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[220px]">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por login, banco ou usuário..."
              value={search}
              onChange={(e) => {
                setPage(1);
                setSearch(e.target.value);
              }}
              className="w-full rounded-lg border border-gray-200 py-1.5 pl-8 pr-3 text-sm outline-none focus:border-[var(--color-primary)]"
            />
          </div>
          <SearchSelect
            className="w-full sm:w-56"
            placeholder="Todos os bancos"
            allowEmpty
            value={bankFilter}
            options={bankOptions}
            onChange={(value) => {
              setPage(1);
              setBankFilter(value);
            }}
          />
        </div>

        {loading ? (
          <SectionSpinner />
        ) : error ? (
          <p className="py-6 text-center text-sm text-red-600">{error}</p>
        ) : accesses.length === 0 ? (
          <EmptyState icon={Landmark} title="Nenhum acesso encontrado" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase text-[var(--color-text-muted)]">
                  <th className="py-2 pr-3">Banco</th>
                  <th className="py-2 pr-3">Usuário</th>
                  <th className="py-2 pr-3">Login</th>
                  <th className="py-2 pr-3">Tipo</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Link</th>
                  {canManage && <th className="py-2 pr-3 text-right">Ações</th>}
                </tr>
              </thead>
              <tbody>
                {accesses.map((access) => (
                  <tr key={access.id} className="border-b border-gray-100">
                    <td className="py-2 pr-3">{access.bank_name}</td>
                    <td className="py-2 pr-3">{access.user_name || '—'}</td>
                    <td className="py-2 pr-3 font-mono text-xs">{access.username}</td>
                    <td className="py-2 pr-3">
                      <Badge tone={access.is_master ? 'warning' : 'primary'}>
                        {access.is_master ? 'Corban' : 'Equipe'}
                      </Badge>
                    </td>
                    <td className="py-2 pr-3">
                      <Badge tone={access.is_active ? 'success' : 'gray'}>
                        {access.is_active ? 'Ativo' : 'Inativo'}
                      </Badge>
                    </td>
                    <td className="py-2 pr-3">
                      {access.link ? (
                        <a
                          href={access.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-[var(--color-primary)] hover:underline"
                        >
                          Abrir <ExternalLink size={12} />
                        </a>
                      ) : (
                        '—'
                      )}
                    </td>
                    {canManage && (
                      <td className="py-2 pr-3 text-right">
                        <div className="flex justify-end gap-1">
                          <button
                            onClick={() => openEditModal(access)}
                            className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100"
                            title="Editar"
                          >
                            <Pencil size={15} />
                          </button>
                          <button
                            onClick={() => handleDelete(access)}
                            disabled={deletingId === access.id}
                            className="rounded-lg p-1.5 text-red-500 hover:bg-red-50 disabled:opacity-50"
                            title="Excluir"
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && count > PAGE_SIZE && (
          <div className="mt-4 flex items-center justify-between text-sm text-[var(--color-text-muted)]">
            <span>
              Página {page} de {totalPages} · {count} acessos
            </span>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Anterior
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Próxima
              </Button>
            </div>
          </div>
        )}
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-xl bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
              <h2 className="text-base font-semibold text-gray-800">
                {form.id ? 'Editar acesso' : 'Novo acesso'}
              </h2>
              <button onClick={() => setModalOpen(false)} className="rounded-lg p-1 text-gray-400 hover:bg-gray-100">
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="max-h-[70vh] overflow-y-auto px-5 py-4">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <label className="text-sm">
                  <span className="mb-1 block text-xs font-medium text-gray-600">Banco</span>
                  <SearchSelect
                    placeholder="Selecione..."
                    value={form.bank}
                    options={bankOptions}
                    onChange={(value) => setForm((f) => ({ ...f, bank: value }))}
                    disabled={!!form.id}
                    required
                  />
                </label>
                <label className="text-sm">
                  <span className="mb-1 block text-xs font-medium text-gray-600">Usuário</span>
                  <SearchSelect
                    placeholder="Selecione..."
                    value={form.user}
                    options={userSelectOptions}
                    onChange={(value) => setForm((f) => ({ ...f, user: value }))}
                    disabled={!!form.id}
                    required
                  />
                </label>
                <label className="text-sm">
                  <span className="mb-1 block text-xs font-medium text-gray-600">Login (e-mail ou CPF)</span>
                  <input
                    type="text"
                    value={form.username}
                    onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                    required
                    className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
                  />
                </label>
                <label className="text-sm">
                  <span className="mb-1 block text-xs font-medium text-gray-600">
                    {form.id ? 'Senha (deixe em branco para manter)' : 'Senha'}
                  </span>
                  <input
                    type="password"
                    value={form.password}
                    onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                    required={!form.id}
                    className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
                  />
                </label>
                <label className="text-sm sm:col-span-2">
                  <span className="mb-1 block text-xs font-medium text-gray-600">Link</span>
                  <input
                    type="url"
                    value={form.link}
                    onChange={(e) => setForm((f) => ({ ...f, link: e.target.value }))}
                    className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
                  />
                </label>
                <label className="text-sm sm:col-span-2">
                  <span className="mb-1 block text-xs font-medium text-gray-600">Observação</span>
                  <textarea
                    value={form.notes}
                    onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                    rows={2}
                    className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
                  />
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={form.is_master}
                    onChange={(e) => setForm((f) => ({ ...f, is_master: e.target.checked }))}
                    className="h-4 w-4 rounded border-gray-300 text-[var(--color-primary)]"
                  />
                  Master (Corban)
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                    className="h-4 w-4 rounded border-gray-300 text-[var(--color-primary)]"
                  />
                  Ativo
                </label>
              </div>

              <div className="mt-5 flex justify-end gap-2 border-t border-gray-100 pt-4">
                <Button type="button" variant="secondary" size="sm" onClick={() => setModalOpen(false)}>
                  Cancelar
                </Button>
                <Button type="submit" size="sm" loading={saving}>
                  Salvar
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
