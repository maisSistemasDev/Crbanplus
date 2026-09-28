import { useEffect, useState } from 'react';
import { useStore } from '@nanostores/react';
import { Plus, Users } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { formatDate } from '../../../../lib/utils/format';
import { $currentUser } from '../../../../lib/stores/auth';
import type { CommissionGroup } from '../../../../lib/api/types';
import { PageHeader } from '../../ui/PageHeader';
import { Button } from '../../ui/Button';
import { Badge } from '../../ui/Badge';
import { EmptyState } from '../../ui/EmptyState';
import { SectionSpinner } from '../../ui/Spinner';

const CAN_MANAGE_ROLES = ['admin', 'empresa_admin', 'gerente', 'lider'];

export function GroupList() {
  const user = useStore($currentUser);
  const [groups, setGroups] = useState<CommissionGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const canManage = !!user && CAN_MANAGE_ROLES.includes(user.role);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function load() {
    setLoading(true);
    api
      .get<CommissionGroup[]>(ENDPOINTS.COMMISSION_GROUPS)
      .then(setGroups)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await api.post(ENDPOINTS.COMMISSION_GROUPS, { name, description });
      toast.success('Equipe criada com sucesso!');
      setShowForm(false);
      setName('');
      setDescription('');
      load();
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Equipes"
        subtitle="Grupos de comissionamento e seus membros."
        actions={
          canManage ? (
            <Button size="sm" onClick={() => setShowForm((v) => !v)}>
              <Plus className="h-4 w-4" />
              Nova equipe
            </Button>
          ) : undefined
        }
      />

      {showForm && (
        <form onSubmit={handleCreate} className="card mb-4 flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[200px]">
            <label className="mb-1 block text-xs font-medium text-[var(--color-text-muted)]">Nome</label>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-primary)]"
              placeholder="Ex: Equipe São Paulo"
            />
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="mb-1 block text-xs font-medium text-[var(--color-text-muted)]">Descrição</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-sm outline-none focus:border-[var(--color-primary)]"
              placeholder="Opcional"
            />
          </div>
          <Button type="submit" size="sm" loading={creating}>
            Criar
          </Button>
          <Button type="button" variant="secondary" size="sm" onClick={() => setShowForm(false)}>
            Cancelar
          </Button>
        </form>
      )}

      <div className="card">
        {loading ? (
          <SectionSpinner />
        ) : error ? (
          <p className="text-sm text-red-600">{error}</p>
        ) : groups.length === 0 ? (
          <EmptyState icon={Users} title="Nenhuma equipe encontrada" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase text-[var(--color-text-muted)]">
                  <th className="py-2 pr-3">Nome</th>
                  <th className="py-2 pr-3">Empresa</th>
                  <th className="py-2 pr-3">Membros</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Criado em</th>
                </tr>
              </thead>
              <tbody>
                {groups.map((group) => (
                  <tr
                    key={group.id}
                    className="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
                    onClick={() => (window.location.href = `/commission-groups/${group.id}`)}
                  >
                    <td className="py-2 pr-3">
                      <div className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: group.color }} />
                        <span className="font-medium text-[var(--color-text)]">{group.name}</span>
                      </div>
                    </td>
                    <td className="py-2 pr-3 text-[var(--color-text-muted)]">
                      {group.company_name ?? 'Promotora'}
                    </td>
                    <td className="py-2 pr-3 text-[var(--color-text-muted)]">
                      <span className="inline-flex items-center gap-1">
                        <Users className="h-3.5 w-3.5" />
                        {(group.sellers?.length ?? 0) + (group.leaders?.length ?? 0)}
                      </span>
                    </td>
                    <td className="py-2 pr-3">
                      <Badge tone={group.is_active ? 'success' : 'gray'}>{group.is_active ? 'Ativo' : 'Inativo'}</Badge>
                    </td>
                    <td className="py-2 pr-3 text-[var(--color-text-muted)]">{formatDate(group.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
