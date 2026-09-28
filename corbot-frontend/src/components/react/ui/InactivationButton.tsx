import { useState } from 'react';
import { Modal } from './Modal';
import { Button } from './Button';
import { api } from '../../../lib/api/client';
import { extractErrorMessage } from '../../../lib/api/errors';
import { Ban, CheckCircle } from 'lucide-react';
import toast from 'react-hot-toast';

interface InactivationButtonProps {
  isActive: boolean;
  activationUrl: string;
  /** Data/hora ISO da inativação, se houver. */
  inactivatedAt?: string | null;
  inactivationReason?: string | null;
  onDone: () => void;
  warning?: string;
}

/**
 * Botão de (in)ativação com registro de motivo. Reaproveitável para
 * Corbans e Usuários (ambos expõem POST {endpoint}/activation/).
 */
export function InactivationButton({
  isActive,
  activationUrl,
  inactivatedAt,
  inactivationReason,
  onDone,
  warning,
}: InactivationButtonProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleActivate() {
    setLoading(true);
    try {
      await api.post(activationUrl, { action: 'activate' });
      toast.success('Reativado com sucesso.');
      onDone();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  async function handleDeactivate() {
    if (!reason.trim()) {
      toast.error('Informe o motivo da inativação.');
      return;
    }
    setLoading(true);
    try {
      await api.post(activationUrl, { action: 'deactivate', reason: reason.trim() });
      toast.success('Inativado com sucesso.');
      setModalOpen(false);
      setReason('');
      onDone();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  if (isActive) {
    return (
      <>
        <Button variant="danger" size="sm" onClick={() => setModalOpen(true)}>
          <Ban size={16} />
          Inativar
        </Button>
        <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Inativar" size="sm">
          <div className="space-y-3">
            {warning && <p className="text-xs text-amber-700 bg-amber-50 rounded-lg px-3 py-2">{warning}</p>}
            <label className="space-y-1 block">
              <span className="text-sm text-gray-600">Motivo da inativação</span>
              <textarea
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                rows={3}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Descreva o motivo..."
              />
            </label>
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" size="sm" onClick={() => setModalOpen(false)}>
                Cancelar
              </Button>
              <Button variant="danger" size="sm" onClick={handleDeactivate} loading={loading}>
                Confirmar inativação
              </Button>
            </div>
          </div>
        </Modal>
      </>
    );
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <Button variant="secondary" size="sm" onClick={handleActivate} loading={loading}>
        <CheckCircle size={16} />
        Reativar
      </Button>
      {(inactivatedAt || inactivationReason) && (
        <p className="text-xs text-gray-500">
          Inativado {inactivatedAt ? `em ${new Date(inactivatedAt).toLocaleString('pt-BR')}` : ''}
          {inactivationReason ? ` — Motivo: ${inactivationReason}` : ''}
        </p>
      )}
    </div>
  );
}
