import { useState, useEffect } from 'react';
import { useStore } from '@nanostores/react';
import { api } from '../../../../lib/api/client';
import { setAuth } from '../../../../lib/stores/auth';
import { applyTheme } from '../../../../lib/stores/theme';
import { $whitelabel } from '../../../../lib/stores/whitelabel';
import { applyCpfOrCnpjMask, unmask } from '../../../../lib/utils/masks';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import type { TokenResponse, User, Company } from '../../../../lib/api/types';

export function LoginForm() {
  const config = useStore($whitelabel);
  const [document, setDocument] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);

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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const tokens = await api.post<TokenResponse>(ENDPOINTS.TOKEN, {
        cpf: unmask(document),
        password,
      });

      // Temporarily set tokens so api client can use them
      const { $tokens } = await import('../../../../lib/stores/auth');
      $tokens.set(tokens);
      localStorage.setItem('tokens', JSON.stringify(tokens));

      const user = await api.get<User>(ENDPOINTS.CURRENT_USER);

      setAuth(tokens, user);

      // Load company theming
      if (user.company) {
        try {
          const company = await api.get<Company>(ENDPOINTS.COMPANY_DETAIL(user.company));
          applyTheme({
            primaryColor: company.primary_color,
            secondaryColor: company.secondary_color,
            accentColor: company.accent_color,
            logoUrl: company.logo,
          });
        } catch {
          // Non-critical: continue with default theme
        }
      }

      window.location.href = `${window.location.origin}/dashboard`;
    } catch (err) {
      // Usar o utilitário para extrair mensagem específica
      const errorMessage = extractErrorMessage(err);
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
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
          <h1 className="text-2xl font-bold text-gray-900">{config.systemName}</h1>
          <p className="text-sm text-gray-500 mt-1">Sistema de Gestao de Comissoes</p>
        </div>

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
      </div>
      )}
    </div>
  );
}
