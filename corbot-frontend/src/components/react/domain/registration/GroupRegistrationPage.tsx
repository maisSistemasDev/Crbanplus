import { useEffect, useState } from 'react';
import { useStore } from '@nanostores/react';
import { API_URL } from '../../../../lib/api/client';
import { $whitelabel } from '../../../../lib/stores/whitelabel';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { applyCpfMask } from '../../../../lib/utils/masks';

interface RegistrationInfo {
  group_id: number;
  group_name: string;
  group_color: string;
  company_id: string;
  company_name: string;
  allowed_role: string;
  expires_at: string | null;
  uses_remaining: number | null;
}

interface Props {
  token: string;
}

async function publicRequest<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(
      (data as { detail?: string | string[] }).detail
        ? Array.isArray((data as { detail: string[] }).detail)
          ? (data as { detail: string[] }).detail.join(', ')
          : String((data as { detail: string }).detail)
        : `Erro ${response.status}`,
    );
  }
  return data as T;
}

export function GroupRegistrationPage({ token }: Props) {
  const config = useStore($whitelabel);
  const [info, setInfo] = useState<RegistrationInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [cpf, setCpf] = useState('');
  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [password, setPassword] = useState('');
  const [phone, setPhone] = useState('');

  useEffect(() => {
    publicRequest<RegistrationInfo>('GET', `/public/registration/${encodeURIComponent(token)}/`)
      .then(setInfo)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [token]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    if (password.length < 6) {
      setError('A senha deve ter pelo menos 6 caracteres.');
      return;
    }

    setSubmitting(true);
    try {
      await publicRequest('POST', `/public/registration/${encodeURIComponent(token)}/`, {
        cpf: cpf.replace(/\D/g, ''),
        email,
        first_name: firstName,
        last_name: lastName,
        password,
        extra_data: phone ? { phone: phone.replace(/\D/g, '') } : undefined,
      });
      setSuccess(true);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-lg text-center text-gray-500">
        Carregando...
      </div>
    );
  }

  if (success) {
    return (
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-lg text-center">
        <h1 className="text-xl font-semibold text-gray-900 mb-2">Cadastro realizado!</h1>
        <p className="text-gray-600 mb-6">
          Você foi adicionado ao grupo <strong>{info?.group_name}</strong>.
        </p>
        <a
          href="/login"
          className="inline-block rounded-lg bg-[var(--color-primary)] px-6 py-2 text-white hover:opacity-90"
        >
          Ir para o login
        </a>
      </div>
    );
  }

  if (!info) {
    return (
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-lg text-center">
        <h1 className="text-xl font-semibold text-red-600 mb-2">Link indisponível</h1>
        <p className="text-gray-600">{error || 'Este link expirou ou foi revogado.'}</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-lg">
      <div className="mb-6 text-center">
        {config.logoUrl && (
          <img src={config.logoUrl} alt={config.appName} className="mx-auto mb-4 h-12 object-contain" />
        )}
        <h1 className="text-xl font-semibold text-gray-900">Cadastro de vendedor</h1>
        <p className="mt-1 text-sm text-gray-600">
          Grupo: <span style={{ color: info.group_color }}>{info.group_name}</span>
        </p>
        <p className="text-sm text-gray-500">{info.company_name}</p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">CPF</label>
          <input
            type="text"
            required
            value={cpf}
            onChange={(e) => setCpf(applyCpfMask(e.target.value))}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            placeholder="000.000.000-00"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
            <input
              type="text"
              required
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Sobrenome</label>
            <input
              type="text"
              required
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">E-mail</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Telefone</label>
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            placeholder="Opcional"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Senha</label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            minLength={6}
          />
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-[var(--color-primary)] py-2.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? 'Cadastrando...' : 'Criar conta'}
        </button>
      </form>
    </div>
  );
}
