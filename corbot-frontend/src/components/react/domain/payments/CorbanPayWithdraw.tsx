import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { Button } from '../../ui/Button';
import { PageHeader } from '../../ui/PageHeader';
import { Badge } from '../../ui/Badge';
import { formatCurrency, formatDate } from '../../../../lib/utils/format';
import type { CorbanPayTransaction } from '../../../../lib/api/types';
import { Wallet, ExternalLink, RefreshCw, CheckCircle, Clock, XCircle, Link } from 'lucide-react';
import toast from 'react-hot-toast';

const STATUS_CONFIG: Record<
  CorbanPayTransaction['status'],
  { label: string; variant: 'default' | 'success' | 'warning' | 'error' | 'info'; icon: React.ReactNode }
> = {
  pending:   { label: 'Pendente',              variant: 'warning', icon: <Clock size={14} /> },
  active:    { label: 'Aguardando saque',       variant: 'info',    icon: <Link size={14} /> },
  withdrawn: { label: 'Sacado',                 variant: 'success', icon: <CheckCircle size={14} /> },
  failed:    { label: 'Falhou',                 variant: 'error',   icon: <XCircle size={14} /> },
};

export function CorbanPayWithdraw() {
  const [txn, setTxn] = useState<CorbanPayTransaction | null>(null);
  const [balance, setBalance] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [balanceRes, txnRes] = await Promise.allSettled([
        api.get<{ available: number; pending: number; balance?: number | string }>(ENDPOINTS.COMMISSION_BALANCE),
        api.get<CorbanPayTransaction>(ENDPOINTS.WITHDRAWALS_CORBANPAY),
      ]);

      if (balanceRes.status === 'fulfilled') {
        const payload = balanceRes.value as { available?: number | string; balance?: number | string };
        const rawAvailable = payload.available ?? payload.balance ?? 0;
        const parsedAvailable = typeof rawAvailable === 'number' ? rawAvailable : parseFloat(String(rawAvailable));
        setBalance(Number.isFinite(parsedAvailable) ? parsedAvailable : 0);
      }
      if (txnRes.status === 'fulfilled') {
        setTxn(txnRes.value as CorbanPayTransaction);
      } else {
        // 404 = nenhuma transação ativa
        setTxn(null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function handleRequestWithdraw() {
    setSubmitting(true);
    try {
      const result = await api.post<CorbanPayTransaction>(ENDPOINTS.WITHDRAWALS_CORBANPAY);
      setTxn(result);
      toast.success('Link de saque gerado com sucesso!');
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="animate-spin h-8 w-8 border-4 border-[var(--color-primary)] border-t-transparent rounded-full" />
      </div>
    );
  }

  const statusCfg = txn ? STATUS_CONFIG[txn.status] : null;
  const hasActiveLink = txn?.status === 'active' && txn.withdrawal_link;
  const canRequest = !txn || txn.status === 'failed' || txn.status === 'withdrawn';

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <PageHeader
        title="Saque de comissões"
        actions={
          <Button variant="ghost" size="sm" onClick={fetchData} loading={loading}>
            <RefreshCw size={16} />
            Atualizar
          </Button>
        }
      />

      {/* Saldo disponível */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <p className="text-sm text-gray-500 mb-1">Saldo disponível para saque</p>
        <p className="text-3xl font-bold text-green-600">
          {balance !== null ? formatCurrency(balance) : '—'}
        </p>
        {balance !== null && balance <= 0 && (
          <p className="text-sm text-gray-400 mt-2">
            Nenhuma comissão liberada no momento.
          </p>
        )}
      </div>

      {/* Transação ativa */}
      {txn && statusCfg && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-700">Última transação</h2>
            <Badge variant={statusCfg.variant}>
              <span className="flex items-center gap-1">
                {statusCfg.icon}
                {statusCfg.label}
              </span>
            </Badge>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-400">Valor</p>
              <p className="font-semibold text-gray-800">{formatCurrency(parseFloat(txn.amount))}</p>
            </div>
            <div>
              <p className="text-gray-400">Data</p>
              <p className="font-semibold text-gray-800">{formatDate(txn.created_at)}</p>
            </div>
            {txn.pre_payment_id && (
              <div>
                <p className="text-gray-400">ID Pré-Pagamento</p>
                <p className="font-mono text-xs text-gray-600 break-all">{txn.pre_payment_id}</p>
              </div>
            )}
            {txn.receiver_id && (
              <div>
                <p className="text-gray-400">ID Recebedor</p>
                <p className="font-mono text-xs text-gray-600 break-all">{txn.receiver_id}</p>
              </div>
            )}
          </div>

          {txn.error_message && (
            <div className="bg-red-50 border border-red-100 rounded-lg p-3 text-sm text-red-600">
              {txn.error_message}
            </div>
          )}

          {hasActiveLink && (
            <div className="space-y-3">
              <div className="bg-blue-50 border border-blue-100 rounded-lg p-3">
                <p className="text-xs text-blue-600 mb-1 font-medium">Link de saque</p>
                <p className="text-xs text-blue-700 break-all font-mono">{txn.withdrawal_link}</p>
              </div>
              <a
                href={txn.withdrawal_link}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 w-full justify-center px-4 py-2.5 bg-[var(--color-primary)] text-white text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
              >
                <ExternalLink size={16} />
                Acessar link de saque
              </a>
            </div>
          )}
        </div>
      )}

      {/* Ação de solicitar */}
      {canRequest && (
        <Button
          onClick={handleRequestWithdraw}
          loading={submitting}
          disabled={balance !== null && balance <= 0}
          className="w-full"
        >
          <Wallet size={18} />
          {submitting ? 'Processando…' : 'Solicitar Saque via CorbanPay'}
        </Button>
      )}

      {!canRequest && !hasActiveLink && (
        <p className="text-center text-sm text-gray-400">
          Seu saque está sendo processado. Aguarde a geração do link.
        </p>
      )}
    </div>
  );
}
