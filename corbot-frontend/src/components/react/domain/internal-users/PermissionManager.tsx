import { useState, useEffect } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import toast from 'react-hot-toast';
import { Button } from '../../ui/Button';
import { PageHeader } from '../../ui/PageHeader';
import { COLABORADORES_ROUTES } from '../../../../lib/routes/colaboradores';
import type { 
  InternalUser, 
  UserPermission, 
  PermissionGroup,
  AvailablePermission 
} from '../../../../lib/api/types/internal-users';

interface PermissionManagerProps {
  userId: string | undefined;
}

export default function PermissionManager({ userId }: PermissionManagerProps) {
  const [user, setUser] = useState<InternalUser | null>(null);
  const [availablePermissions, setAvailablePermissions] = useState<PermissionGroup[]>([]);
  const [selectedPermissions, setSelectedPermissions] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [userId]);

  const loadData = async () => {
    if (!userId) return;

    setLoading(true);
    setError(null);

    try {
      // Carregar dados do usuário
      const userResponse = await api.get<InternalUser>(
        ENDPOINTS.INTERNAL_USER_DETAIL(parseInt(userId))
      );
      setUser(userResponse);

      // Carregar permissões do usuário
      const permissionsResponse = await api.get<UserPermission[]>(
        ENDPOINTS.INTERNAL_USER_PERMISSIONS(parseInt(userId))
      );
      const currentPermissions = new Set(permissionsResponse.map(p => p.codename));
      setSelectedPermissions(currentPermissions);

      // Carregar permissões disponíveis
      const availableResponse = await api.get<PermissionGroup[]>(
        ENDPOINTS.AVAILABLE_PERMISSIONS
      );
      setAvailablePermissions(availableResponse);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleTogglePermission = (codename: string) => {
    setSelectedPermissions(prev => {
      const newSet = new Set(prev);
      if (newSet.has(codename)) {
        newSet.delete(codename);
      } else {
        newSet.add(codename);
      }
      return newSet;
    });
  };

  const handleSelectAll = (category: string) => {
    const group = availablePermissions.find(g => g.category === category);
    if (!group) return;

    const allSelected = group.permissions.every(p => selectedPermissions.has(p.codename));
    
    setSelectedPermissions(prev => {
      const newSet = new Set(prev);
      group.permissions.forEach(p => {
        if (allSelected) {
          newSet.delete(p.codename);
        } else {
          newSet.add(p.codename);
        }
      });
      return newSet;
    });
  };

  const handleSave = async () => {
    if (!userId) return;

    setSaving(true);
    setError(null);

    try {
      // Converter Set para array de objetos de permissão
      const permissionsToSave = Array.from(selectedPermissions).map(codename => {
        // Encontrar os detalhes da permissão
        for (const group of availablePermissions) {
          const perm = group.permissions.find(p => p.codename === codename);
          if (perm) {
            return {
              codename: perm.codename,
              name: perm.name,
              category: perm.category,
            };
          }
        }
        return null;
      }).filter(Boolean);

      const response = await api.post<{ message: string; user: InternalUser }>(
        ENDPOINTS.INTERNAL_USER_PERMISSIONS(parseInt(userId)),
        { permissions: permissionsToSave }
      );

      toast.success(response.message || 'Permissões atualizadas com sucesso.');
      window.location.href = COLABORADORES_ROUTES.list;
    } catch (err) {
      const msg = extractErrorMessage(err);
      setError(msg);
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="animate-spin h-6 w-6 border-2 border-[var(--color-primary)] border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!userId) {
    return <p className="text-sm text-red-600">ID do usuário não fornecido.</p>;
  }

  if (!user) {
    return <p className="text-sm text-red-600">Usuário não encontrado.</p>;
  }

  return (
    <div>
      <PageHeader
        title="Gerenciar permissões"
        subtitle={`${user.first_name} ${user.last_name}`}
      />

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="space-y-6">
          {availablePermissions.map((group) => {
            const allSelected = group.permissions.every(p => selectedPermissions.has(p.codename));
            const someSelected = group.permissions.some(p => selectedPermissions.has(p.codename));

            return (
              <div key={group.category} className="border-b pb-6 last:border-b-0">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">{group.label}</h3>
                  <button
                    onClick={() => handleSelectAll(group.category)}
                    className="text-sm text-blue-600 hover:text-blue-800"
                  >
                    {allSelected ? 'Desmarcar todas' : 'Selecionar todas'}
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {group.permissions.map((permission) => (
                    <label
                      key={permission.codename}
                      className="flex items-center p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedPermissions.has(permission.codename)}
                        onChange={() => handleTogglePermission(permission.codename)}
                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                      <span className="ml-3 text-sm text-gray-700">{permission.name}</span>
                    </label>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-6 flex items-center justify-between pt-6 border-t">
          <div className="text-sm text-gray-600">
            {selectedPermissions.size} permissão(ões) selecionada(s)
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => { window.location.href = COLABORADORES_ROUTES.list; }} disabled={saving}>
              Cancelar
            </Button>
            <Button size="sm" onClick={handleSave} loading={saving}>
              Salvar permissões
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
