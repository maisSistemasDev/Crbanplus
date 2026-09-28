import { Modal } from '../../ui/Modal';
import { Badge } from '../../ui/Badge';
import { formatCurrency, formatDate } from '../../../../lib/utils/format';
import type { CommissionRow } from '../../../../lib/api/types';

interface CommissionDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  items: CommissionRow[];
}

export function CommissionDetailModal({ isOpen, onClose, title, subtitle, items }: CommissionDetailModalProps) {
  const totals = items.reduce(
    (acc, item) => ({
      total: acc.total + Number(item.total_value || 0),
      debit: acc.debit + Number(item.debit_value || 0),
      net: acc.net + Number(item.net_value || 0),
    }),
    { total: 0, debit: 0, net: 0 },
  );

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="xl" scrollBody>
      {subtitle && <p className="mb-3 text-sm text-gray-500">{subtitle}</p>}

      {items.length === 0 ? (
        <p className="text-sm text-gray-500">Nenhuma proposta encontrada.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs uppercase text-gray-500">
                <th className="py-2 pr-3">Proposta</th>
                <th className="py-2 pr-3">Cliente</th>
                <th className="py-2 pr-3">CPF</th>
                <th className="py-2 pr-3">Banco</th>
                <th className="py-2 pr-3">Tabela</th>
                <th className="py-2 pr-3">Tipo</th>
                <th className="py-2 pr-3 text-right">%</th>
                <th className="py-2 pr-3 text-right">Comissão</th>
                <th className="py-2 pr-3 text-right">Débito</th>
                <th className="py-2 text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-gray-100">
                  <td className="py-2 pr-3">
                    <div className="font-mono text-xs">{item.contract_number || '-'}</div>
                    <div className="text-xs text-gray-400">{formatDate(item.created_at)}</div>
                  </td>
                  <td className="py-2 pr-3">{item.client_name || '-'}</td>
                  <td className="py-2 pr-3 font-mono text-xs">{item.client_document || '-'}</td>
                  <td className="py-2 pr-3">{item.bank_name || '-'}</td>
                  <td className="py-2 pr-3">{item.table_name || '-'}</td>
                  <td className="py-2 pr-3">{item.role_display || '-'}</td>
                  <td className="py-2 pr-3 text-right">{Number(item.percentage || 0).toFixed(2)}%</td>
                  <td className="py-2 pr-3 text-right">{formatCurrency(Number(item.total_value || 0))}</td>
                  <td className="py-2 pr-3 text-right text-red-600">
                    {Number(item.debit_value || 0) > 0 ? `- ${formatCurrency(Number(item.debit_value))}` : '-'}
                  </td>
                  <td className="py-2 text-right font-medium">
                    {item.is_zeroed ? (
                      <Badge variant="warning">Zerado</Badge>
                    ) : (
                      <span className="text-green-600">{formatCurrency(Number(item.net_value || 0))}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="font-medium">
                <td className="py-2 pr-3" colSpan={7}>
                  {items.length} proposta(s)
                </td>
                <td className="py-2 pr-3 text-right">{formatCurrency(totals.total)}</td>
                <td className="py-2 pr-3 text-right text-red-600">
                  {totals.debit > 0 ? `- ${formatCurrency(totals.debit)}` : '-'}
                </td>
                <td className="py-2 text-right text-green-600">{formatCurrency(totals.net)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </Modal>
  );
}
