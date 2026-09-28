import { useEffect, useState } from 'react';
import { useStore } from '@nanostores/react';
import toast from 'react-hot-toast';
import { RefreshCw } from 'lucide-react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { $currentUser, updateCurrentUser } from '../../../../lib/stores/auth';
import { ROLE_LABELS, type Role } from '../../../../lib/utils/roles';
import type { User } from '../../../../lib/api/types';
import { PageHeader } from '../../ui/PageHeader';
import { Button } from '../../ui/Button';
import { SearchSelect } from '../../ui/SearchSelect';

interface ProfileForm {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  pix_key: string;
  pix_type: 'CHAVE_ALEATORIA' | 'EMAIL' | 'CELULAR' | 'CPF' | 'CNPJ' | '';
  current_password: string;
  new_password: string;
  confirm_password: string;
}

const PIX_TYPE_OPTIONS = [
  { value: '', label: 'Não informado' },
  { value: 'CHAVE_ALEATORIA', label: 'Chave Aleatória' },
  { value: 'EMAIL', label: 'E-mail' },
  { value: 'CELULAR', label: 'Celular' },
  { value: 'CPF', label: 'CPF' },
  { value: 'CNPJ', label: 'CNPJ' },
] as const;

function buildProfileForm(user: User): ProfileForm {
  return {
    first_name: user.first_name || '',
    last_name: user.last_name || '',
    email: user.email || '',
    phone: user.extra_data?.phone || '',
    pix_key: user.extra_data?.pix_key || '',
    pix_type: user.extra_data?.pix_type || '',
    current_password: '',
    new_password: '',
    confirm_password: '',
  };
}

export function SettingsPage() {
  const user = useStore($currentUser);
  const [form, setForm] = useState<ProfileForm | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user) setForm(buildProfileForm(user));
  }, [user]);

  if (!form || !user) return null;

  function updateField<K extends keyof ProfileForm>(field: K, value: ProfileForm[K]) {
    setForm((prev) => (prev ? { ...prev, [field]: value } : prev));
  }

  async function refreshUser() {
    setLoading(true);
    try {
      const refreshed = await api.get<User>(ENDPOINTS.CURRENT_USER);
      updateCurrentUser(refreshed);
      setForm(buildProfileForm(refreshed));
      toast.success('Dados atualizados.');
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;

    const wantsPasswordChange = Boolean(form.current_password || form.new_password || form.confirm_password);
    if (wantsPasswordChange && form.new_password !== form.confirm_password) {
      toast.error('A confirmação da nova senha não confere.');
      return;
    }

    const payload: Record<string, unknown> = {
      first_name: form.first_name,
      last_name: form.last_name,
      email: form.email,
      extra_data: {
        phone: form.phone || null,
        pix_key: form.pix_key || null,
        pix_type: form.pix_type || null,
      },
    };

    if (wantsPasswordChange) {
      payload.current_password = form.current_password;
      payload.new_password = form.new_password;
    }

    setSaving(true);
    try {
      const updated = await api.patch<User>(ENDPOINTS.PROFILE_SETTINGS, payload);
      updateCurrentUser(updated);
      setForm(buildProfileForm(updated));
      toast.success('Perfil atualizado com sucesso!');
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="Configurações"
        subtitle="Dados do seu perfil e alteração de senha"
        actions={
          <Button variant="ghost" size="sm" icon={<RefreshCw size={14} />} loading={loading} onClick={refreshUser}>
            Atualizar dados
          </Button>
        }
      />

      <form onSubmit={handleSave} className="space-y-5">
        <div className="card">
          <h2 className="section-title mb-4">Perfil</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="text-sm">
              <span className="mb-1 block text-xs font-medium text-gray-600">Nome</span>
              <input
                value={form.first_name}
                onChange={(e) => updateField('first_name', e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-xs font-medium text-gray-600">Sobrenome</span>
              <input
                value={form.last_name}
                onChange={(e) => updateField('last_name', e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-xs font-medium text-gray-600">E-mail</span>
              <input
                type="email"
                value={form.email}
                onChange={(e) => updateField('email', e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-xs font-medium text-gray-600">CPF</span>
              <input
                value={user.cpf}
                disabled
                className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-500"
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-xs font-medium text-gray-600">Perfil</span>
              <input
                value={ROLE_LABELS[user.role as Role] ?? user.role}
                disabled
                className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-500"
              />
            </label>
          </div>
        </div>

        <div className="card">
          <h2 className="section-title mb-4">Contato e PIX</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="text-sm">
              <span className="mb-1 block text-xs font-medium text-gray-600">Telefone</span>
              <input
                value={form.phone}
                onChange={(e) => updateField('phone', e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-xs font-medium text-gray-600">Tipo de chave PIX</span>
              <SearchSelect
                value={form.pix_type}
                options={PIX_TYPE_OPTIONS}
                onChange={(value) => updateField('pix_type', value as ProfileForm['pix_type'])}
              />
            </label>
            <label className="text-sm md:col-span-2">
              <span className="mb-1 block text-xs font-medium text-gray-600">Chave PIX</span>
              <input
                value={form.pix_key}
                onChange={(e) => updateField('pix_key', e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
              />
            </label>
          </div>
        </div>

        <div className="card">
          <h2 className="section-title mb-4">Alterar senha</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <label className="text-sm">
              <span className="mb-1 block text-xs font-medium text-gray-600">Senha atual</span>
              <input
                type="password"
                value={form.current_password}
                onChange={(e) => updateField('current_password', e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-xs font-medium text-gray-600">Nova senha</span>
              <input
                type="password"
                value={form.new_password}
                onChange={(e) => updateField('new_password', e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-xs font-medium text-gray-600">Confirmar nova senha</span>
              <input
                type="password"
                value={form.confirm_password}
                onChange={(e) => updateField('confirm_password', e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
              />
            </label>
          </div>
        </div>

        <div className="flex justify-end">
          <Button type="submit" loading={saving}>
            Salvar alterações
          </Button>
        </div>
      </form>
    </div>
  );
}
