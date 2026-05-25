import { useState, useEffect } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { PageSpinner } from '../../ui/Spinner';
import { formatCurrency } from '../../../../lib/utils/format';
import { Button } from '../../ui/Button';
import toast from 'react-hot-toast';

interface MirrorEntry {
  proposal: string;
  contract_number: string;
  amount: string;
  commissions: Array<{
    role: string;
    role_display: string;
    user_name: string;
    percentage: string;
    value: string;
  }>;
}

export function CommissionMirror() {
  const [data, setData] = useState<MirrorEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get<MirrorEntry[]>(ENDPOINTS.COMMISSION_MIRROR);
        setData(Array.isArray(res) ? res : []);
      } catch {
        toast.error('Erro ao carregar espelho');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <PageSpinner />;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Espelho de Comissoes</h1>
      </div>

      {data.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center text-gray-400">
          Nenhum dado disponivel
        </div>
      ) : (
        <div className="space-y-4">
          {data.map((entry) => (
            <div key={entry.proposal} className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium text-gray-700">Contrato: {entry.contract_number}</span>
                  <span className="text-xs text-gray-400 ml-3">Valor: {formatCurrency(Number(entry.amount))}</span>
                </div>
              </div>
              <div className="divide-y divide-gray-50">
                {entry.commissions.map((c, i) => (
                  <div key={i} className="px-4 py-2 flex items-center justify-between text-sm">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-medium px-2 py-0.5 bg-gray-100 rounded-full">
                        {c.role_display}
                      </span>
                      <span className="text-gray-700">{c.user_name || 'Empresa'}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-gray-400">{c.percentage}%</span>
                      <span className="font-medium text-green-600">{formatCurrency(Number(c.value))}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
