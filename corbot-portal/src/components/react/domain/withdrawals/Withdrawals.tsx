import { useEffect, useState } from 'react';
import { ExternalLink, Wallet } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { formatCurrency, formatDateTime } from '../../../../lib/utils/format';
import type { CorbanPayTransaction, Withdraw } from '../../../../lib/api/types';
import { PageHeader } from '../../ui/PageHeader';
import { Button } from '../../ui/Button';
import { EmptyState } from '../../ui/EmptyState';
import { SectionSpinner } from '../../ui/Spinner';
import { StatusBadge } from '../../ui/Badge';

const TXN_STATUS_LABELS: Record<string, string> = {
  pending: 'Pendente',
  active: 'Ativo — aguardando saque',
  withdrawn: 'Sacado',
  failed: 'Falhou',
};

interface Balance {
  available: number;
  pending: number;
}

export function Withdrawals() {
  const [withdrawals, setWithdrawals] = useState<Withdraw[]>([]);
  const [balance, setBalance] = useState<Balance | null>(null);
  const [activeTxn, setActiveTxn] = useState<CorbanPayTransaction | null>(null);
  const [loading, setLoading] = useState(true);
  const [requesting, setRequesting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function load() {
    setLoading(true);
    Promise.all([
      api.get<Withdraw[]>(ENDPOINTS.WITHDRAWALS).catch(() => []),
      api.get<Balance>(ENDPOINTS.COMMISSION_BALANCE).catch(() => null),
      api.get<CorbanPayTransaction>(ENDPOINTS.WITHDRAWALS_CORBANPAY).catch(() => null),
    ]).then(([withdrawalsRes, balanceRes, txnRes]) => {
      setWithdrawals(withdrawalsRes);
      setBalance(balanceRes);
      setActiveTxn(txnRes);
      setLoading(false);
    });
  }

  async function handleRequestWithdraw() {
    setRequesting(true);
    setError('');
    try {
      const txn = await api.post<CorbanPayTransaction>(ENDPOINTS.WITHDRAWALS_CORBANPAY);
      setActiveTxn(txn);
      toast.success('Saque solicitado com sucesso!');
      load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setRequesting(false);
    }
  }

  const canRequest = (balance?.available ?? 0) > 0 && activeTxn?.status !== 'active';

  return (
    <div>
      <PageHeader title="Saques CorbanPay" subtitle="Solicite o saque das comissões disponíveis e acompanhe o histórico." />

      {loading ? (
        <SectionSpinner />
      ) : (
        <div className="space-y-5">
          <div className="card flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
                Saldo disponível
              </p>
              <p className="mt-1 text-2xl font-bold text-emerald-600">{formatCurrency(balance?.available ?? 0)}</p>
            </div>
            <Button onClick={handleRequestWithdraw} disabled={!canRequest || requesting}>
              {requesting ? 'Solicitando...' : 'Solicitar saque'}
            </Button>
          </div>

          {error && <div className="card text-sm text-red-600">{error}</div>}

          {activeTxn && activeTxn.status === 'active' && activeTxn.withdrawal_link && (
            <div className="card border-l-4 border-l-emerald-500">
              <p className="text-sm font-medium text-[var(--color-text)]">
                Saque de {formatCurrency(activeTxn.amount)} pronto para ser recebido.
              </p>
              <a
                href={activeTxn.withdrawal_link}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-primary)] hover:underline"
              >
                Abrir link de saque <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          )}

          <div className="card">
            <h2 className="section-title mb-3">Histórico de saques</h2>
            {withdrawals.length === 0 ? (
              <EmptyState icon={Wallet} title="Nenhum saque realizado" description="Seus saques aparecerão aqui." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase text-[var(--color-text-muted)]">
                      <th className="py-2 pr-3">Valor</th>
                      <th className="py-2 pr-3">Data</th>
                      <th className="py-2 pr-3">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {withdrawals.map((withdraw) => (
                      <tr key={withdraw.id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-2 pr-3 font-medium text-emerald-700">{formatCurrency(withdraw.amount)}</td>
                        <td className="py-2 pr-3 text-[var(--color-text-muted)]">{formatDateTime(withdraw.created_at)}</td>
                        <td className="py-2 pr-3">
                          <StatusBadge status="pago" label="Processado" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {activeTxn && (
            <p className="text-xs text-[var(--color-text-muted)]">
              Última transação CorbanPay: {TXN_STATUS_LABELS[activeTxn.status] ?? activeTxn.status}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
