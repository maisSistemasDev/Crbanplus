import { useState } from 'react';
import { api, API_URL } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Modal } from '../../ui/Modal';
import { Download, CreditCard } from 'lucide-react';
import toast from 'react-hot-toast';
import { extractErrorMessage } from '../../../../lib/api/errors';

interface ReleaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedIds: number[];
  selectedCommissions: Array<{ id: number; release_status?: string }>;
  onSuccess: () => void;
}

export function ReleaseModal({ isOpen, onClose, selectedIds, selectedCommissions, onSuccess }: ReleaseModalProps) {
  const [releasing, setReleasing] = useState(false);
  const [downloadingExcel, setDownloadingExcel] = useState(false);

  // Verificar se há comissões aguardando pagamento selecionadas
  const hasPendingPayment = selectedCommissions.some(
    comm => comm.release_status === 'pending_manual_payment'
  );

  async function handleUpdateStatus(newStatus: 'withdraw_available' | 'paid') {
    setReleasing(true);
    try {
      await api.post(ENDPOINTS.COMMISSION_UPDATE_STATUS, {
        commission_ids: selectedIds,
        new_status: newStatus,
      });
      const statusLabel = newStatus === 'withdraw_available' ? 'saque liberado' : 'pago';
      toast.success(`Comissões atualizadas para '${statusLabel}' com sucesso!`);
      onSuccess();
      onClose();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setReleasing(false);
    }
  }

  async function handleDownloadExcel() {
    setDownloadingExcel(true);
    try {
      const response = await fetch(`${API_URL}${ENDPOINTS.COMMISSION_EXPORT}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${JSON.parse(localStorage.getItem('tokens') || '{}').access}`,
        },
        body: JSON.stringify({ commission_ids: selectedIds }),
      });

      if (!response.ok) throw new Error('Erro ao gerar Excel');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pagamentos_comissoes_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success('Excel gerado com sucesso!');
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setDownloadingExcel(false);
    }
  }

  async function handleRelease(type: 'withdraw' | 'manual') {
    if (type === 'manual') {
      setDownloadingExcel(true);
      try {
        await api.post(ENDPOINTS.COMMISSION_RELEASE, {
          commission_ids: selectedIds,
          release_type: 'manual',
        });

        await handleDownloadExcel();
        
        toast.success('Comissões liberadas e Excel gerado com sucesso!');
        onSuccess();
        onClose();
      } catch (error) {
        toast.error(extractErrorMessage(error));
      } finally {
        setDownloadingExcel(false);
      }
    } else {
      setReleasing(true);
      try {
        await api.post(ENDPOINTS.COMMISSION_RELEASE, {
          commission_ids: selectedIds,
          release_type: 'withdraw',
        });
        toast.success('Comissões liberadas para saque com sucesso!');
        onSuccess();
        onClose();
      } catch (error) {
        toast.error(extractErrorMessage(error));
      } finally {
        setReleasing(false);
      }
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={hasPendingPayment ? "Gerenciar Comissões" : "Liberar Comissões"}>
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Você selecionou <strong>{selectedIds.length}</strong> comissão(ões).{' '}
          {hasPendingPayment ? 'Escolha uma ação:' : 'Escolha como deseja liberar:'}
        </p>

        {hasPendingPayment ? (
          // Opções para comissões aguardando pagamento
          <div className="grid grid-cols-1 gap-3">
            <button
              onClick={handleDownloadExcel}
              disabled={releasing || downloadingExcel}
              className="flex items-center gap-3 p-4 border-2 border-gray-200 rounded-lg hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-bg)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex-shrink-0 w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
                <Download size={20} className="text-purple-600" />
              </div>
              <div className="flex-1 text-left">
                <h3 className="font-semibold text-gray-900">Baixar Excel</h3>
                <p className="text-xs text-gray-500">
                  Gera novamente o arquivo Excel com os dados de pagamento
                </p>
              </div>
            </button>

            <button
              onClick={() => handleUpdateStatus('withdraw_available')}
              disabled={releasing || downloadingExcel}
              className="flex items-center gap-3 p-4 border-2 border-gray-200 rounded-lg hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-bg)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                <CreditCard size={20} className="text-blue-600" />
              </div>
              <div className="flex-1 text-left">
                <h3 className="font-semibold text-gray-900">Marcar como Saque Liberado</h3>
                <p className="text-xs text-gray-500">
                  Atualiza o status para saque disponível
                </p>
              </div>
            </button>

            <button
              onClick={() => handleUpdateStatus('paid')}
              disabled={releasing || downloadingExcel}
              className="flex items-center gap-3 p-4 border-2 border-gray-200 rounded-lg hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-bg)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex-shrink-0 w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                <Download size={20} className="text-green-600" />
              </div>
              <div className="flex-1 text-left">
                <h3 className="font-semibold text-gray-900">Marcar como Pago</h3>
                <p className="text-xs text-gray-500">
                  Confirma que o pagamento foi realizado
                </p>
              </div>
            </button>
          </div>
        ) : (
          // Opções para comissões não liberadas
          <div className="grid grid-cols-1 gap-3">
            <button
              onClick={() => handleRelease('withdraw')}
              disabled={releasing || downloadingExcel}
              className="flex items-center gap-3 p-4 border-2 border-gray-200 rounded-lg hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-bg)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                <CreditCard size={20} className="text-blue-600" />
              </div>
              <div className="flex-1 text-left">
                <h3 className="font-semibold text-gray-900">Liberar para Saque</h3>
                <p className="text-xs text-gray-500">
                  As comissões ficarão disponíveis para saque pelos usuários
                </p>
              </div>
            </button>

            <button
              onClick={() => handleRelease('manual')}
              disabled={releasing || downloadingExcel}
              className="flex items-center gap-3 p-4 border-2 border-gray-200 rounded-lg hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-bg)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex-shrink-0 w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                <Download size={20} className="text-green-600" />
              </div>
              <div className="flex-1 text-left">
                <h3 className="font-semibold text-gray-900">Pagar Manualmente</h3>
                <p className="text-xs text-gray-500">
                  Gera um arquivo Excel com os dados para pagamento manual
                </p>
              </div>
            </button>
          </div>
        )}

        {(releasing || downloadingExcel) && (
          <div className="flex items-center justify-center py-4">
            <div className="animate-spin h-6 w-6 border-2 border-[var(--color-primary)] border-t-transparent rounded-full" />
            <span className="ml-2 text-sm text-gray-600">
              {downloadingExcel ? 'Gerando Excel...' : 'Processando...'}
            </span>
          </div>
        )}
      </div>
    </Modal>
  );
}
