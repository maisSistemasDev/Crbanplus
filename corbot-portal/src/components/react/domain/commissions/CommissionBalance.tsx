import { useEffect, useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { formatCurrency } from '../../../../lib/utils/format';
import { PageHeader } from '../../ui/PageHeader';
import { SectionSpinner } from '../../ui/Spinner';

interface Balance {
  available: number;
  pending: number;
}

export function CommissionBalance() {
  const [balance, setBalance] = useState<Balance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .get<Balance>(ENDPOINTS.COMMISSION_BALANCE)
      .then(setBalance)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <PageHeader title="Saldo" subtitle="Saldo de comissões disponível e aguardando pagamento." />

      {loading ? (
        <SectionSpinner />
      ) : error ? (
        <div className="card text-sm text-red-600">{error}</div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="card">
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
              Disponível para saque
            </p>
            <p className="mt-2 text-3xl font-bold text-emerald-600">{formatCurrency(balance?.available ?? 0)}</p>
            <p className="mt-2 text-xs text-[var(--color-text-muted)]">
              Comissões já liberadas, prontas para saque via CorbanPay.
            </p>
            <a
              href="/withdrawals"
              className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-[var(--color-primary)] hover:underline"
            >
              Solicitar saque <ArrowRight className="h-3.5 w-3.5" />
            </a>
          </div>
          <div className="card">
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
              Aguardando pagamento manual
            </p>
            <p className="mt-2 text-3xl font-bold text-amber-600">{formatCurrency(balance?.pending ?? 0)}</p>
            <p className="mt-2 text-xs text-[var(--color-text-muted)]">
              Comissões que serão pagas fora do fluxo automático de saque.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
