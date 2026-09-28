import { useEffect, useState } from 'react';
import { Boxes, Search } from 'lucide-react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { formatDateTime } from '../../../../lib/utils/format';
import type { PaginatedResponse, ProposalBatch } from '../../../../lib/api/types';
import { PageHeader } from '../../ui/PageHeader';
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

export function BatchList() {
  const [batches, setBatches] = useState<ProposalBatch[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError('');
      try {
        const res = await api.get<PaginatedResponse<ProposalBatch> | ProposalBatch[]>(
          `${ENDPOINTS.BATCHES}?page_size=100`,
        );
        if (cancelled) return;
        setBatches(Array.isArray(res) ? res : res.results);
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
  }, []);

  const filtered = batches.filter((batch) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (batch.name || '').toLowerCase().includes(q) || (batch.bank_name || '').toLowerCase().includes(q);
  });

  return (
    <div>
      <PageHeader title="Lotes de importação" subtitle="Lotes que contêm propostas da sua hierarquia" />

      <div className="card">
        <div className="mb-4 relative max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar lote..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-200 py-1.5 pl-8 pr-3 text-sm outline-none focus:border-[var(--color-primary)]"
          />
        </div>

        {loading ? (
          <SectionSpinner />
        ) : error ? (
          <p className="py-6 text-center text-sm text-red-600">{error}</p>
        ) : filtered.length === 0 ? (
          <EmptyState icon={Boxes} title="Nenhum lote encontrado" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase text-[var(--color-text-muted)]">
                  <th className="py-2 pr-3">Banco</th>
                  <th className="py-2 pr-3">Layout</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Propostas</th>
                  <th className="py-2 pr-3">Data</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((batch) => (
                  <tr
                    key={batch.id}
                    onClick={() => (window.location.href = `/proposals/batches/${batch.id}`)}
                    className="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
                  >
                    <td className="py-2 pr-3">{batch.bank_name}</td>
                    <td className="py-2 pr-3">{batch.layout_name}</td>
                    <td className="py-2 pr-3">
                      <StatusBadge status={STATUS_LABELS[batch.status] || batch.status} />
                    </td>
                    <td className="py-2 pr-3">
                      <span className="text-emerald-600">{batch.processed_rows}</span> / {batch.total_rows}
                      {batch.errored_rows > 0 && (
                        <span className="ml-1 text-red-500">({batch.errored_rows} erros)</span>
                      )}
                    </td>
                    <td className="py-2 pr-3">{formatDateTime(batch.created_at)}</td>
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
