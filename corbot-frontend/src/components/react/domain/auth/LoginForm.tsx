import { useState, useEffect } from 'react';
import { useStore } from '@nanostores/react';
import { api, resolveMediaUrl } from '../../../../lib/api/client';
import { setAuth } from '../../../../lib/stores/auth';
import { applyTheme } from '../../../../lib/stores/theme';
import { $whitelabel } from '../../../../lib/stores/whitelabel';
import { applyCpfOrCnpjMask, unmask } from '../../../../lib/utils/masks';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import type {
  TokenResponse,
  User,
  Company,
  LoginProfile,
  LoginResponse,
} from '../../../../lib/api/types';
import { isProfileSelectionResponse } from '../../../../lib/api/types';

const PORTAL_APP_URL = (import.meta.env.PUBLIC_PORTAL_APP_URL as string | undefined) || '';

export function LoginForm() {
  const config = useStore($whitelabel);
  const [document, setDocument] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);
  const [profiles, setProfiles] = useState<LoginProfile[] | null>(null);

  useEffect(() => {
    api.get<{ initialized: boolean }>(ENDPOINTS.SETUP_STATUS)
      .then((data) => {
        if (!data.initialized) {
          window.location.href = `${window.location.origin}/setup`;
          return;
        }
        setChecking(false);
      })
      .catch(() => setChecking(false));
  }, []);

  async function finishLogin(tokens: TokenResponse) {
    const { $tokens } = await import('../../../../lib/stores/auth');
    $tokens.set(tokens);
    localStorage.setItem('tokens', JSON.stringify(tokens));

    const user = await api.get<User>(ENDPOINTS.CURRENT_USER);

    // Corban, gerente, líder e vendedor usam a rota específica do portal.
    if (PORTAL_APP_URL && user.role !== 'admin' && user.role !== 'colaborador' && user.role !== 'gerente_comercial') {
      $tokens.set(null);
      localStorage.removeItem('tokens');
      window.location.href = `${PORTAL_APP_URL.replace(/\/+$/, '')}/portal-login`;
      return;
    }

    setAuth(tokens, user);

    if (user.company) {
      try {
        const company = await api.get<Company>(ENDPOINTS.COMPANY_DETAIL(user.company));
        applyTheme({
          primaryColor: company.primary_color,
          secondaryColor: company.secondary_color,
          accentColor: company.accent_color,
          logoUrl: resolveMediaUrl(company.logo),
        });
      } catch {
        // Tema padrão se falhar
      }
    }

    window.location.href = `${window.location.origin}/dashboard`;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await api.post<LoginResponse>(ENDPOINTS.TOKEN, {
        cpf: unmask(document),
        password,
      });

      if (isProfileSelectionResponse(response)) {
        setProfiles(response.profiles);
        return;
      }

      await finishLogin(response);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectProfile(userId: number) {
    setError('');
    setLoading(true);

    try {
      const tokens = await api.post<TokenResponse>(ENDPOINTS.TOKEN_SELECT_PROFILE, {
        cpf: unmask(document),
        password,
        user_id: userId,
      });
      await finishLogin(tokens);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function handleBackToLogin() {
    setProfiles(null);
    setError('');
  }

  return (
    <div className="w-full max-w-md">
      {checking ? (
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-primary)]" />
        </div>
      ) : (
      <div className="bg-white rounded-xl shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="page-title">{config.systemName}</h1>
          <p className="page-subtitle">
            {profiles ? 'Escolha como deseja entrar' : 'Sistema de gestão de comissões'}
          </p>
        </div>

        {profiles ? (
          <div className="space-y-4">
            <p className="text-sm text-gray-600 text-center">
              Este CPF possui mais de um perfil. Cada acesso é independente — dados de vendedor e de corban não se misturam.
            </p>

            {profiles.map((profile) => (
              <button
                key={profile.user_id}
                type="button"
                disabled={loading}
                onClick={() => handleSelectProfile(profile.user_id)}
                className="w-full text-left p-4 border border-gray-200 rounded-lg hover:border-[var(--color-primary)] hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                <span className="block font-medium text-gray-900">{profile.label}</span>
                <span className="block text-xs text-gray-500 mt-1">
                  {profile.profile_type === 'promotora'
                    ? 'Acesso Promotora'
                    : profile.profile_type === 'corban'
                      ? 'Acesso Corban'
                      : 'Acesso Equipe / Vendedor'}
                </span>
              </button>
            ))}

            <button
              type="button"
              onClick={handleBackToLogin}
              className="w-full py-2 text-sm text-gray-500 hover:text-gray-700"
            >
              Voltar
            </button>
          </div>
        ) : (
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="document" className="block text-sm font-medium text-gray-700 mb-1">
              CPF/CNPJ
            </label>
            <input
              id="document"
              type="text"
              value={document}
              onChange={(e) => setDocument(applyCpfOrCnpjMask(e.target.value))}
              placeholder="000.000.000-00 ou 00.000.000/0000-00"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent outline-none transition-all text-sm"
              required
              autoFocus
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Senha
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent outline-none transition-all text-sm"
              required
            />
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 text-sm p-3 rounded-lg">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 bg-[var(--color-primary)] hover:bg-[var(--color-primary-dark)] text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
          >
            {loading ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
        )}

        {profiles && error && (
          <div className="bg-red-50 text-red-600 text-sm p-3 rounded-lg mt-4">
            {error}
          </div>
        )}
      </div>
      )}
    </div>
  );
}
