import { useState } from 'react';
import { api } from '../../../../lib/api/client';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Button } from '../../ui/Button';
import { PageHeader } from '../../ui/PageHeader';
import { Select } from '../../ui/Select';
import { Play, CheckCircle } from 'lucide-react';
import toast from 'react-hot-toast';

export function GenerateCommissions() {
  const [batchId, setBatchId] = useState('');
  const [generating, setGenerating] = useState(false);
  const [done, setDone] = useState(false);

  async function handleGenerate() {
    if (!batchId) {
      toast.error('Selecione um lote');
      return;
    }
    setGenerating(true);
    try {
      const res = await api.post<{
        detail?: string;
        statistics?: { created_commissions?: number; total_proposals?: number };
      }>(ENDPOINTS.GENERATE_COMMISSIONS, { batch_id: batchId });
      const created = res?.statistics?.created_commissions ?? 0;
      toast.success(
        created > 0
          ? `${created} comissão(ões) gerada(s) com sucesso!`
          : (res?.detail || 'Comissoes geradas com sucesso!'),
      );
      setDone(true);
    } catch (err: unknown) {
      toast.error(extractErrorMessage(err));
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div>
      <PageHeader title="Gerar comissões" />

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 max-w-xl">
        {done ? (
          <div className="text-center py-8">
            <CheckCircle size={48} className="mx-auto text-green-500 mb-4" />
            <p className="text-lg font-medium text-gray-900">Comissoes geradas com sucesso!</p>
            <p className="text-sm text-gray-500 mt-1">
              As comissoes foram calculadas e estao disponiveis para consulta.
            </p>
            <div className="flex gap-2 justify-center mt-6">
              <Button variant="secondary" onClick={() => (window.location.href = `${window.location.origin}/commissions`)}>
                Ver Comissoes
              </Button>
              <Button
                onClick={() => {
                  setDone(false);
                  setBatchId('');
                }}
              >
                Gerar Mais
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Selecione o lote de propostas para gerar as comissoes automaticamente.
            </p>
            <Select
              label="Lote de Propostas"
              required
              options_url={ENDPOINTS.BATCHES}
              value={batchId}
              onChange={(e) => setBatchId(e.target.value)}
            />
            <div className="pt-4">
              <Button onClick={handleGenerate} loading={generating} disabled={!batchId}>
                <Play size={16} />
                Gerar Comissoes
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
