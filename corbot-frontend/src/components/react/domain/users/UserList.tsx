import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { DataTable } from '../../ui/DataTable';
import { Button } from '../../ui/Button';
import { Badge } from '../../ui/Badge';
import { ROLE_LABELS, ROLE_COLORS } from '../../../../lib/utils/roles';
import { formatCPF } from '../../../../lib/utils/format';
import type { Role } from '../../../../lib/utils/roles';
import type { User, PaginatedResponse } from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { Plus, Search } from 'lucide-react';
import clsx from 'clsx';

interface UserListProps {
  endpoint?: string;
  title?: string;
  showCreateButton?: boolean;
  role?: string;
}

export function UserList({
  endpoint = ENDPOINTS.USERS,
  title = 'Usuarios',
  showCreateButton = true,
  role,
}: UserListProps) {
  const [data, setData] = useState<User[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(currentPage) });
      if (search) params.set('search', search);
      if (role) params.set('role', role);
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
  }, [endpoint, currentPage, search, role]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const columns: Column<User>[] = [
    {
      key: 'first_name',
      header: 'Nome',
      sortable: true,
      render: (item) => (
        <span className="font-medium text-gray-900">
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
        <span className={clsx('text-xs font-medium px-2 py-0.5 rounded-full', ROLE_COLORS[item.role as Role])}>
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

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        {showCreateButton && (
          <a href="/users/create">
            <Button>
              <Plus size={16} />
              Novo Usuario
            </Button>
          </a>
        )}
      </div>

      <div className="mb-4">
        <div className="relative max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar por nome ou CPF..."
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
        onRowClick={(item) => (window.location.href = `${window.location.origin}/users/${(item as unknown as User).id}`)}
        keyExtractor={(item) => (item as unknown as User).id}
        emptyMessage="Nenhum usuario encontrado"
      />
    </div>
  );
}
