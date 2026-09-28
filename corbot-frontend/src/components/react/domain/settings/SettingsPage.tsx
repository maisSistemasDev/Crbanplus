import { useEffect, useMemo, useState } from 'react';
import { useStore } from '@nanostores/react';
import { PageShell } from '../../layout/PageShell';
import { PageHeader } from '../../ui/PageHeader';
import { Button } from '../../ui/Button';
import { SearchSelect } from '../../ui/SearchSelect';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { $currentUser, updateCurrentUser } from '../../../../lib/stores/auth';
import type { User } from '../../../../lib/api/types';
import { extractErrorMessage } from '../../../../lib/api/errors';
import toast from 'react-hot-toast';

interface CorbanPayConfigResponse {
  corbanpay_base_url: string;
  corbanpay_api_key: string;
  corbanpay_api_key_configured: boolean;
}

interface AIConfigResponse {
  ai_provider: 'openai' | 'anthropic';
  ai_model: string;
  ai_api_key: string;
  ai_api_key_configured: boolean;
}

interface ProfileForm {
  first_name: string;
  last_name: string;
  email: string;
  certificado: string;
  phone: string;
  pix_key: string;
  pix_type: 'CHAVE_ALEATORIA' | 'EMAIL' | 'CELULAR' | 'CPF' | 'CNPJ' | '';
  rg: string;
  rg_emission_organ: string;
  rg_emission_date: string;
  birth_date: string;
  current_password: string;
  new_password: string;
  confirm_password: string;
}

const PIX_TYPE_OPTIONS = [
  { value: '', label: 'Nao informado' },
  { value: 'CHAVE_ALEATORIA', label: 'Chave Aleatoria' },
  { value: 'EMAIL', label: 'Email' },
  { value: 'CELULAR', label: 'Celular' },
  { value: 'CPF', label: 'CPF' },
  { value: 'CNPJ', label: 'CNPJ' },
] as const;

const AI_PROVIDER_OPTIONS = [
  { value: 'openai', label: 'OpenAI (ChatGPT)' },
  { value: 'anthropic', label: 'Anthropic (Claude)' },
];

function buildProfileForm(user: User): ProfileForm {
  return {
    first_name: user.first_name || '',
    last_name: user.last_name || '',
    email: user.email || '',
    certificado: user.certificado || '',
    phone: user.extra_data?.phone || '',
    pix_key: user.extra_data?.pix_key || '',
    pix_type: user.extra_data?.pix_type || '',
    rg: user.extra_data?.rg || '',
    rg_emission_organ: user.extra_data?.rg_emission_organ || '',
    rg_emission_date: user.extra_data?.rg_emission_date || '',
    birth_date: user.extra_data?.birth_date || '',
    current_password: '',
    new_password: '',
    confirm_password: '',
  };
}

export function SettingsPage() {
  const user = useStore($currentUser);
  const [profileForm, setProfileForm] = useState<ProfileForm | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [integrationLoading, setIntegrationLoading] = useState(false);
  const [integrationSaving, setIntegrationSaving] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [corbanPayBaseUrl, setCorbanPayBaseUrl] = useState('');
  const [corbanPayApiKey, setCorbanPayApiKey] = useState('');
  const [corbanPayKeyConfigured, setCorbanPayKeyConfigured] = useState(false);
  const [aiProvider, setAiProvider] = useState<'openai' | 'anthropic'>('openai');
  const [aiModel, setAiModel] = useState('');
  const [aiApiKey, setAiApiKey] = useState('');
  const [aiKeyConfigured, setAiKeyConfigured] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiSaving, setAiSaving] = useState(false);

  const isPromotoraAdmin = useMemo(() => {
    return user?.role === 'admin' && !user?.company;
  }, [user]);

  useEffect(() => {
    if (!user) return;
    setProfileForm(buildProfileForm(user));
  }, [user]);

  useEffect(() => {
    if (!isPromotoraAdmin) return;

    setIntegrationLoading(true);
    api.get<CorbanPayConfigResponse>(ENDPOINTS.CORBANPAY_CONFIG)
      .then((data) => {
        setCorbanPayBaseUrl(data.corbanpay_base_url || '');
        setCorbanPayApiKey('');
        setCorbanPayKeyConfigured(!!data.corbanpay_api_key_configured);
      })
      .catch((error) => {
        toast.error(extractErrorMessage(error));
      })
      .finally(() => setIntegrationLoading(false));

    setAiLoading(true);
    api.get<AIConfigResponse>(ENDPOINTS.AI_SETTINGS)
      .then((data) => {
        setAiProvider(data.ai_provider || 'openai');
        setAiModel(data.ai_model || '');
        setAiApiKey('');
        setAiKeyConfigured(!!data.ai_api_key_configured);
      })
      .catch(() => { /* silencia se não disponível */ })
      .finally(() => setAiLoading(false));
  }, [isPromotoraAdmin]);

  if (!profileForm || !user) {
    return (
      <PageShell>
        <div className="flex justify-center py-16">
          <div className="animate-spin h-8 w-8 border-4 border-[var(--color-primary)] border-t-transparent rounded-full" />
        </div>
      </PageShell>
    );
  }

  function updateProfileField<K extends keyof ProfileForm>(field: K, value: ProfileForm[K]) {
    setProfileForm((prev) => (prev ? { ...prev, [field]: value } : prev));
  }

  async function refreshCurrentUser() {
    setProfileLoading(true);
    try {
      const refreshed = await api.get<User>(ENDPOINTS.CURRENT_USER);
      updateCurrentUser(refreshed);
      setProfileForm(buildProfileForm(refreshed));
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setProfileLoading(false);
    }
  }

  async function saveProfile() {
    if (!profileForm) return;

    const wantsPasswordChange = Boolean(profileForm.current_password || profileForm.new_password || profileForm.confirm_password);
    if (wantsPasswordChange && profileForm.new_password !== profileForm.confirm_password) {
      toast.error('A confirmacao da nova senha nao confere.');
      return;
    }

    const payload: Record<string, unknown> = {
      first_name: profileForm.first_name,
      last_name: profileForm.last_name,
      email: profileForm.email,
      certificado: profileForm.certificado || null,
      extra_data: {
        phone: profileForm.phone || null,
        pix_key: profileForm.pix_key || null,
        pix_type: profileForm.pix_type || null,
        rg: profileForm.rg || null,
        rg_emission_organ: profileForm.rg_emission_organ || null,
        rg_emission_date: profileForm.rg_emission_date || null,
        birth_date: profileForm.birth_date || null,
      },
    };

    if (wantsPasswordChange) {
      payload.current_password = profileForm.current_password;
      payload.new_password = profileForm.new_password;
    }

    setProfileSaving(true);
    try {
      const updated = await api.patch<User>(ENDPOINTS.PROFILE_SETTINGS, payload);
      updateCurrentUser(updated);
      setProfileForm(buildProfileForm(updated));
      toast.success('Perfil atualizado com sucesso.');
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setProfileSaving(false);
    }
  }

  async function saveAiConfig() {
    setAiSaving(true);
    try {
      const payload: Record<string, string> = { ai_provider: aiProvider, ai_model: aiModel };
      if (aiApiKey.trim()) payload.ai_api_key = aiApiKey.trim();
      const updated = await api.patch<AIConfigResponse>(ENDPOINTS.AI_SETTINGS, payload);
      setAiProvider(updated.ai_provider);
      setAiModel(updated.ai_model || '');
      setAiApiKey('');
      setAiKeyConfigured(!!updated.ai_api_key_configured);
      toast.success('Configuração do agente IA salva.');
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setAiSaving(false);
    }
  }

  async function saveCorbanPayConfig() {
    setIntegrationSaving(true);
    try {
      const payload: Record<string, string> = {
        corbanpay_base_url: corbanPayBaseUrl,
      };

      if (corbanPayApiKey.trim()) {
        payload.corbanpay_api_key = corbanPayApiKey.trim();
      }

      const updated = await api.patch<CorbanPayConfigResponse>(ENDPOINTS.CORBANPAY_CONFIG, payload);
      setCorbanPayBaseUrl(updated.corbanpay_base_url || '');
      setCorbanPayApiKey('');
      setCorbanPayKeyConfigured(!!updated.corbanpay_api_key_configured);
      toast.success('Configuracao CorbanPay atualizada com sucesso.');
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setIntegrationSaving(false);
    }
  }

  return (
    <PageShell>
      <div className="max-w-4xl mx-auto space-y-6">
        <PageHeader
          title="Configurações"
          actions={
            <Button variant="ghost" size="sm" onClick={refreshCurrentUser} loading={profileLoading}>
              Atualizar dados
            </Button>
          }
        />

        <div className="bg-white border border-gray-100 rounded-xl p-6 space-y-5">
          <h2 className="section-title">Perfil</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="space-y-1">
              <span className="text-sm text-gray-600">Nome</span>
              <input className="w-full rounded-lg border border-gray-300 px-3 py-2" value={profileForm.first_name} onChange={(e) => updateProfileField('first_name', e.target.value)} />
            </label>
            <label className="space-y-1">
              <span className="text-sm text-gray-600">Sobrenome</span>
              <input className="w-full rounded-lg border border-gray-300 px-3 py-2" value={profileForm.last_name} onChange={(e) => updateProfileField('last_name', e.target.value)} />
            </label>
            <label className="space-y-1">
              <span className="text-sm text-gray-600">Email</span>
              <input type="email" className="w-full rounded-lg border border-gray-300 px-3 py-2" value={profileForm.email} onChange={(e) => updateProfileField('email', e.target.value)} />
            </label>
            <label className="space-y-1">
              <span className="text-sm text-gray-600">Certificado</span>
              <input className="w-full rounded-lg border border-gray-300 px-3 py-2" value={profileForm.certificado} onChange={(e) => updateProfileField('certificado', e.target.value)} />
            </label>
            <label className="space-y-1">
              <span className="text-sm text-gray-600">CPF</span>
              <input className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-500" value={user.cpf} disabled />
            </label>
            <label className="space-y-1">
              <span className="text-sm text-gray-600">Matricula</span>
              <input className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-500" value={user.matricula || ''} disabled />
            </label>
          </div>

          <hr className="border-gray-100" />

          <h3 className="text-md font-semibold text-gray-900">Contato e PIX</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="space-y-1">
              <span className="text-sm text-gray-600">Telefone</span>
              <input className="w-full rounded-lg border border-gray-300 px-3 py-2" value={profileForm.phone} onChange={(e) => updateProfileField('phone', e.target.value)} />
            </label>
            <label className="space-y-1">
              <span className="text-sm text-gray-600">Tipo de PIX</span>
              <SearchSelect
                value={profileForm.pix_type}
                options={PIX_TYPE_OPTIONS}
                onChange={(e) => updateProfileField('pix_type', e.target.value as ProfileForm['pix_type'])}
              />
            </label>
            <label className="space-y-1 md:col-span-2">
              <span className="text-sm text-gray-600">Chave PIX</span>
              <input className="w-full rounded-lg border border-gray-300 px-3 py-2" value={profileForm.pix_key} onChange={(e) => updateProfileField('pix_key', e.target.value)} />
            </label>
          </div>

          <hr className="border-gray-100" />

          <h3 className="text-md font-semibold text-gray-900">Dados complementares</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="space-y-1">
              <span className="text-sm text-gray-600">RG</span>
              <input className="w-full rounded-lg border border-gray-300 px-3 py-2" value={profileForm.rg} onChange={(e) => updateProfileField('rg', e.target.value)} />
            </label>
            <label className="space-y-1">
              <span className="text-sm text-gray-600">Orgao Emissor do RG</span>
              <input className="w-full rounded-lg border border-gray-300 px-3 py-2" value={profileForm.rg_emission_organ} onChange={(e) => updateProfileField('rg_emission_organ', e.target.value)} />
            </label>
            <label className="space-y-1">
              <span className="text-sm text-gray-600">Data de emissao do RG</span>
              <input type="date" className="w-full rounded-lg border border-gray-300 px-3 py-2" value={profileForm.rg_emission_date || ''} onChange={(e) => updateProfileField('rg_emission_date', e.target.value)} />
            </label>
            <label className="space-y-1">
              <span className="text-sm text-gray-600">Data de nascimento</span>
              <input type="date" className="w-full rounded-lg border border-gray-300 px-3 py-2" value={profileForm.birth_date || ''} onChange={(e) => updateProfileField('birth_date', e.target.value)} />
            </label>
          </div>

          <hr className="border-gray-100" />

          <h3 className="text-md font-semibold text-gray-900">Alterar senha</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <label className="space-y-1">
              <span className="text-sm text-gray-600">Senha atual</span>
              <input type="password" className="w-full rounded-lg border border-gray-300 px-3 py-2" value={profileForm.current_password} onChange={(e) => updateProfileField('current_password', e.target.value)} />
            </label>
            <label className="space-y-1">
              <span className="text-sm text-gray-600">Nova senha</span>
              <input type="password" className="w-full rounded-lg border border-gray-300 px-3 py-2" value={profileForm.new_password} onChange={(e) => updateProfileField('new_password', e.target.value)} />
            </label>
            <label className="space-y-1">
              <span className="text-sm text-gray-600">Confirmar nova senha</span>
              <input type="password" className="w-full rounded-lg border border-gray-300 px-3 py-2" value={profileForm.confirm_password} onChange={(e) => updateProfileField('confirm_password', e.target.value)} />
            </label>
          </div>

          <div className="pt-2">
            <Button onClick={saveProfile} loading={profileSaving}>Salvar perfil</Button>
          </div>
        </div>

        {isPromotoraAdmin && (
          <div className="bg-white border border-gray-100 rounded-xl p-6 space-y-4">
            <h2 className="section-title">Integração CorbanPay</h2>

            <label className="space-y-1 block">
              <span className="text-sm text-gray-600">URL base</span>
              <input
                className="w-full rounded-lg border border-gray-300 px-3 py-2"
                placeholder="https://seudominio.com/api/v1/prepayment"
                value={corbanPayBaseUrl}
                onChange={(e) => setCorbanPayBaseUrl(e.target.value)}
                disabled={integrationLoading}
              />
            </label>

            <label className="space-y-1 block">
              <span className="text-sm text-gray-600">API Key</span>
              <input
                type="password"
                className="w-full rounded-lg border border-gray-300 px-3 py-2"
                placeholder={corbanPayKeyConfigured ? 'API key configurada. Digite apenas para substituir.' : 'Digite a API key'}
                value={corbanPayApiKey}
                onChange={(e) => setCorbanPayApiKey(e.target.value)}
                disabled={integrationLoading}
              />
            </label>

            <p className="text-xs text-gray-500">
              A API key nao e exibida por seguranca. Preencha apenas quando quiser atualizar o valor atual.
            </p>

            <Button onClick={saveCorbanPayConfig} loading={integrationSaving || integrationLoading}>
              Salvar configuracao CorbanPay
            </Button>
          </div>
        )}

        {isPromotoraAdmin && (
          <div className="bg-white border border-gray-100 rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-indigo-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
              </div>
              <div>
                <h2 className="section-title">Agente IA</h2>
                <p className="text-xs text-gray-500">Chave configurada aqui é usada por todos os usuários da promotora.</p>
              </div>
            </div>

            <label className="space-y-1 block">
              <span className="text-sm text-gray-600">Provedor</span>
              <SearchSelect
                value={aiProvider}
                options={AI_PROVIDER_OPTIONS}
                onChange={(e) => setAiProvider(e.target.value as 'openai' | 'anthropic')}
                disabled={aiLoading}
              />
            </label>

            <label className="space-y-1 block">
              <span className="text-sm text-gray-600">Modelo</span>
              <input
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                placeholder={aiProvider === 'openai' ? 'gpt-4o-mini (padrão)' : 'claude-3-haiku-20240307 (padrão)'}
                value={aiModel}
                onChange={(e) => setAiModel(e.target.value)}
                disabled={aiLoading}
              />
              <span className="text-xs text-gray-400">Deixe em branco para usar o modelo padrão do provedor.</span>
            </label>

            <label className="space-y-1 block">
              <span className="text-sm text-gray-600">API Key</span>
              <input
                type="password"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                placeholder={aiKeyConfigured ? 'Chave configurada. Digite apenas para substituir.' : 'sk-... ou anthropic key'}
                value={aiApiKey}
                onChange={(e) => setAiApiKey(e.target.value)}
                disabled={aiLoading}
                autoComplete="new-password"
              />
            </label>

            {aiKeyConfigured && (
              <div className="flex items-center gap-1.5 text-xs text-green-600">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                Chave configurada
              </div>
            )}

            <p className="text-xs text-gray-400">
              Sem chave configurada, o agente usa respostas por palavras-chave (modo offline).
            </p>

            <Button onClick={saveAiConfig} loading={aiSaving || aiLoading}>
              Salvar configuração IA
            </Button>
          </div>
        )}
      </div>
    </PageShell>
  );
}
