import { useEffect, useState } from 'react';
import { Modal } from '../../ui/Modal';
import { Badge } from '../../ui/Badge';
import { Spinner } from '../../ui/Spinner';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { formatCurrency, formatDate } from '../../../../lib/utils/format';
import type { DebitDetailResponse } from '../../../../lib/api/types';

interface DebitDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  commissionIds: number[];
  title?: string;
}

const ORIGIN_LABEL: Record<string, string> = {
  manual: 'Manual',
  sinistro: 'Sinistro',
};

export function DebitDetailModal({ isOpen, onClose, commissionIds, title }: DebitDetailModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState<DebitDetailResponse | null>(null);

  useEffect(() => {
    if (!isOpen || commissionIds.length === 0) return;

    let cancelled = false;
    setLoading(true);
    setError('');

    api
      .post<DebitDetailResponse>(ENDPOINTS.COMMISSION_DEBIT_DETAIL, { commission_ids: commissionIds })
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch(() => {
        if (!cancelled) setError('Não foi possível carregar os débitos.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen, commissionIds]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title || 'Débitos abatidos'} size="xl" scrollBody>
      {loading && (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      )}

      {!loading && error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && data && (
        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-3">
            <span className="text-sm text-gray-600">Total descontado neste recorte</span>
            <span className="text-lg font-semibold text-red-600">{formatCurrency(Number(data.total || 0))}</span>
          </div>

          {data.results.length === 0 ? (
            <p className="text-sm text-gray-500">Nenhum débito incide sobre estas comissões.</p>
          ) : (
            data.results.map((debit) => (
              <div key={debit.debit_id} className="rounded-lg border border-gray-200 p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-gray-900">{debit.reason}</p>
                    <p className="text-xs text-gray-500">
                      {debit.owner_name} · lançado em {formatDate(debit.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={debit.origin === 'sinistro' ? 'error' : 'default'}>
                      {ORIGIN_LABEL[debit.origin] || debit.origin}
                    </Badge>
                    {debit.projected && <Badge variant="warning">A abater</Badge>}
                  </div>
                </div>

                <div className="mt-3 grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-gray-500">Valor do débito</p>
                    <p className="font-medium">{formatCurrency(Number(debit.debit_amount || 0))}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Saldo pendente</p>
                    <p className="font-medium">{formatCurrency(Number(debit.remaining_amount || 0))}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Descontado aqui</p>
                    <p className="font-medium text-red-600">{formatCurrency(Number(debit.amount || 0))}</p>
                  </div>
                </div>

                {debit.commissions.length > 0 && (
                  <table className="mt-3 w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 text-left text-xs uppercase text-gray-500">
                        <th className="py-1 pr-3">Proposta</th>
                        <th className="py-1 pr-3">Cliente</th>
                        <th className="py-1 text-right">Valor</th>
                      </tr>
                    </thead>
                    <tbody>
                      {debit.commissions.map((item, index) => (
                        <tr key={`${item.commission_id}-${index}`} className="border-b border-gray-50">
                          <td className="py-1 pr-3 font-mono text-xs">{item.contract_number || '-'}</td>
                          <td className="py-1 pr-3">{item.client_name || '-'}</td>
                          <td className="py-1 text-right">{formatCurrency(Number(item.amount || 0))}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </Modal>
  );
}
