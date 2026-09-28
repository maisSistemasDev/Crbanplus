import { useState } from 'react';
import { Sparkles } from 'lucide-react';
import { api, ApiError } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import type { ProposalEtlFlow } from '../../../../lib/api/types/etl';
import { Button } from '../../ui/Button';
import { Input } from '../../ui/Input';
import { Modal } from '../../ui/Modal';
import { SearchSelect } from '../../ui/SearchSelect';

interface EtlGenerateFromDocModalProps {
  open: boolean;
  onClose: () => void;
}

export function EtlGenerateFromDocModal({ open, onClose }: EtlGenerateFromDocModalProps) {
  const [name, setName] = useState('');
  const [documentation, setDocumentation] = useState('');
  const [bankId, setBankId] = useState('');
  const [layoutId, setLayoutId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    if (!documentation.trim()) {
      setError('Cole a documentação ou exemplos cURL da API.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const flow = await api.post<ProposalEtlFlow & { warnings?: string[]; source?: string }>(
        ENDPOINTS.PROPOSAL_ETL_GENERATE_FROM_DOC,
        {
          name: name.trim() || undefined,
          documentation: documentation.trim(),
          bank: bankId || undefined,
          layout_id: layoutId || undefined,
        },
      );
      if (flow.warnings?.length) {
        sessionStorage.setItem(`etl-warnings-${flow.id}`, JSON.stringify(flow.warnings));
      }
      window.location.href = `/proposal-etl/${flow.id}`;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao gerar fluxo.');
      setLoading(false);
    }
  }

  function handleClose() {
    if (loading) return;
    onClose();
  }

  return (
    <Modal open={open} onClose={handleClose} title="Gerar fluxo com IA" size="xl">
      <div className="p-4 space-y-4">
        <p className="text-sm text-gray-600">
          Cole a documentação da API, exemplos cURL ou OpenAPI. A IA monta um rascunho do fluxo
          (auth → HTTP → extrair → mapear → lote) para você revisar no editor.
        </p>

        <Input
          label="Nome do fluxo (opcional)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="ETL Unnotech Propostas"
        />

        <SearchSelect
          label="Banco (opcional)"
          options_url={ENDPOINTS.BANKS}
          value={bankId}
          onChange={(e) => setBankId(e.target.value)}
        />

        <SearchSelect
          label="Layout de importação (recomendado)"
          options_url={ENDPOINTS.LAYOUTS}
          value={layoutId}
          onChange={(e) => setLayoutId(e.target.value)}
        />

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Documentação / cURL
          </label>
          <textarea
            className="w-full min-h-[220px] border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono"
            value={documentation}
            onChange={(e) => setDocumentation(e.target.value)}
            placeholder={`curl --location 'https://gtw.exemplo.com/public/api/v1/auth/token' \\
--header 'Content-Type: application/json' \\
--data '{"client_id": "...", "client_secret": "..."}'

curl --location 'https://gtw.exemplo.com/api/v1/propostas' \\
--header 'Authorization: Bearer ...'`}
          />
        </div>

        {error && (
          <div className="px-3 py-2 rounded-lg bg-red-50 text-red-700 text-sm">{error}</div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={handleClose} disabled={loading}>
            Cancelar
          </Button>
          <Button loading={loading} icon={<Sparkles size={16} />} onClick={handleGenerate}>
            Gerar fluxo
          </Button>
        </div>
      </div>
    </Modal>
  );
}
