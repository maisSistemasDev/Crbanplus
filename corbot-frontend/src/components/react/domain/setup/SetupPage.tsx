import { useState, useEffect } from 'react';
import { useStore } from '@nanostores/react';
import { api } from '../../../../lib/api/client';
import { $whitelabel } from '../../../../lib/stores/whitelabel';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { applyCpfMask, applyCnpjMask } from '../../../../lib/utils/masks';

interface SetupData {
  company: {
    name: string;
    cnpj: string;
    email: string;
  };
  user: {
    cpf: string;
    email: string;
    first_name: string;
    last_name: string;
    password: string;
  };
}

export function SetupPage() {
  const config = useStore($whitelabel);
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState<SetupData>({
    company: { name: '', cnpj: '', email: '' },
    user: { cpf: '', email: '', first_name: '', last_name: '', password: '' },
  });

  useEffect(() => {
    api.get<{ initialized: boolean }>(ENDPOINTS.SETUP_STATUS)
      .then((res) => {
        if (res.initialized) {
          window.location.href = `${window.location.origin}/login`;
          return;
        }
        setChecking(false);
      })
      .catch(() => setChecking(false));
  }, []);

  function updateCompany(field: string, value: string) {
    setData((prev) => ({ ...prev, company: { ...prev.company, [field]: value } }));
  }

  function updateUser(field: string, value: string) {
    setData((prev) => ({ ...prev, user: { ...prev.user, [field]: value } }));
  }

  function handleNextStep(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setStep(2);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    if (data.user.password.length < 6) {
      setError('A senha deve ter pelo menos 6 caracteres.');
      return;
    }

    setLoading(true);
    try {
      await api.post(ENDPOINTS.SETUP, {
        company: {
          name: data.company.name,
          cnpj: data.company.cnpj,
          email: data.company.email,
        },
        user: {
          cpf: data.user.cpf,
          email: data.user.email,
          first_name: data.user.first_name,
          last_name: data.user.last_name,
          password: data.user.password,
        },
      });
      window.location.href = `${window.location.origin}/login`;
    } catch (error) {
      setError(extractErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  if (checking) {
    return (
      <div className="flex justify-center py-16">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-primary)]" />
      </div>
    );
  }

  const inputClass =
    'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent outline-none transition-all text-sm';

  return (
    <div className="w-full max-w-lg">
      <div className="bg-white rounded-xl shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="page-title">{config.systemName}</h1>
          <p className="page-subtitle">Configuração inicial</p>
          <div className="flex justify-center gap-2 mt-4">
            <div className={`h-2 w-16 rounded-full ${step >= 1 ? 'bg-[var(--color-primary)]' : 'bg-gray-200'}`} />
            <div className={`h-2 w-16 rounded-full ${step >= 2 ? 'bg-[var(--color-primary)]' : 'bg-gray-200'}`} />
          </div>
        </div>

        {step === 1 && (
          <form onSubmit={handleNextStep} className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Dados da Promotora</h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nome da Empresa</label>
              <input
                type="text"
                value={data.company.name}
                onChange={(e) => updateCompany('name', e.target.value)}
                className={inputClass}
                required
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">CNPJ</label>
              <input
                type="text"
                value={data.company.cnpj}
                onChange={(e) => updateCompany('cnpj', applyCnpjMask(e.target.value))}
                placeholder="00.000.000/0000-00"
                className={inputClass}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={data.company.email}
                onChange={(e) => updateCompany('email', e.target.value)}
                className={inputClass}
              />
            </div>
            <button
              type="submit"
              className="w-full py-2.5 px-4 bg-[var(--color-primary)] hover:bg-[var(--color-primary-dark)] text-white font-medium rounded-lg transition-colors text-sm"
            >
              Proximo
            </button>
          </form>
        )}

        {step === 2 && (
          <form onSubmit={handleSubmit} className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Administrador da Promotora</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
                <input
                  type="text"
                  value={data.user.first_name}
                  onChange={(e) => updateUser('first_name', e.target.value)}
                  className={inputClass}
                  required
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sobrenome</label>
                <input
                  type="text"
                  value={data.user.last_name}
                  onChange={(e) => updateUser('last_name', e.target.value)}
                  className={inputClass}
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">CPF</label>
              <input
                type="text"
                value={data.user.cpf}
                onChange={(e) => updateUser('cpf', applyCpfMask(e.target.value))}
                placeholder="000.000.000-00"
                className={inputClass}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={data.user.email}
                onChange={(e) => updateUser('email', e.target.value)}
                className={inputClass}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Senha</label>
              <input
                type="password"
                value={data.user.password}
                onChange={(e) => updateUser('password', e.target.value)}
                className={inputClass}
                required
              />
            </div>

            {error && (
              <div className="bg-red-50 text-red-600 text-sm p-3 rounded-lg">{error}</div>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="flex-1 py-2.5 px-4 border border-gray-300 text-gray-700 font-medium rounded-lg transition-colors text-sm hover:bg-gray-50"
              >
                Voltar
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 py-2.5 px-4 bg-[var(--color-primary)] hover:bg-[var(--color-primary-dark)] text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
              >
                {loading ? 'Configurando...' : 'Finalizar'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
