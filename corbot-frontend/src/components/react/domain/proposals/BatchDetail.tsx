import { useState, useEffect, useRef, useCallback } from 'react';
import { api, API_BASE_URL } from '../../../../lib/api/client';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Button } from '../../ui/Button';
import { StatusBadge } from '../../ui/Badge';
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
    key: 'digitador',
    header: 'Digitador / Acesso',
    render: (item) => {
      const digitador = String((item.digitador as string | null) ?? '').trim();
      const bankAccess = item.bank_access_details as { display_name?: string; username?: string } | undefined;
      const accessName = bankAccess?.display_name || bankAccess?.username;
      if (digitador && accessName) {
        return (
          <div>
            <div className="font-medium text-sm">{digitador}</div>
            <div className="text-xs text-gray-500">{accessName}</div>
          </div>
        );
      }
      if (digitador) return <span className="text-sm">{digitador}</span>;
      if (accessName) return <span className="text-sm">{accessName}</span>;
      const seller = item.seller_details as { first_name?: string; last_name?: string } | undefined;
      return seller ? `${seller.first_name || ''} ${seller.last_name || ''}`.trim() || '-' : '-';
    },
  },
  {
    key: 'amount',
    header: 'Valor',
    render: (item) => formatCurrency(Number(item.amount)),
  },
  {
    key: 'commission_value',
    header: 'Comissão',
    render: (item) => {
      const value = item.commission_value;
      if (value === null || value === undefined || value === '') return '-';
      return formatCurrency(Number(value));
    },
  },
  {
    key: 'processing_status',
    header: 'Status',
    render: () => <StatusBadge status="processed" />,
  },
  {
    key: 'status',
    header: 'Status Pagamento',
    render: (item) => (
      <StatusBadge status={String(item.payment_status || item.status || 'pending')} />
    ),
  },
];

export function BatchDetail({ batchId }: BatchDetailProps) {
  const [batch, setBatch] = useState<ProposalBatch | null>(null);
  const [proposals, setProposals] = useState<Record<string, unknown>[]>([]);
  const [totalProposals, setTotalProposals] = useState(0);
  const [proposalPage, setProposalPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const progress = useBatchProgress(batchId);
  const finalSyncDoneRef = useRef(false);

  const resolveFileUrl = useCallback((url: string) => {
    if (!url) return '';
    if (/^https?:\/\//i.test(url)) return url;
    return `${API_BASE_URL}${url}`;
  }, []);

  const loadBatchDetail = useCallback(async () => {
    const batchData = await api.get<ProposalBatch>(ENDPOINTS.BATCH_DETAIL(batchId));
    setBatch(batchData);
    return batchData;
  }, [batchId]);

  const loadProposals = useCallback(async (page = proposalPage) => {
    const proposalData = await api.get<Proposal[] | PaginatedResponse<Proposal>>(
      `${ENDPOINTS.BATCH_PROPOSALS(batchId)}?page=${page}`,
    );
    const results = Array.isArray(proposalData) ? proposalData : (proposalData?.results || []);
    setProposals(results as unknown as Record<string, unknown>[]);
    setTotalProposals(
      Array.isArray(proposalData) ? results.length : (proposalData?.count ?? results.length),
    );
  }, [batchId, proposalPage]);

  useEffect(() => {
    async function load() {
      try {
        await loadBatchDetail();
      } catch {
        toast.error('Erro ao carregar lote');
        setLoading(false);
        return;
      }
      try {
        await loadProposals();
      } catch {
        toast.error('Erro ao carregar propostas do lote');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [batchId, proposalPage, loadBatchDetail, loadProposals]);

  // Update batch from WebSocket progress
  useEffect(() => {
    if (progress) {
      setBatch((prev) =>
        prev
          ? {
              ...prev,
              status: progress.status,
              processed_rows: Math.max(prev.processed_rows || 0, progress.processed_proposals || 0),
              errored_rows: Math.max(prev.errored_rows || 0, progress.error_proposals || 0),
              total_rows: Math.max(prev.total_rows || 0, progress.total_proposals || 0),
            }
          : prev,
      );

      if ((progress.status === 'completed' || progress.status === 'failed') && !finalSyncDoneRef.current) {
        finalSyncDoneRef.current = true;
        void loadBatchDetail();
        void loadProposals();
      }

      if (progress.status === 'processing') {
        finalSyncDoneRef.current = false;
      }
    }
  }, [progress, loadBatchDetail, loadProposals]);

  if (loading) return <PageSpinner />;
  if (!batch) return <div className="text-center py-12 text-gray-400">Lote não encontrado</div>;

  const progressPct = batch.total_rows > 0 ? (batch.processed_rows / batch.total_rows) * 100 : 0;

  const handleDeleteBatch = async () => {
    if (
      !window.confirm(
        'Tem certeza que deseja excluir este lote?\n\n' +
          'Serão removidos o lote, as propostas vinculadas, erros de importação ' +
          'e comissões que ainda não foram pagas. Lotes com propostas pagas não podem ser excluídos.',
      )
    ) {
      return;
    }

    setDeleting(true);
    try {
      const res = await api.delete<{
        detail?: string;
        deleted_proposals?: number;
        deleted_commissions?: number;
      }>(ENDPOINTS.BATCH_DETAIL(batchId));
      const proposals = res?.deleted_proposals ?? 0;
      const commissions = res?.deleted_commissions ?? 0;
      toast.success(
        res?.detail ||
          `Lote deletado (${proposals} proposta(s), ${commissions} comissão(ões) removidas).`,
      );
      setTimeout(() => (window.location.href = `${window.location.origin}/proposals/batches`), 1000);
    } catch (error: unknown) {
      toast.error(extractErrorMessage(error));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="animate-fadeIn">
      <div className="flex items-center gap-2 mb-4">
        <Button variant="ghost" size="sm" onClick={() => (window.location.href = `${window.location.origin}/proposals/batches`)}>
          <ArrowLeft size={16} />
        </Button>
        <h1 className="page-title">Lote de propostas</h1>
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
            <StatusBadge status={batch.status} />
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
        <div className="grid grid-cols-4 gap-4 mt-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg transition-all duration-300 hover:shadow-sm">
            <p className="text-2xl font-bold text-gray-900">{batch.total_rows}</p>
            <p className="text-xs text-gray-500">Total</p>
          </div>
          <div className="text-center p-3 bg-blue-50 rounded-lg transition-all duration-300 hover:shadow-sm">
            <p className="text-2xl font-bold text-blue-700">{batch.processed_rows}</p>
            <p className="text-xs text-gray-500">Processadas</p>
          </div>
          <div className="text-center p-3 bg-green-50 rounded-lg transition-all duration-300 hover:shadow-sm">
            <p className="text-2xl font-bold text-green-600">{batch.saved_count ?? Math.max(0, (batch.processed_rows || 0) - (batch.errored_rows || 0))}</p>
            <p className="text-xs text-gray-500">Gravadas</p>
          </div>
          <div className="text-center p-3 bg-red-50 rounded-lg transition-all duration-300 hover:shadow-sm">
            <p className="text-2xl font-bold text-red-600">{batch.errored_rows}</p>
            <p className="text-xs text-gray-500">Erros</p>
          </div>
        </div>

        {batch.error_summary && batch.error_summary.length > 0 && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="mb-2 text-sm font-semibold text-red-800">
              Motivo dos erros ({batch.errored_rows})
            </p>
            <ul className="max-h-48 space-y-1 overflow-y-auto text-xs text-red-800">
              {batch.error_summary.map((item, i) => (
                <li key={i}>
                  <strong>{item.count}×</strong> {item.error_message}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 mt-4">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              try {
                if (batch.original_file_url) {
                  const fullUrl = resolveFileUrl(batch.original_file_url);
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
            Baixar original
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              try {
                if (batch.log_url) {
                  const fullUrl = resolveFileUrl(batch.log_url);
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
            Baixar log
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={handleDeleteBatch}
            loading={deleting}
            disabled={deleting}
            className="text-red-600 hover:bg-red-50 transition-all duration-300"
            title="Excluir lote (não permitido se houver propostas pagas)"
          >
            <Trash2 size={14} />
            Excluir lote
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
            emptyMessage={
              (batch.saved_count ?? 0) > 0
                ? `${batch.saved_count} proposta(s) gravadas, mas a lista não carregou. Atualize a página.`
                : 'Nenhuma proposta neste lote'
            }
          />
        </div>
      )}
    </div>
  );
}
