import { useState, useEffect, useCallback } from 'react';
import { useStore } from '@nanostores/react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { $currentUser } from '../../../../lib/stores/auth';
import { isPromotoraAdmin } from '../../../../lib/utils/roles';
import type { Role } from '../../../../lib/utils/roles';
import type { PaginatedResponse } from '../../../../lib/api/types';
import { PageHeader } from '../../ui/PageHeader';
import { Button } from '../../ui/Button';
import { Modal } from '../../ui/Modal';
import { Badge } from '../../ui/Badge';
import { DataTable, type Column } from '../../ui/DataTable';
import { InactivationButton } from '../../ui/InactivationButton';
import { PageSpinner } from '../../ui/Spinner';
import { KeyRound, Plus, Users } from 'lucide-react';
import toast from 'react-hot-toast';
import type { CommercialManager } from './types';
import { managerLabel } from './types';

function CreateManagerModal({
  isOpen,
  onClose,
  onCreated,
}: {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
    cpf: '',
    email: '',
    first_name: '',
    last_name: '',
    password: '',
  });
  const [saving, setSaving] = useState(false);

  async function handleSubmit() {
    setSaving(true);
    try {
      await api.post(ENDPOINTS.COMMERCIAL_MANAGERS, form);
      toast.success('Gerente comercial criado com sucesso!');
      setForm({ cpf: '', email: '', first_name: '', last_name: '', password: '' });
      onCreated();
      onClose();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Novo Gerente Comercial">
      <div className="space-y-3">
        <label className="space-y-1 block">
          <span className="text-sm text-gray-600">CPF</span>
          <input
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            value={form.cpf}
            onChange={(e) => setForm({ ...form, cpf: e.target.value })}
          />
        </label>
        <label className="space-y-1 block">
          <span className="text-sm text-gray-600">Nome</span>
          <input
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            value={form.first_name}
            onChange={(e) => setForm({ ...form, first_name: e.target.value })}
          />
        </label>
        <label className="space-y-1 block">
          <span className="text-sm text-gray-600">Sobrenome</span>
          <input
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            value={form.last_name}
            onChange={(e) => setForm({ ...form, last_name: e.target.value })}
          />
        </label>
        <label className="space-y-1 block">
          <span className="text-sm text-gray-600">Email</span>
          <input
            type="email"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </label>
        <label className="space-y-1 block">
          <span className="text-sm text-gray-600">Senha</span>
          <input
            type="password"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </label>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Cancelar
          </Button>
          <Button size="sm" onClick={handleSubmit} loading={saving}>
            Criar
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function PasswordModal({
  manager,
  onClose,
  onSaved,
}: {
  manager: CommercialManager | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [saving, setSaving] = useState(false);

  async function handleSubmit() {
    if (!manager) return;
    if (password.length < 6) {
      toast.error('A senha deve ter pelo menos 6 caracteres.');
      return;
    }
    if (password !== confirm) {
      toast.error('As senhas não coincidem.');
      return;
    }
    setSaving(true);
    try {
      await api.patch(ENDPOINTS.COMMERCIAL_MANAGER_DETAIL(manager.id), { password });
      toast.success('Senha atualizada.');
      setPassword('');
      setConfirm('');
      onSaved();
      onClose();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal isOpen={!!manager} onClose={onClose} title={manager ? `Trocar senha — ${managerLabel(manager)}` : 'Trocar senha'}>
      <div className="space-y-3">
        <label className="space-y-1 block">
          <span className="text-sm text-gray-600">Nova senha</span>
          <input
            type="password"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <label className="space-y-1 block">
          <span className="text-sm text-gray-600">Confirmar senha</span>
          <input
            type="password"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
        </label>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Cancelar
          </Button>
          <Button size="sm" onClick={handleSubmit} loading={saving}>
            Salvar senha
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export function CommercialManagersPage() {
  const user = useStore($currentUser);
  const canManage = isPromotoraAdmin((user?.role as Role) ?? null, user?.company ?? null);
  const [managers, setManagers] = useState<CommercialManager[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [passwordManager, setPasswordManager] = useState<CommercialManager | null>(null);

  const loadManagers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<PaginatedResponse<CommercialManager> | CommercialManager[]>(
        `${ENDPOINTS.COMMERCIAL_MANAGERS}?page_size=200`,
      );
      setManagers(Array.isArray(res) ? res : res.results);
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!canManage) {
      setLoading(false);
      return;
    }
    loadManagers();
  }, [canManage, loadManagers]);

  const columns: Column<CommercialManager>[] = [
    {
      key: 'first_name',
      header: 'Nome',
      sortable: true,
      render: (item) => <span className="font-medium text-gray-900">{managerLabel(item)}</span>,
    },
    { key: 'cpf', header: 'CPF' },
    {
      key: 'email',
      header: 'E-mail',
      render: (item) => item.email || '—',
    },
    {
      key: 'team_size',
      header: 'Equipe',
      render: (item) => `${item.team_size} corban(s)`,
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (item) => (
        <Badge variant={item.is_active ? 'success' : 'error'}>{item.is_active ? 'Ativo' : 'Inativo'}</Badge>
      ),
    },
  ];

  if (!canManage) {
    return (
      <div>
        <PageHeader title="Gerentes" subtitle="Acesso restrito ao admin da promotora" />
        <p className="text-sm text-gray-500">Você não tem permissão para gerenciar gerentes comerciais.</p>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Gerentes"
        subtitle="Cadastro de gerentes comerciais da promotora. Inativar um gerente deixa a equipe sem gerente."
        actions={
          <Button size="sm" onClick={() => setModalOpen(true)}>
            <Plus size={16} />
            Novo gerente comercial
          </Button>
        }
      />

      {loading ? (
        <PageSpinner />
      ) : (
        <DataTable
          columns={columns as unknown as Column<Record<string, unknown>>[]}
          data={managers as unknown as Record<string, unknown>[]}
          keyExtractor={(item) => String((item as unknown as CommercialManager).id)}
          emptyMessage="Nenhum gerente comercial cadastrado ainda."
          rowActions={(row) => {
            const item = row as unknown as CommercialManager;
            return (
            <div className="flex flex-wrap items-center justify-end gap-1">
              <a href={`/commercial/teams?manager=${item.id}`}>
                <Button size="sm" variant="secondary" disabled={!item.is_active}>
                  <Users size={14} />
                  Equipe
                </Button>
              </a>
              <Button size="sm" variant="secondary" onClick={() => setPasswordManager(item)}>
                <KeyRound size={14} />
                Senha
              </Button>
              <InactivationButton
                isActive={item.is_active}
                activationUrl={ENDPOINTS.COMMERCIAL_MANAGER_ACTIVATION(item.id)}
                inactivatedAt={item.inactivated_at}
                inactivationReason={item.inactivation_reason}
                onDone={loadManagers}
                warning="Ao inativar, toda a equipe deste gerente fica sem gerente."
              />
            </div>
            );
          }}
        />
      )}

      <CreateManagerModal isOpen={modalOpen} onClose={() => setModalOpen(false)} onCreated={loadManagers} />
      <PasswordModal
        manager={passwordManager}
        onClose={() => setPasswordManager(null)}
        onSaved={loadManagers}
      />
    </div>
  );
}
