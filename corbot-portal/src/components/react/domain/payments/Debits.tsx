import { useCallback, useEffect, useState } from 'react';
import { X } from 'lucide-react';
import toast from 'react-hot-toast';

import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { formatCurrency, formatDate, formatDateTime } from '../../../../lib/utils/format';
import type { PaginatedResponse, PortalDebit, PortalDebitDetail } from '../../../../lib/api/types';
import { PageHeader } from '../../ui/PageHeader';
import { EmptyState } from '../../ui/EmptyState';
import { SectionSpinner } from '../../ui/Spinner';
import { Badge } from '../../ui/Badge';
import { Button } from '../../ui/Button';

const ORIGIN_LABEL: Record<string, string> = {
  manual: 'Manual',
  sinistro: 'Sinistro',
};

export function Debits() {
  const [debits, setDebits] = useState<PortalDebit[]>([]);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState<PortalDebitDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const loadDebits = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page_size: '100' });
      const response = await api.get<PaginatedResponse<PortalDebit> | PortalDebit[]>(
        `${ENDPOINTS.DEBITS}?${params.toString()}`,
      );
      setDebits(Array.isArray(response) ? response : response.results);
    } catch (error) {
      toast.error(extractErrorMessage(error));
      setDebits([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDebits();
  }, [loadDebits]);

  async function openDetail(debit: PortalDebit) {
    setLoadingDetail(true);
    try {
      const response = await api.get<PortalDebitDetail>(ENDPOINTS.DEBIT_DETAIL(debit.id));
      setDetail(response);
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setLoadingDetail(false);
    }
  }

  const pendingTotal = debits
    .filter((debit) => debit.is_active)
    .reduce((acc, debit) => acc + Number(debit.remaining_amount || 0), 0);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Débitos"
        subtitle="Valores a descontar das próximas comissões liberadas"
      />

      <section className="rounded-md border border-gray-200 bg-white p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-xs text-gray-500">Saldo pendente</p>
            <p className="text-2xl font-semibold text-red-600">{formatCurrency(pendingTotal)}</p>
          </div>
          <Button variant="secondary" onClick={() => void loadDebits()}>
            Atualizar
          </Button>
        </div>

        {loading ? (
          <SectionSpinner />
        ) : debits.length === 0 ? (
          <EmptyState title="Nenhum débito" description="Você não possui débitos lançados." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs uppercase text-gray-500">
                  <th className="py-2 pr-3">Motivo</th>
                  <th className="py-2 pr-3">Origem</th>
                  <th className="py-2 pr-3">Dono</th>
                  <th className="py-2 pr-3 text-right">Valor</th>
                  <th className="py-2 pr-3 text-right">Saldo</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Lançado em</th>
                  <th className="py-2 text-right">Detalhes</th>
                </tr>
              </thead>
              <tbody>
                {debits.map((debit) => (
                  <tr key={debit.id} className="border-b border-gray-50">
                    <td className="py-2 pr-3 text-gray-800">{debit.reason}</td>
                    <td className="py-2 pr-3">
                      <Badge tone={debit.origin === 'sinistro' ? 'error' : 'gray'}>
                        {ORIGIN_LABEL[debit.origin] || debit.origin}
                      </Badge>
                    </td>
                    <td className="py-2 pr-3 text-gray-600">{debit.owner_name || '-'}</td>
                    <td className="py-2 pr-3 text-right text-gray-800">
                      {formatCurrency(Number(debit.amount))}
                    </td>
                    <td
                      className={`py-2 pr-3 text-right font-semibold ${
                        Number(debit.remaining_amount) > 0 ? 'text-red-600' : 'text-emerald-600'
                      }`}
                    >
                      {formatCurrency(Number(debit.remaining_amount))}
                    </td>
                    <td className="py-2 pr-3">
                      <Badge tone={debit.is_active ? 'warning' : 'success'}>
                        {debit.is_active ? 'Pendente' : 'Quitado'}
                      </Badge>
                    </td>
                    <td className="py-2 pr-3 text-gray-500">{formatDateTime(debit.created_at)}</td>
                    <td className="py-2 text-right">
                      <button
                        type="button"
                        onClick={() => void openDetail(debit)}
                        disabled={loadingDetail}
                        className="rounded px-2 py-1 text-xs font-medium text-[#1e242f] underline decoration-dotted disabled:opacity-50"
                      >
                        Ver detalhes
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {detail && (
        <div className="fixed inset-0 z-50 bg-black/35 p-4">
          <div className="mx-auto max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-md bg-white shadow-xl">
            <div className="flex items-center justify-between bg-[#1e242f] px-4 py-3 text-white">
              <h2 className="text-lg font-semibold">Detalhes do débito</h2>
              <button type="button" onClick={() => setDetail(null)} aria-label="Fechar">
                <X size={18} />
              </button>
            </div>

            <div className="space-y-5 p-4">
              <div>
                <p className="text-base font-medium text-gray-900">{detail.reason}</p>
                <p className="text-xs text-gray-500">
                  {ORIGIN_LABEL[detail.origin] || detail.origin} · lançado em{' '}
                  {formatDateTime(detail.created_at)}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                <div className="rounded border border-gray-200 p-3">
                  <p className="text-xs text-gray-500">Valor do débito</p>
                  <p className="font-semibold">{formatCurrency(Number(detail.amount))}</p>
                </div>
                <div className="rounded border border-gray-200 p-3">
                  <p className="text-xs text-gray-500">Saldo pendente</p>
                  <p className="font-semibold text-red-600">
                    {formatCurrency(Number(detail.remaining_amount))}
                  </p>
                </div>
                <div className="rounded border border-gray-200 p-3">
                  <p className="text-xs text-gray-500">Dono</p>
                  <p className="font-semibold">{detail.owner_name || '-'}</p>
                </div>
              </div>

              <div>
                <h3 className="mb-2 text-sm font-semibold text-gray-800">Propostas de origem</h3>
                {detail.origin_claims.length === 0 ? (
                  <p className="text-sm text-gray-500">
                    Débito lançado manualmente, sem proposta de origem.
                  </p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 text-left text-xs uppercase text-gray-500">
                        <th className="py-1 pr-3">Proposta</th>
                        <th className="py-1 pr-3">Cliente</th>
                        <th className="py-1 pr-3">Motivo</th>
                        <th className="py-1 text-right">Valor</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.origin_claims.map((claim) => (
                        <tr key={claim.claim_id} className="border-b border-gray-50">
                          <td className="py-1 pr-3 font-mono text-xs">
                            {claim.contract_number || '-'}
                            <span className="block text-[11px] text-gray-400">
                              {formatDate(claim.created_at)}
                            </span>
                          </td>
                          <td className="py-1 pr-3">
                            {claim.client_name || '-'}
                            <span className="block text-[11px] text-gray-400">
                              {claim.client_document || ''}
                            </span>
                          </td>
                          <td className="py-1 pr-3">{claim.claim_type_display}</td>
                          <td className="py-1 text-right">{formatCurrency(Number(claim.amount))}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              <div>
                <h3 className="mb-2 text-sm font-semibold text-gray-800">Descontos já aplicados</h3>
                {detail.applications.length === 0 ? (
                  <p className="text-sm text-gray-500">
                    Nenhum desconto aplicado ainda. O valor será abatido nas próximas comissões liberadas.
                  </p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 text-left text-xs uppercase text-gray-500">
                        <th className="py-1 pr-3">Proposta</th>
                        <th className="py-1 pr-3">Cliente</th>
                        <th className="py-1 pr-3">Comissão</th>
                        <th className="py-1 text-right">Descontado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.applications.map((application) => (
                        <tr key={application.commission_id} className="border-b border-gray-50">
                          <td className="py-1 pr-3 font-mono text-xs">
                            {application.contract_number || '-'}
                            <span className="block text-[11px] text-gray-400">
                              {formatDate(application.created_at)}
                            </span>
                          </td>
                          <td className="py-1 pr-3">{application.client_name || '-'}</td>
                          <td className="py-1 pr-3">{application.role_display}</td>
                          <td className="py-1 text-right text-red-600">
                            {formatCurrency(Number(application.amount))}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
