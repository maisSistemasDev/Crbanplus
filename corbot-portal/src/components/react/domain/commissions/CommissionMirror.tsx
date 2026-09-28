import { useEffect, useState } from 'react';
import { FileSearch } from 'lucide-react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { formatCurrency, formatPercent } from '../../../../lib/utils/format';
import type { Commission, Proposal } from '../../../../lib/api/types';
import { PageHeader } from '../../ui/PageHeader';
import { EmptyState } from '../../ui/EmptyState';
import { SectionSpinner } from '../../ui/Spinner';

interface MirrorEntry {
  proposal: Proposal;
  commissions: Commission[];
  company_name: string | null;
  seller_name: string | null;
  leader_name: string | null;
  seller_commissions: Commission[];
  leader_commissions: Commission[];
  company_commissions: Commission[];
}

interface MirrorResponse {
  espelho_comissoes: MirrorEntry[];
  total_registros: number;
  gerado_em: string;
  usuario: string;
}

function sum(list: Commission[]): number {
  return list.reduce((acc, c) => acc + Number(c.value || 0), 0);
}

export function CommissionMirror() {
  const [data, setData] = useState<MirrorResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const ids = params.get('ids');

    if (!ids) {
      setLoading(false);
      return;
    }

    api
      .post<MirrorResponse>(ENDPOINTS.COMMISSION_MIRROR, {
        commission_ids: ids.split(',').filter(Boolean),
        download: false,
      })
      .then(setData)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <PageHeader title="Espelho por proposta" subtitle="Detalhamento das comissões agrupadas por proposta." />

      {loading ? (
        <SectionSpinner />
      ) : error ? (
        <div className="card text-sm text-red-600">{error}</div>
      ) : !data || data.espelho_comissoes.length === 0 ? (
        <EmptyState
          icon={FileSearch}
          title="Nenhum espelho para exibir"
          description="Volte para o extrato de comissões e selecione uma ou mais comissões para ver o espelho por proposta."
        />
      ) : (
        <div className="space-y-4">
          {data.espelho_comissoes.map((entry) => (
            <div key={entry.proposal.id} className="card">
              <div className="mb-3 flex flex-wrap items-start justify-between gap-2 border-b border-[var(--color-border)] pb-3">
                <div>
                  <p className="text-sm font-semibold text-[var(--color-text)]">
                    {entry.proposal.client_name || 'Cliente não identificado'}
                  </p>
                  <p className="text-xs text-[var(--color-text-muted)]">
                    Contrato {entry.proposal.contract_number} · {entry.proposal.bank_details?.name ?? '—'} ·{' '}
                    {entry.proposal.table_details?.name_in_bank ?? '—'}
                  </p>
                </div>
                <p className="text-sm font-semibold text-[var(--color-text)]">
                  Valor da operação: {formatCurrency(entry.proposal.amount)}
                </p>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <MirrorColumn
                  label="Vendedor"
                  name={entry.seller_name}
                  commissions={entry.seller_commissions}
                />
                <MirrorColumn label="Líder" name={entry.leader_name} commissions={entry.leader_commissions} />
                <MirrorColumn
                  label="Empresa"
                  name={entry.company_name}
                  commissions={entry.company_commissions}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MirrorColumn({
  label,
  name,
  commissions,
}: {
  label: string;
  name: string | null;
  commissions: Commission[];
}) {
  if (commissions.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-[var(--color-border)] p-3 text-xs text-[var(--color-text-muted)]">
        {label}: sem comissão
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-[var(--color-border)] p-3">
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-muted)]">{label}</p>
      <p className="mt-1 text-sm font-medium text-[var(--color-text)]">{name ?? '—'}</p>
      <p className="mt-1 text-lg font-bold text-emerald-600">{formatCurrency(sum(commissions))}</p>
      <p className="text-xs text-[var(--color-text-muted)]">
        {formatPercent(commissions[0]?.percentage ?? 0)} de comissão
      </p>
    </div>
  );
}
