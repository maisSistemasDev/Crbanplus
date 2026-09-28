import { useEffect, useMemo, useState } from 'react';
import { HandCoins } from 'lucide-react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { formatCurrency, formatDateTime, formatPercent } from '../../../../lib/utils/format';
import type { Commission } from '../../../../lib/api/types';
import { PageHeader } from '../../ui/PageHeader';
import { StatusBadge } from '../../ui/Badge';
import { Button } from '../../ui/Button';
import { EmptyState } from '../../ui/EmptyState';
import { SectionSpinner } from '../../ui/Spinner';
import { SearchSelect } from '../../ui/SearchSelect';

const RELEASE_STATUS_LABELS: Record<string, string> = {
  not_released: 'Não liberado',
  withdraw_available: 'Saque liberado',
  pending_manual_payment: 'Aguardando pagamento',
  paid: 'Pago',
  sinistro: 'Sinistro',
};

const statusOptions = Object.entries(RELEASE_STATUS_LABELS).map(([value, label]) => ({ value, label }));

const ROLE_LABELS: Record<string, string> = {
  vendedor: 'Vendedor',
  lider: 'Líder',
  empresa: 'Empresa',
};

export function CommissionList() {
  const [commissions, setCommissions] = useState<Commission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function load() {
    setLoading(true);
    setError('');
    api
      .get<Commission[]>(ENDPOINTS.COMMISSIONS)
      .then(setCommissions)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }

  const filtered = useMemo(() => {
    if (!statusFilter) return commissions;
    return commissions.filter((c) => c.release_status === statusFilter);
  }, [commissions, statusFilter]);

  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function openMirror() {
    if (selected.size === 0) return;
    const ids = Array.from(selected).join(',');
    window.location.href = `/commissions/mirror?ids=${ids}`;
  }

  return (
    <div>
      <PageHeader
        title="Comissões"
        subtitle="Extrato de comissões geradas para você e sua equipe."
        actions={
          <Button variant="secondary" size="sm" disabled={selected.size === 0} onClick={openMirror}>
            Ver espelho ({selected.size})
          </Button>
        }
      />

      <div className="card">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <SearchSelect
            className="w-56"
            placeholder="Todos os status"
            allowEmpty
            value={statusFilter}
            options={statusOptions}
            onChange={setStatusFilter}
          />
        </div>

        {loading ? (
          <SectionSpinner />
        ) : error ? (
          <p className="text-sm text-red-600">{error}</p>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={HandCoins}
            title="Nenhuma comissão encontrada"
            description="Ainda não há comissões registradas para o período/status selecionado."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase text-[var(--color-text-muted)]">
                  <th className="w-8 py-2"></th>
                  <th className="py-2 pr-3">Proposta</th>
                  <th className="py-2 pr-3">Função</th>
                  <th className="py-2 pr-3">%</th>
                  <th className="py-2 pr-3">Valor</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Data</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((commission) => (
                  <tr key={commission.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-2">
                      <input
                        type="checkbox"
                        checked={selected.has(commission.id)}
                        onChange={() => toggleSelect(commission.id)}
                      />
                    </td>
                    <td className="py-2 pr-3 font-mono text-xs text-[var(--color-text-muted)]">
                      {String(commission.proposal).slice(0, 8)}
                    </td>
                    <td className="py-2 pr-3">{ROLE_LABELS[commission.role] ?? commission.role_display}</td>
                    <td className="py-2 pr-3">{formatPercent(commission.percentage)}</td>
                    <td className="py-2 pr-3 font-medium text-emerald-700">{formatCurrency(commission.value)}</td>
                    <td className="py-2 pr-3">
                      <StatusBadge
                        status={commission.release_status}
                        label={RELEASE_STATUS_LABELS[commission.release_status] ?? commission.release_status}
                      />
                    </td>
                    <td className="py-2 pr-3 text-[var(--color-text-muted)]">{formatDateTime(commission.created_at)}</td>
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
