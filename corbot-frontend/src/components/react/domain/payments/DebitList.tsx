import { useCallback, useEffect, useMemo, useState } from 'react';
import { Search, Plus, RotateCcw, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

import { api } from '../../../../lib/api/client';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import type { Company, PaginatedResponse, User, UserDebit } from '../../../../lib/api/types';
import { formatCPF, formatCurrency, formatDateTime } from '../../../../lib/utils/format';
import { PageHeader } from '../../ui/PageHeader';
import { Button } from '../../ui/Button';
import { Badge } from '../../ui/Badge';
import { Modal } from '../../ui/Modal';
import { SearchSelect } from '../../ui/SearchSelect';

type DebitOwnerType = 'user' | 'company';

interface DebitFormState {
  ownerType: DebitOwnerType;
  user: string;
  company: string;
  amount: string;
  reason: string;
}

const EMPTY_FORM: DebitFormState = {
  ownerType: 'user',
  user: '',
  company: '',
  amount: '',
  reason: '',
};

const ORIGIN_LABEL: Record<string, string> = {
  manual: 'Manual',
  sinistro: 'Sinistro',
};

export function DebitList() {
  const [search, setSearch] = useState('');
  const [debits, setDebits] = useState<UserDebit[]>([]);
  const [loading, setLoading] = useState(true);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form, setForm] = useState<DebitFormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const [userQuery, setUserQuery] = useState('');
  const [userOptions, setUserOptions] = useState<User[]>([]);
  const [searchingUsers, setSearchingUsers] = useState(false);
  const [companyOptions, setCompanyOptions] = useState<Company[]>([]);

  const userSelectOptions = useMemo(
    () =>
      userOptions.map((u) => ({
        value: String(u.id),
        label: `${u.first_name} ${u.last_name} - ${u.email} - ${u.matricula || u.cpf}`,
      })),
    [userOptions],
  );
  const companySelectOptions = useMemo(
    () =>
      companyOptions.map((company) => ({
        value: String(company.id),
        label: company.document ? `${company.name} - ${company.document}` : company.name,
      })),
    [companyOptions],
  );

  const loadDebits = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page_size: '30' });
      if (search.trim()) params.set('search', search.trim());
      const response = await api.get<PaginatedResponse<UserDebit> | UserDebit[]>(`${ENDPOINTS.DEBITS}?${params.toString()}`);
      setDebits(Array.isArray(response) ? response : response.results);
    } catch (error) {
      toast.error(extractErrorMessage(error));
      setDebits([]);
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    loadDebits();
  }, [loadDebits]);

  async function searchUsers() {
    const q = userQuery.trim();
    if (!q) {
      setUserOptions([]);
      return;
    }

    setSearchingUsers(true);
    try {
      const params = new URLSearchParams({ search: q, page_size: '30' });
      const response = await api.get<PaginatedResponse<User> | User[]>(`${ENDPOINTS.USERS}?${params.toString()}`);
      const users = Array.isArray(response) ? response : response.results;
      setUserOptions(users.filter((u) => u.role !== 'admin' && u.role !== 'colaborador'));
    } catch (error) {
      toast.error(extractErrorMessage(error));
      setUserOptions([]);
    } finally {
      setSearchingUsers(false);
    }
  }

  async function loadCompanies() {
    try {
      const params = new URLSearchParams({ page_size: '500' });
      const response = await api.get<PaginatedResponse<Company> | Company[]>(`${ENDPOINTS.COMPANIES}?${params.toString()}`);
      setCompanyOptions(Array.isArray(response) ? response : response.results);
    } catch (error) {
      toast.error(extractErrorMessage(error));
      setCompanyOptions([]);
    }
  }

  function openCreateModal() {
    setForm(EMPTY_FORM);
    setUserQuery('');
    setUserOptions([]);
    setIsModalOpen(true);
    if (companyOptions.length === 0) void loadCompanies();
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (form.ownerType === 'user' && !form.user) {
      toast.error('Selecione um usuário do corban.');
      return;
    }
    if (form.ownerType === 'company' && !form.company) {
      toast.error('Selecione o corban.');
      return;
    }
    if (!form.reason.trim()) {
      toast.error('Motivo é obrigatório.');
      return;
    }

    setSaving(true);
    try {
      await api.post(ENDPOINTS.DEBITS, {
        ...(form.ownerType === 'user' ? { user: Number(form.user) } : { company: form.company }),
        amount: Number(form.amount),
        reason: form.reason.trim(),
      });
      toast.success('Débito lançado com sucesso.');
      setIsModalOpen(false);
      await loadDebits();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteDebit(item: UserDebit) {
    if (!window.confirm(`Excluir o debito de ${item.owner_name || '-'}?`)) {
      return;
    }

    try {
      await api.delete(ENDPOINTS.DEBIT_DETAIL(item.id));
      toast.success('Debito excluido com sucesso.');
      await loadDebits();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Debitos"
        subtitle="Lance débitos para um corban ou para um usuário. O saldo pendente é abatido automaticamente na liberação das comissões."
      />

      <section className="card">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <div className="relative min-w-[280px] flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Pesquisar por matrícula, email ou CPF"
              className="w-full rounded border border-gray-300 py-2 pl-9 pr-3 text-sm"
            />
          </div>
          <Button variant="secondary" size="sm" onClick={() => void loadDebits()}>
            <RotateCcw size={14} />
            Atualizar
          </Button>
          <Button size="sm" onClick={openCreateModal}>
            <Plus size={14} />
            Novo debito
          </Button>
        </div>

        {loading ? (
          <p className="text-sm text-gray-500">Carregando debitos...</p>
        ) : debits.length === 0 ? (
          <p className="text-sm text-gray-500">Nenhum debito encontrado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs uppercase text-gray-500">
                  <th className="py-2 pr-3">Dono</th>
                  <th className="py-2 pr-3">CPF/CNPJ</th>
                  <th className="py-2 pr-3">Matricula</th>
                  <th className="py-2 pr-3">Motivo</th>
                  <th className="py-2 pr-3">Origem</th>
                  <th className="py-2 pr-3">Valor</th>
                  <th className="py-2 pr-3">Saldo</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Criado em</th>
                  <th className="py-2 text-right">Acoes</th>
                </tr>
              </thead>
              <tbody>
                {debits.map((item) => (
                  <tr key={item.id} className="border-b border-gray-50">
                    <td className="py-2 pr-3 font-medium text-gray-800">
                      {item.owner_name || '-'}
                      <p className="text-xs text-gray-500">
                        {item.owner_type === 'company' ? 'Corban' : item.user_details?.email || 'Usuário'}
                      </p>
                    </td>
                    <td className="py-2 pr-3 text-gray-600">
                      {item.owner_type === 'company'
                        ? item.company_details?.document || '-'
                        : formatCPF(item.user_details?.cpf || '')}
                    </td>
                    <td className="py-2 pr-3 text-gray-600">{item.user_details?.matricula || '-'}</td>
                    <td className="py-2 pr-3 text-gray-700">{item.reason}</td>
                    <td className="py-2 pr-3">
                      <Badge variant={item.origin === 'sinistro' ? 'error' : 'default'}>
                        {ORIGIN_LABEL[item.origin] || item.origin}
                      </Badge>
                    </td>
                    <td className="py-2 pr-3 text-gray-800">{formatCurrency(Number(item.amount))}</td>
                    <td className={`py-2 pr-3 font-semibold ${Number(item.remaining_amount) > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                      {formatCurrency(-Number(item.remaining_amount))}
                    </td>
                    <td className="py-2 pr-3">
                      <Badge variant={item.is_active ? 'warning' : 'success'}>
                        {item.is_active ? 'Pendente' : 'Quitado'}
                      </Badge>
                    </td>
                    <td className="py-2 pr-3 text-gray-500">{formatDateTime(item.created_at)}</td>
                    <td className="py-2 text-right">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                        onClick={() => void handleDeleteDebit(item)}
                        title="Excluir debito"
                      >
                        <Trash2 size={14} />
                        Excluir
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Novo debito"
      >
        <form className="space-y-3" onSubmit={handleSubmit}>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Dono do debito</label>
            <div className="flex gap-2">
              {(['user', 'company'] as DebitOwnerType[]).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setForm((prev) => ({ ...prev, ownerType: type, user: '', company: '' }))}
                  className={`flex-1 rounded border px-3 py-2 text-sm ${
                    form.ownerType === type
                      ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/10 text-[var(--color-primary)]'
                      : 'border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  {type === 'user' ? 'Usuario' : 'Corban'}
                </button>
              ))}
            </div>
          </div>

          {form.ownerType === 'user' ? (
            <>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Buscar usuario por matricula, email ou CPF</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={userQuery}
                    onChange={(e) => setUserQuery(e.target.value)}
                    placeholder="Digite matricula, email ou CPF"
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                  />
                  <Button type="button" variant="secondary" onClick={() => void searchUsers()} disabled={searchingUsers}>
                    {searchingUsers ? 'Buscando...' : 'Buscar'}
                  </Button>
                </div>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Usuario corban</label>
                <SearchSelect
                  required
                  placeholder="Selecione"
                  value={form.user}
                  options={userSelectOptions}
                  onChange={(e) => setForm((prev) => ({ ...prev, user: e.target.value }))}
                />
              </div>
            </>
          ) : (
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Corban</label>
              <SearchSelect
                required
                placeholder="Selecione"
                value={form.company}
                options={companySelectOptions}
                onChange={(e) => setForm((prev) => ({ ...prev, company: e.target.value }))}
              />
            </div>
          )}

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Valor do debito</label>
            <input
              required
              type="number"
              min="0.01"
              step="0.01"
              value={form.amount}
              onChange={(e) => setForm((prev) => ({ ...prev, amount: e.target.value }))}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Motivo</label>
            <textarea
              required
              value={form.reason}
              onChange={(e) => setForm((prev) => ({ ...prev, reason: e.target.value }))}
              className="h-24 w-full rounded border border-gray-300 px-3 py-2 text-sm"
              placeholder="Descreva o motivo do debito"
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setIsModalOpen(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? 'Salvando...' : 'Lancar debito'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
