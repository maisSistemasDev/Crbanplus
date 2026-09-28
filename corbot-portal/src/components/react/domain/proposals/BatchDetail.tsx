import { useEffect, useState } from 'react';
import { ArrowLeft, FileText } from 'lucide-react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { formatCurrency, formatDateTime } from '../../../../lib/utils/format';
import type { Proposal, ProposalBatch } from '../../../../lib/api/types';
import { Button } from '../../ui/Button';
import { StatusBadge } from '../../ui/Badge';
import { EmptyState } from '../../ui/EmptyState';
import { SectionSpinner } from '../../ui/Spinner';

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pendente',
  processing: 'Processando',
  completed: 'Concluído',
  failed: 'Falhou',
  partial: 'Parcial',
};

interface BatchDetailProps {
  batchId: string;
}

export function BatchDetail({ batchId }: BatchDetailProps) {
  const [batch, setBatch] = useState<ProposalBatch | null>(null);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError('');
      try {
        const [batchData, proposalsData] = await Promise.all([
          api.get<ProposalBatch>(ENDPOINTS.BATCH_DETAIL(batchId)),
          api.get<Proposal[]>(ENDPOINTS.BATCH_PROPOSALS(batchId)),
        ]);
        if (cancelled) return;
        setBatch(batchData);
        setProposals(proposalsData);
      } catch (err) {
        if (!cancelled) setError(extractErrorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [batchId]);

  if (loading) return <SectionSpinner />;
  if (error) return <div className="card text-sm text-red-600">{error}</div>;
  if (!batch) return null;

  return (
    <div>
      <div className="mb-4 flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={() => (window.location.href = '/proposals/batches')}>
          <ArrowLeft size={16} />
        </Button>
        <h1 className="page-title">Lote de propostas</h1>
      </div>

      <div className="card mb-5">
        <div className="mb-4 grid grid-cols-2 gap-4 md:grid-cols-4">
          <div>
            <p className="text-xs text-[var(--color-text-muted)]">Banco</p>
            <p className="font-medium text-[var(--color-text)]">{batch.bank_name}</p>
          </div>
          <div>
            <p className="text-xs text-[var(--color-text-muted)]">Layout</p>
            <p className="font-medium text-[var(--color-text)]">{batch.layout_name}</p>
          </div>
          <div>
            <p className="text-xs text-[var(--color-text-muted)]">Data</p>
            <p className="font-medium text-[var(--color-text)]">{formatDateTime(batch.created_at)}</p>
          </div>
          <div>
            <p className="text-xs text-[var(--color-text-muted)]">Status</p>
            <StatusBadge status={STATUS_LABELS[batch.status] || batch.status} />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="rounded-lg bg-gray-50 p-3 text-center">
            <p className="text-2xl font-bold text-[var(--color-text)]">{batch.total_rows}</p>
            <p className="text-xs text-[var(--color-text-muted)]">Total</p>
          </div>
          <div className="rounded-lg bg-emerald-50 p-3 text-center">
            <p className="text-2xl font-bold text-emerald-600">{batch.processed_rows}</p>
            <p className="text-xs text-[var(--color-text-muted)]">Processadas</p>
          </div>
          <div className="rounded-lg bg-red-50 p-3 text-center">
            <p className="text-2xl font-bold text-red-600">{batch.errored_rows}</p>
            <p className="text-xs text-[var(--color-text-muted)]">Erros</p>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="section-title mb-3">Propostas do lote (visíveis para você)</h2>
        {proposals.length === 0 ? (
          <EmptyState icon={FileText} title="Nenhuma proposta visível neste lote" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase text-[var(--color-text-muted)]">
                  <th className="py-2 pr-3">Contrato</th>
                  <th className="py-2 pr-3">Cliente</th>
                  <th className="py-2 pr-3">Vendedor</th>
                  <th className="py-2 pr-3">Valor</th>
                  <th className="py-2 pr-3">Comissão</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Status Pagamento</th>
                </tr>
              </thead>
              <tbody>
                {proposals.map((proposal) => (
                  <tr key={proposal.id} className="border-b border-gray-100">
                    <td className="py-2 pr-3 font-mono text-xs">{proposal.contract_number}</td>
                    <td className="py-2 pr-3">
                      <p className="font-medium text-[var(--color-text)]">{proposal.client_name || '—'}</p>
                      <p className="text-xs text-[var(--color-text-muted)]">{proposal.client_document}</p>
                    </td>
                    <td className="py-2 pr-3">
                      {proposal.seller_details
                        ? `${proposal.seller_details.first_name} ${proposal.seller_details.last_name}`
                        : '—'}
                    </td>
                    <td className="py-2 pr-3 font-medium text-emerald-600">{formatCurrency(proposal.amount)}</td>
                    <td className="py-2 pr-3 font-medium text-emerald-700">
                      {proposal.commission_value == null ? '—' : formatCurrency(proposal.commission_value)}
                    </td>
                    <td className="py-2 pr-3">
                      <StatusBadge status="processed" />
                    </td>
                    <td className="py-2 pr-3">
                      <StatusBadge status={proposal.payment_status || proposal.status || 'pending'} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
