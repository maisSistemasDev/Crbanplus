import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { Button } from '../../ui/Button';
import { PageHeader } from '../../ui/PageHeader';
import { DataTable } from '../../ui/DataTable';
import { Badge } from '../../ui/Badge';
import { PageSpinner } from '../../ui/Spinner';
import { formatCurrency, formatDate } from '../../../../lib/utils/format';
import type { Column } from '../../ui/DataTable';
import { DollarSign, CheckCircle, Wallet } from 'lucide-react';
import toast from 'react-hot-toast';

interface WithdrawEntry {
  id: number;
  amount: string;
  created_at: string;
  payment: number;
}

const STATUS_MAP: Record<string, { label: string; variant: 'default' | 'success' | 'warning' | 'error' | 'info' }> = {
  pending: { label: 'Pendente', variant: 'warning' },
  approved: { label: 'Aprovado', variant: 'info' },
  paid: { label: 'Pago', variant: 'success' },
  rejected: { label: 'Rejeitado', variant: 'error' },
};

const columns: Column<Record<string, unknown>>[] = [
  {
    key: 'amount',
    header: 'Valor',
    render: (item) => (
      <span className="font-medium text-green-600">
        {formatCurrency(Number(item.amount))}
      </span>
    ),
  },
  {
    key: 'created_at',
    header: 'Data',
    render: (item) => formatDate(item.created_at as string),
  },
];

export function WithdrawalRequest() {
  const [withdrawals, setWithdrawals] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<WithdrawEntry[] | { results: WithdrawEntry[] }>(ENDPOINTS.WITHDRAWALS);
      const list = Array.isArray(res) ? res : res.results || [];
      setWithdrawals(list as unknown as Record<string, unknown>[]);
    } catch {
      setWithdrawals([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function handleWithdraw() {
    setSubmitting(true);
    try {
      await api.post(ENDPOINTS.WITHDRAWALS);
      toast.success('Saque solicitado com sucesso!');
      fetchData();
    } catch (error) {
      // Usar o utilitário para extrair mensagem específica
      const errorMessage = extractErrorMessage(error);
      toast.error(errorMessage);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <PageSpinner />;

  return (
    <div>
      <PageHeader
        title="Saques"
        actions={
          <Button size="sm" onClick={handleWithdraw} loading={submitting}>
            <Wallet size={16} />
            Solicitar saque
          </Button>
        }
      />

      <p className="text-sm text-gray-500 mb-4">
        Ao solicitar um saque, todas as suas comissoes liberadas serao vinculadas ao pagamento.
      </p>

      <DataTable
        columns={columns}
        data={withdrawals}
        loading={loading}
        totalItems={withdrawals.length}
        currentPage={1}
        onPageChange={() => {}}
        keyExtractor={(item) => String(item.id)}
        emptyMessage="Nenhum saque realizado"
      />
    </div>
  );
}
