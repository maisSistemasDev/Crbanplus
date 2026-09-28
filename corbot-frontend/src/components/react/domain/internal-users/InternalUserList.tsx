import { useState, useEffect } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import type { InternalUser } from '../../../../lib/api/types/internal-users';
import type { PaginatedResponse } from '../../../../lib/api/types';
import { Button } from '../../ui/Button';
import { PageHeader } from '../../ui/PageHeader';
import { Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import { COLABORADORES_ROUTES } from '../../../../lib/routes/colaboradores';

export default function InternalUserList() {
  const [users, setUsers] = useState<InternalUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.get<PaginatedResponse<InternalUser> | InternalUser[]>(
        `${ENDPOINTS.INTERNAL_USERS}?page_size=500`,
      );
      setUsers(Array.isArray(response) ? response : (response.results ?? []));
    } catch (err) {
      setError(extractErrorMessage(err));
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Tem certeza que deseja excluir este usuário?')) return;

    try {
      await api.delete(ENDPOINTS.INTERNAL_USER_DETAIL(id));
      toast.success('Usuário excluído com sucesso.');
      loadUsers();
    } catch (err) {
      toast.error(extractErrorMessage(err));
    }
  };

  const getRoleBadge = (role: string) => {
    const badges = {
      admin: 'bg-purple-100 text-purple-800',
      colaborador: 'bg-blue-100 text-blue-800',
    };
    const labels = {
      admin: 'Administrador',
      colaborador: 'Colaborador',
    };
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${badges[role as keyof typeof badges]}`}>
        {labels[role as keyof typeof labels]}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="animate-spin h-6 w-6 border-2 border-[var(--color-primary)] border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Colaboradores"
        subtitle="Equipe interna da promotora — sem vínculo com corbans"
        actions={
          <a href={COLABORADORES_ROUTES.create}>
            <Button size="sm">
              <Plus size={14} />
              Novo colaborador
            </Button>
          </a>
        }
      />

      {error && (
        <div className="mb-3 flex items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          <span>{error}</span>
          <Button size="sm" variant="secondary" onClick={loadUsers}>
            Tentar novamente
          </Button>
        </div>
      )}

      <div className="card p-0 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-100 text-sm">
          <thead className="bg-gray-50/80">
            <tr>
              {['Nome', 'CPF', 'E-mail', 'Tipo', 'Permissões', 'Status', 'Ações'].map((h) => (
                <th
                  key={h}
                  className={`px-3 py-2 text-left text-[11px] font-medium text-gray-500 uppercase tracking-wider ${
                    h === 'Ações' ? 'text-right' : ''
                  }`}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {users.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-gray-500 text-sm">
                  {error ? '—' : 'Nenhum usuário encontrado'}
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50/80">
                  <td className="px-3 py-2 font-medium text-gray-900 whitespace-nowrap">
                    {user.first_name} {user.last_name}
                  </td>
                  <td className="px-3 py-2 text-gray-600 whitespace-nowrap">{user.cpf}</td>
                  <td className="px-3 py-2 text-gray-600 whitespace-nowrap">{user.email}</td>
                  <td className="px-3 py-2 whitespace-nowrap">{getRoleBadge(user.role)}</td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    {user.role === 'colaborador' ? (
                      <a
                        href={COLABORADORES_ROUTES.permissions(user.id)}
                        className="text-[var(--color-primary)] hover:underline text-xs"
                      >
                        {user.permission_count} permissões
                      </a>
                    ) : (
                      <span className="text-xs text-gray-500">Acesso total</span>
                    )}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        user.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {user.is_active ? 'Ativo' : 'Inativo'}
                    </span>
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap text-right text-xs">
                    <div className="flex items-center justify-end gap-2">
                      <a
                        href={COLABORADORES_ROUTES.edit(user.id)}
                        className="text-[var(--color-primary)] hover:underline"
                      >
                        Editar
                      </a>
                      {user.role === 'colaborador' && (
                        <a
                          href={COLABORADORES_ROUTES.permissions(user.id)}
                          className="text-purple-600 hover:underline"
                        >
                          Permissões
                        </a>
                      )}
                      <button
                        type="button"
                        onClick={() => handleDelete(user.id)}
                        className="text-red-600 hover:underline"
                      >
                        Excluir
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
