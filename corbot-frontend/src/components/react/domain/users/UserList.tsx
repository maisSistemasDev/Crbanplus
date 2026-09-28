import { useState, useEffect, useCallback } from 'react';
import { useStore } from '@nanostores/react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { $currentUser } from '../../../../lib/stores/auth';
import { DataTable } from '../../ui/DataTable';
import { Button } from '../../ui/Button';
import { PageHeader } from '../../ui/PageHeader';
import { Badge } from '../../ui/Badge';
import { ROLE_LABELS, ROLE_COLORS } from '../../../../lib/utils/roles';
import { formatCPF } from '../../../../lib/utils/format';
import type { Role } from '../../../../lib/utils/roles';
import type { User, PaginatedResponse } from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { Plus, Search, KeyRound, Users, UserCheck, UserX, Building2 } from 'lucide-react';
import clsx from 'clsx';
import { UserBankAccessModal } from '../bank-access/UserBankAccessModal';
import { SearchSelect } from '../../ui/SearchSelect';

interface CompanyOption {
  id: string;
  name: string;
}

interface UserListProps {
  endpoint?: string;
  title?: string;
  showCreateButton?: boolean;
  role?: string;
  showCompanyFilter?: boolean;
}

export function UserList({
  endpoint = ENDPOINTS.USERS,
  title = 'Usuarios',
  showCreateButton = true,
  role,
  showCompanyFilter = false,
}: UserListProps) {
  const currentUser = useStore($currentUser);
  const isGerenteComercial = currentUser?.role === 'gerente_comercial';
  const allowCreate = showCreateButton && !isGerenteComercial;
  const [data, setData] = useState<User[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [companyFilter, setCompanyFilter] = useState('');
  const [companies, setCompanies] = useState<CompanyOption[]>([]);
  const [accessUser, setAccessUser] = useState<User | null>(null);

  const canFilterByCompany =
    showCompanyFilter &&
    (currentUser?.role === 'admin' || currentUser?.role === 'colaborador' || currentUser?.role === 'gerente_comercial');

  useEffect(() => {
    if (!canFilterByCompany) return;
    api
      .get<CompanyOption[] | { results: CompanyOption[] }>(`${ENDPOINTS.COMPANIES}?page_size=500`)
      .then((res) => {
        const items = Array.isArray(res) ? res : (res.results ?? []);
        setCompanies(items);
      })
      .catch(() => setCompanies([]));
  }, [canFilterByCompany]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(currentPage) });
      if (search) params.set('search', search);
      if (role) params.set('role', role);
      if (companyFilter) params.set('company', companyFilter);
      const res = await api.get<PaginatedResponse<User> | User[]>(`${endpoint}?${params}`);
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
  }, [endpoint, currentPage, search, role, companyFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const columns: Column<User>[] = [
    {
      key: 'first_name',
      header: 'Nome',
      sortable: true,
      render: (item) => (
        <span className="font-semibold text-slate-800">
          {item.first_name} {item.last_name}
        </span>
      ),
    },
    {
      key: 'cpf',
      header: 'CPF',
      render: (item) => formatCPF(item.cpf),
    },
    {
      key: 'email',
      header: 'Email',
      sortable: true,
    },
    {
      key: 'role',
      header: 'Perfil',
      render: (item) => (
        <span className={clsx('text-xs font-medium px-2.5 py-1 rounded-full inline-flex items-center', ROLE_COLORS[item.role as Role])}>
          {ROLE_LABELS[item.role as Role]}
        </span>
      ),
    },
    {
      key: 'company_name',
      header: 'Empresa',
      render: (item) => item.company_name || '-',
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

  const totalUsers = data.length;
  const activeUsers = data.filter((user) => user.is_active).length;
  const inactiveUsers = totalUsers - activeUsers;

  return (
    <div className="space-y-4">
      <PageHeader
        title={title}
        subtitle={role ? `Visualização de ${ROLE_LABELS[role as Role]}` : undefined}
        actions={
          allowCreate ? (
            <a href="/users/create">
              <Button size="sm" className="!bg-[var(--color-primary)] !text-white hover:!opacity-90">
                <Plus size={16} />
                Novo usuário
              </Button>
            </a>
          ) : undefined
        }
      />

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-500">Total</span>
            <div className="rounded-lg bg-slate-100 p-2 text-slate-600">
              <Users size={16} />
            </div>
          </div>
          <div className="mt-3 text-3xl font-semibold text-slate-800">{totalUsers}</div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-500">Ativos</span>
            <div className="rounded-lg bg-emerald-100 p-2 text-emerald-600">
              <UserCheck size={16} />
            </div>
          </div>
          <div className="mt-3 text-3xl font-semibold text-slate-800">{activeUsers}</div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-500">Inativos</span>
            <div className="rounded-lg bg-rose-100 p-2 text-rose-600">
              <UserX size={16} />
            </div>
          </div>
          <div className="mt-3 text-3xl font-semibold text-slate-800">{inactiveUsers}</div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="relative max-w-md flex-1 min-w-[220px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Buscar por nome ou CPF..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2.5 pl-9 pr-3 text-sm text-slate-700 outline-none transition focus:border-[var(--color-primary)] focus:bg-white"
            />
          </div>

          {canFilterByCompany && companies.length > 1 && (
            <div className="w-full lg:max-w-xs">
              <SearchSelect
                label="Empresa"
                placeholder="Todas as empresas"
                options={[
                  { value: '', label: 'Todas as empresas' },
                  ...companies.map((c) => ({ value: c.id, label: c.name })),
                ]}
                value={companyFilter}
                onChange={(e) => {
                  setCompanyFilter(e.target.value);
                  setCurrentPage(1);
                }}
              />
            </div>
          )}
        </div>

        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <DataTable
            columns={columns as unknown as Column<Record<string, unknown>>[]}
            data={data as unknown as Record<string, unknown>[]}
            loading={loading}
            totalItems={totalItems}
            currentPage={currentPage}
            onPageChange={setCurrentPage}
            onRowClick={(item) => (window.location.href = `${window.location.origin}/users/${(item as unknown as User).id}`)}
            keyExtractor={(item) => (item as unknown as User).id}
            emptyMessage="Nenhum usuário encontrado"
            rowActions={
              isGerenteComercial
                ? undefined
                : (item) => {
              const user = item as unknown as User;
              return (
                <button
                  type="button"
                  onClick={() => setAccessUser(user)}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-slate-600 transition hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-bg)] hover:text-[var(--color-primary)]"
                  title="Gerenciar acessos bancários"
                >
                  <KeyRound size={14} />
                  Acessos
                </button>
              );
            }}
          />
        </div>
      </div>

      {accessUser && (
        <UserBankAccessModal
          user={accessUser}
          onClose={() => setAccessUser(null)}
        />
      )}
    </div>
  );
}
