import { useState } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Modal } from '../../ui/Modal';
import { Button } from '../../ui/Button';
import { formatCurrency } from '../../../../lib/utils/format';
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { extractErrorMessage } from '../../../../lib/utils/errors';

interface WithdrawModalProps {
  isOpen: boolean;
  onClose: () => void;
  availableAmount: number;
  onSuccess: () => void;
}

export function WithdrawModal({ isOpen, onClose, availableAmount, onSuccess }: WithdrawModalProps) {
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<'confirm' | 'processing' | 'success'>('confirm');

  const handleWithdraw = async () => {
    setLoading(true);
    setStep('processing');

    try {
      // Simula processamento por 2 segundos
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Envia requisição de saque
      await api.post(ENDPOINTS.WITHDRAWALS, {});

      setStep('success');
      toast.success('Saque realizado com sucesso!');

      // Fecha modal após 1.5 segundos
      setTimeout(() => {
        onSuccess();
        handleClose();
      }, 1500);
    } catch (error) {
      setStep('confirm');
      toast.error(extractErrorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      setStep('confirm');
      onClose();
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Solicitar Saque">
      <div className="space-y-4">
        {step === 'confirm' && (
          <>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertCircle size={20} className="text-blue-600 mt-0.5" />
                <div className="text-sm text-blue-800">
                  <p className="font-medium mb-1">Atenção</p>
                  <p>Você está prestes a sacar todo o saldo disponível. Esta ação não pode ser desfeita.</p>
                </div>
              </div>
            </div>

            <div className="bg-gray-50 rounded-lg p-4 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Saldo Disponível:</span>
                <span className="text-lg font-bold text-gray-900">{formatCurrency(availableAmount)}</span>
              </div>
              <div className="border-t border-gray-200 my-2"></div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-900">Valor do Saque:</span>
                <span className="text-xl font-bold text-green-600">{formatCurrency(availableAmount)}</span>
              </div>
            </div>

            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
              <p className="text-xs text-yellow-800">
                <strong>Importante:</strong> Após a confirmação, suas comissões serão marcadas como pagas e o saldo será zerado.
              </p>
            </div>

            <div className="flex gap-3 mt-6">
              <Button
                onClick={handleClose}
                variant="secondary"
                className="flex-1"
                disabled={loading}
              >
                Cancelar
              </Button>
              <Button
                onClick={handleWithdraw}
                variant="primary"
                className="flex-1"
                disabled={loading}
              >
                Confirmar Saque
              </Button>
            </div>
          </>
        )}

        {step === 'processing' && (
          <div className="text-center py-8">
            <Loader2 size={48} className="animate-spin text-blue-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Processando Saque</h3>
            <p className="text-sm text-gray-600">
              Aguarde enquanto processamos sua solicitação...
            </p>
            <div className="mt-4 bg-blue-50 rounded-lg p-3">
              <p className="text-sm text-blue-800">
                Valor: <strong>{formatCurrency(availableAmount)}</strong>
              </p>
            </div>
          </div>
        )}

        {step === 'success' && (
          <div className="text-center py-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
              <CheckCircle2 size={32} className="text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Saque Realizado!</h3>
            <p className="text-sm text-gray-600 mb-4">
              Seu saque de <strong>{formatCurrency(availableAmount)}</strong> foi processado com sucesso.
            </p>
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <p className="text-xs text-green-800">
                As comissões foram marcadas como pagas e seu saldo foi atualizado.
              </p>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
