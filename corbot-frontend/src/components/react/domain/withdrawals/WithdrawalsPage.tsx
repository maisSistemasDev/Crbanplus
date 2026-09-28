import { useState, useEffect, useCallback } from 'react';
import { useStore } from '@nanostores/react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { $currentUser } from '../../../../lib/stores/auth';
import { DataTable } from '../../ui/DataTable';
import { Button } from '../../ui/Button';
import { PageHeader } from '../../ui/PageHeader';
import { Badge } from '../../ui/Badge';
import { formatCurrency, formatDate } from '../../../../lib/utils/format';
import { WithdrawModal } from './WithdrawModal';
import type { Column } from '../../ui/DataTable';
import { Wallet, ArrowDownToLine } from 'lucide-react';
import toast from 'react-hot-toast';

interface Withdrawal {
  id: number;
  user: number;
  amount: number;
  created_at: string;
  payment: number;
}

export function WithdrawalsPage() {
  const currentUser = useStore($currentUser);
  const [withdrawals, setWithdrawals] = useState<Withdrawal[]>([]);
  const [loading, setLoading] = useState(true);
  const [balance, setBalance] = useState<{ available: number; pending: number } | null>(null);
  const [withdrawModalOpen, setWithdrawModalOpen] = useState(false);

  const fetchWithdrawals = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<Withdrawal[]>(ENDPOINTS.WITHDRAWALS);
      setWithdrawals(data);
    } catch (error) {
      console.error('Error fetching withdrawals:', error);
      toast.error('Erro ao carregar saques');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchBalance = useCallback(async () => {
    try {
      const data = await api.get<{ available: number; pending: number }>(ENDPOINTS.COMMISSION_BALANCE);
      setBalance(data);
    } catch (error) {
      console.error('Error fetching balance:', error);
    }
  }, []);

  useEffect(() => {
    fetchWithdrawals();
    fetchBalance();
  }, [fetchWithdrawals, fetchBalance]);

  const handleWithdrawSuccess = () => {
    fetchWithdrawals();
    fetchBalance();
    setWithdrawModalOpen(false);
  };

  const columns: Column<Withdrawal>[] = [
    {
      key: 'id',
      header: 'ID',
      render: (item) => `#${item.id}`,
    },
    {
      key: 'amount',
      header: 'Valor',
      render: (item) => (
        <span className="font-semibold text-green-600">
          {formatCurrency(item.amount)}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Data',
      render: (item) => formatDate(item.created_at),
    },
    {
      key: 'status',
      header: 'Status',
      render: () => (
        <Badge variant="success">Processado</Badge>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Saques"
        subtitle="Gerencie seus saques de comissões"
        actions={
          balance !== null && balance.available > 0 ? (
            <Button
              size="sm"
              onClick={() => setWithdrawModalOpen(true)}
              variant="primary"
              icon={<ArrowDownToLine size={16} />}
            >
              Solicitar saque
            </Button>
          ) : undefined
        }
      />

      {balance !== null && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="bg-green-100 p-3 rounded-lg">
                <Wallet size={24} className="text-green-600" />
              </div>
              <div>
                <p className="text-sm text-green-700 font-medium">Disponível para Saque</p>
                <p className="text-2xl font-bold text-green-800">{formatCurrency(balance.available)}</p>
              </div>
            </div>
          </div>
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex items-center gap-3">
              <div className="bg-yellow-100 p-3 rounded-lg">
                <Wallet size={24} className="text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-yellow-700 font-medium">Aguardando Pagamento</p>
                <p className="text-2xl font-bold text-yellow-800">{formatCurrency(balance.pending)}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Histórico de Saques</h2>
        </div>
        <DataTable
          data={withdrawals}
          columns={columns}
          loading={loading}
          emptyMessage="Nenhum saque realizado"
        />
      </div>

      <WithdrawModal
        isOpen={withdrawModalOpen}
        onClose={() => setWithdrawModalOpen(false)}
        availableAmount={balance?.available || 0}
        onSuccess={handleWithdrawSuccess}
      />
    </div>
  );
}
