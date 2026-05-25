import { useState, useEffect } from 'react';
import { api, API_BASE_URL } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Button } from '../../ui/Button';
import { Badge } from '../../ui/Badge';
import { DataTable } from '../../ui/DataTable';
import { PageSpinner } from '../../ui/Spinner';
import { useBatchProgress } from '../../../../lib/ws/useBatchProgress';
import { formatDate, formatCurrency } from '../../../../lib/utils/format';
import type { ProposalBatch, Proposal, PaginatedResponse } from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { ArrowLeft, Play, Download, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { ValueMatcher } from './ValueMatcher';

interface BatchDetailProps {
  batchId: string;
}

const proposalColumns: Column<Record<string, unknown>>[] = [
  { key: 'contract_number', header: 'Contrato', sortable: true },
  { key: 'client_name', header: 'Cliente' },
  { key: 'client_document', header: 'CPF' },
  {
    key: 'amount',
    header: 'Valor',
    render: (item) => formatCurrency(Number(item.amount)),
  },
  { key: 'status', header: 'Status' },
];

export function BatchDetail({ batchId }: BatchDetailProps) {
  const [batch, setBatch] = useState<ProposalBatch | null>(null);
  const [proposals, setProposals] = useState<Record<string, unknown>[]>([]);
  const [totalProposals, setTotalProposals] = useState(0);
  const [proposalPage, setProposalPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const progress = useBatchProgress(batchId);

  useEffect(() => {
    async function load() {
      try {
        const [batchData, proposalData] = await Promise.all([
          api.get<ProposalBatch>(ENDPOINTS.BATCH_DETAIL(batchId)),
          api.get<PaginatedResponse<Proposal>>(`${ENDPOINTS.BATCH_PROPOSALS(batchId)}?page=${proposalPage}`),
        ]);
        setBatch(batchData);
        const results = Array.isArray(proposalData) ? proposalData : (proposalData?.results || []);
        setProposals(results as unknown as Record<string, unknown>[]);
        setTotalProposals(proposalData?.count || results.length);
      } catch {
        toast.error('Erro ao carregar lote');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [batchId, proposalPage]);

  // Update batch from WebSocket progress
  useEffect(() => {
    if (progress) {
      setBatch((prev) =>
        prev
          ? {
              ...prev,
              status: progress.status,
              processed_rows: progress.processed_proposals,
              errored_rows: progress.error_proposals,
              total_rows: progress.total_proposals,
            }
          : prev,
      );
    }
  }, [progress]);

  if (loading) return <PageSpinner />;
  if (!batch) return <div className="text-center py-12 text-gray-400">Lote nao encontrado</div>;

  const progressPct = batch.total_rows > 0 ? (batch.processed_rows / batch.total_rows) * 100 : 0;

  const handleDeleteBatch = async () => {
    if (!window.confirm('⚠️ Tem certeza que deseja deletar este lote? Isso não pode ser desfeito.')) {
      return;
    }

    setDeleting(true);
    try {
      await api.delete(ENDPOINTS.BATCH_DETAIL(batchId));
      toast.success('Lote deletado com sucesso!');
      // Redirecionar de volta para a lista de lotes
      setTimeout(() => (window.location.href = `${window.location.origin}/proposals/batches`), 1000);
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || 'Erro ao deletar lote';
      toast.error(errorMsg);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="animate-fadeIn">
      <div className="flex items-center gap-3 mb-6">
        <Button variant="ghost" size="sm" onClick={() => (window.location.href = `${window.location.origin}/proposals/batches`)}>
          <ArrowLeft size={16} />
        </Button>
        <h1 className="text-2xl font-bold text-gray-900">Lote de Propostas</h1>
      </div>

      {/* Batch Info Card */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6 transition-all duration-300">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div>
            <p className="text-xs text-gray-400">Banco</p>
            <p className="font-medium">{batch.bank_name}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400">Layout</p>
            <p className="font-medium">{batch.layout_name}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400">Data</p>
            <p className="font-medium">{formatDate(batch.created_at)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400">Status</p>
            <Badge
              variant={
                batch.status === 'completed'
                  ? 'success'
                  : batch.status === 'failed'
                    ? 'error'
                    : batch.status === 'processing'
                      ? 'info'
                      : 'warning'
              }
            >
              {batch.status}
            </Badge>
          </div>
        </div>

        {/* Progress bar */}
        {batch.status === 'processing' && (
          <div className="mt-4 animate-fadeIn">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Progresso</span>
              <span>
                {batch.processed_rows} / {batch.total_rows} ({Math.round(progressPct)}%)
              </span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div
                className="bg-[var(--color-primary)] h-2 rounded-full transition-all duration-500"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            {progress?.message && (
              <p className="text-xs text-gray-400 mt-1 transition-all duration-300">{progress.message}</p>
            )}
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mt-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg transition-all duration-300 hover:shadow-sm">
            <p className="text-2xl font-bold text-gray-900">{batch.total_rows}</p>
            <p className="text-xs text-gray-500">Total</p>
          </div>
          <div className="text-center p-3 bg-green-50 rounded-lg transition-all duration-300 hover:shadow-sm">
            <p className="text-2xl font-bold text-green-600">{batch.processed_rows}</p>
            <p className="text-xs text-gray-500">Processadas</p>
          </div>
          <div className="text-center p-3 bg-red-50 rounded-lg transition-all duration-300 hover:shadow-sm">
            <p className="text-2xl font-bold text-red-600">{batch.errored_rows}</p>
            <p className="text-xs text-gray-500">Erros</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 mt-4">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              try {
                if (batch.original_file_url) {
                  const fullUrl = `${API_BASE_URL}${batch.original_file_url}`;
                  window.open(fullUrl, '_blank');
                } else {
                  toast.error('Arquivo original não disponível');
                }
              } catch (e) {
                toast.error('Erro ao baixar arquivo original');
              }
            }}
            title="Baixar arquivo Excel original enviado"
          >
            <Download size={14} />
            Download Original
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              try {
                if (batch.log_url) {
                  const fullUrl = `${API_BASE_URL}${batch.log_url}`;
                  window.open(fullUrl, '_blank');
                } else {
                  toast.error('Log não disponível - sem erros no processamento');
                }
              } catch (e) {
                toast.error('Erro ao baixar log');
              }
            }}
            title="Baixar log com propostas que tiveram erro"
            disabled={!batch.log_url}
          >
            <Download size={14} />
            Download Log
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={handleDeleteBatch}
            loading={deleting}
            disabled={deleting}
            className="text-red-600 hover:bg-red-50 transition-all duration-300"
            title="Deletar lote (só é possível se não tiver comissões geradas)"
          >
            <Trash2 size={14} />
            Deletar Lote
          </Button>
        </div>
      </div>

      {/* Value Matcher (when pending) */}
      {batch.status === 'pending' && batch.bank_id && (
        <div className="animate-fadeIn">
          <ValueMatcher
            batchId={batchId}
            bankId={batch.bank_id}
            onProcessStart={() =>
              setBatch((prev) => (prev ? { ...prev, status: 'processing' } : prev))
            }
          />
        </div>
      )}

      {/* Proposals Table (when processing or done) */}
      {batch.status !== 'pending' && (
        <div className="animate-fadeIn transition-all duration-300">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Propostas do Lote</h2>
          <DataTable
            columns={proposalColumns}
            data={proposals}
            totalItems={totalProposals}
            currentPage={proposalPage}
            onPageChange={setProposalPage}
            keyExtractor={(item) => item.id as string}
            emptyMessage="Nenhuma proposta neste lote"
          />
        </div>
      )}
    </div>
  );
}
