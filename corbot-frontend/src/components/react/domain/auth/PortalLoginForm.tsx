import { useState } from 'react';
import { useStore } from '@nanostores/react';
import { Eye, EyeOff, LockKeyhole, ShieldCheck, UserRound } from 'lucide-react';
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

const ADMIN_APP_URL = (import.meta.env.PUBLIC_ADMIN_APP_URL as string | undefined) || 'http://localhost:3000';

export function PortalLoginForm() {
  const config = useStore($whitelabel);
  const [document, setDocument] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [profiles, setProfiles] = useState<LoginProfile[] | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  async function finishLogin(tokens: TokenResponse) {
    const { $tokens } = await import('../../../../lib/stores/auth');
    $tokens.set(tokens);
    localStorage.setItem('tokens', JSON.stringify(tokens));

    const user = await api.get<User>(ENDPOINTS.CURRENT_USER);

    if (user.role === 'admin' || user.role === 'colaborador' || user.role === 'gerente_comercial') {
      window.location.href = ADMIN_APP_URL;
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
    <div className="min-h-screen w-full bg-[#f2f2f2]">
      <div className="grid min-h-screen w-full lg:grid-cols-[1.5fr_1fr]">
        <div className="relative hidden min-h-[420px] overflow-hidden bg-slate-900 lg:block">
          <div
            className="absolute inset-0 bg-cover bg-center"
            style={{
              backgroundImage:
                "linear-gradient(0deg, rgba(10, 17, 29, 0.7), rgba(10, 17, 29, 0.45)), url('https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1400&q=80')",
            }}
          />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.12),_transparent_55%)]" />
          <div className="absolute left-6 top-6 z-10 rounded-full bg-orange-500 px-5 py-2 text-xs font-bold uppercase tracking-[0.2em] text-white shadow-lg">
            Área de Corretores
          </div>
        </div>

        <div className="flex items-center justify-center bg-[#f5f5f5] px-4 py-12 sm:px-6 lg:px-10">
          <div className="w-full max-w-[430px]">
            <div className="mb-8 rounded-xl bg-[#0d1b2d] p-6 text-center shadow-[0_10px_30px_rgba(13,27,45,0.18)]">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-md bg-[#f7f7f7] text-sm font-black text-[#0d1b2d]">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div className="text-2xl font-black tracking-[0.18em] text-white uppercase">
                {config.systemName || 'Auto Promotora'}
              </div>
              <div className="mt-2 text-[10px] font-medium tracking-[0.3em] text-slate-300 uppercase">
                Liberdade e Conhecimento
              </div>
            </div>

            <div className="mb-6 text-center text-[#2b2b2b]">
              <p className="text-[15px] font-medium">
                {profiles ? 'Escolha como deseja entrar' : 'Insira suas credenciais para acessar sua conta.'}
              </p>
            </div>

            {profiles ? (
              <div className="space-y-3 rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                <p className="text-center text-sm text-gray-600">
                  Este CPF possui mais de um perfil. Cada acesso é independente.
                </p>

                {profiles.map((profile) => (
                  <button
                    key={profile.user_id}
                    type="button"
                    disabled={loading}
                    onClick={() => handleSelectProfile(profile.user_id)}
                    className="w-full rounded-lg border border-gray-200 p-4 text-left transition-colors hover:border-[var(--color-primary)] hover:bg-gray-50 disabled:opacity-50"
                  >
                    <span className="block font-medium text-gray-900">{profile.label}</span>
                    <span className="mt-1 block text-xs text-gray-500">
                      {profile.profile_type === 'promotora'
                        ? 'Acesso Promotora'
                        : profile.profile_type === 'corban'
                          ? 'Acesso Corban'
                          : 'Acesso Equipe / Vendedor'}
                    </span>
                  </button>
                ))}

                {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

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
                  <label htmlFor="document" className="mb-2 block text-sm font-medium text-slate-700">
                    Usuário
                  </label>
                  <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-100 px-3 py-2.5 shadow-inner">
                    <UserRound className="h-5 w-5 text-slate-500" />
                    <input
                      id="document"
                      type="text"
                      value={document}
                      onChange={(e) => setDocument(applyCpfOrCnpjMask(e.target.value))}
                      placeholder="000.000.000-00"
                      className="w-full border-0 bg-transparent text-sm text-slate-700 outline-none placeholder:text-slate-500"
                      required
                      autoFocus
                    />
                  </div>
                </div>

                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label htmlFor="password" className="text-sm font-medium text-slate-700">
                      Senha
                    </label>
                    <button
                      type="button"
                      onClick={() => setShowPassword((prev) => !prev)}
                      className="text-xs text-slate-500 hover:text-slate-700"
                    >
                      {showPassword ? 'Ocultar' : 'Esquecer a senha?'}
                    </button>
                  </div>
                  <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-100 px-3 py-2.5 shadow-inner">
                    <LockKeyhole className="h-5 w-5 text-slate-500" />
                    <input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full border-0 bg-transparent text-sm text-slate-700 outline-none placeholder:text-slate-500"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((prev) => !prev)}
                      className="flex h-7 w-7 items-center justify-center rounded-md text-slate-500 transition hover:bg-white hover:text-slate-700"
                      aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-lg bg-orange-500 px-4 py-3 text-base font-semibold text-white shadow-[0_12px_20px_rgba(245,158,11,0.35)] transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? 'Entrando...' : 'Acessar'}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
