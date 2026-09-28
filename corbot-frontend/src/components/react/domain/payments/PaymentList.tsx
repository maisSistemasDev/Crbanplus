import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { DataTable } from '../../ui/DataTable';
import { PageHeader } from '../../ui/PageHeader';
import { Badge } from '../../ui/Badge';
import { Button } from '../../ui/Button';
import { Modal } from '../../ui/Modal';
import { SearchSelect } from '../../ui/SearchSelect';
import { formatCurrency, formatDate, formatCPF } from '../../../../lib/utils/format';
import type { Commission, Payment, PaginatedResponse } from '../../../../lib/api/types';
import type { Column } from '../../ui/DataTable';
import { FileText, Search } from 'lucide-react';
import toast from 'react-hot-toast';

const STATUS_MAP: Record<string, { label: string; variant: 'default' | 'success' | 'warning' | 'error' | 'info' }> = {
  pending: { label: 'Pendente', variant: 'warning' },
  approved: { label: 'Aprovado', variant: 'info' },
  paid: { label: 'Pago', variant: 'success' },
  rejected: { label: 'Rejeitado', variant: 'error' },
};

const STATUS_FILTER_OPTIONS = [
  { value: 'pending', label: 'Pendente' },
  { value: 'approved', label: 'Aprovado' },
  { value: 'paid', label: 'Pago' },
  { value: 'rejected', label: 'Rejeitado' },
];

const columns: Column<Record<string, unknown>>[] = [
  {
    key: 'user_details',
    header: 'Usuario',
    render: (item) => {
      const d = item.user_details as Record<string, unknown> | null;
      return d ? (
        <div>
          <p className="font-medium text-gray-900">{d.first_name} {d.last_name}</p>
          <p className="text-xs text-gray-400">{formatCPF(d.cpf as string)}</p>
        </div>
      ) : '-';
    },
  },
  {
    key: 'total_amount',
    header: 'Valor',
    sortable: true,
    render: (item) => (
      <span className="font-medium text-green-600">{formatCurrency(Number(item.total_amount))}</span>
    ),
  },
  {
    key: 'status',
    header: 'Status',
    render: (item) => {
      const s = STATUS_MAP[item.status as string] || { label: item.status, variant: 'default' as const };
      return <Badge variant={s.variant}>{s.label}</Badge>;
    },
  },
  { key: 'payment_method', header: 'Metodo' },
  {
    key: 'created_at',
    header: 'Data',
    sortable: true,
    render: (item) => formatDate(item.created_at as string),
  },
];

export function PaymentList() {
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [receiptPayment, setReceiptPayment] = useState<Record<string, unknown> | null>(null);
  const [receiptCommissions, setReceiptCommissions] = useState<Commission[]>([]);
  const [loadingReceipt, setLoadingReceipt] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(currentPage) });
      if (search) params.set('search', search);
      if (statusFilter) params.set('status', statusFilter);
      const res = await api.get<PaginatedResponse<Payment> | Payment[]>(`${ENDPOINTS.PAYMENTS}?${params}`);
      if (Array.isArray(res)) {
        setData(res as unknown as Record<string, unknown>[]);
        setTotalItems(res.length);
      } else {
        setData(res.results as unknown as Record<string, unknown>[]);
        setTotalItems(res.count);
      }
    } catch {
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [currentPage, search, statusFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function openReceipt(item: Record<string, unknown>) {
    setReceiptPayment(item);
    setLoadingReceipt(true);
    try {
      const query = new URLSearchParams({ payment_id: String(item.id) });
      const commissions = await api.get<Commission[]>(`${ENDPOINTS.COMMISSIONS}?${query}`);
      setReceiptCommissions(Array.isArray(commissions) ? commissions : []);
    } catch (error) {
      toast.error(extractErrorMessage(error));
      setReceiptCommissions([]);
    } finally {
      setLoadingReceipt(false);
    }
  }

  function printReceipt() {
    window.print();
  }

  return (
    <div>
      <PageHeader title="Pagamentos" />

      <div className="flex gap-3 mb-4">
        <div className="relative max-w-sm flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
          />
        </div>
        <SearchSelect
          className="w-full sm:w-52"
          placeholder="Todos os status"
          allowEmpty
          value={statusFilter}
          options={STATUS_FILTER_OPTIONS}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setCurrentPage(1);
          }}
        />
      </div>

      <DataTable
        columns={columns}
        data={data}
        loading={loading}
        totalItems={totalItems}
        currentPage={currentPage}
        onPageChange={setCurrentPage}
        keyExtractor={(item) => String(item.id)}
        emptyMessage="Nenhum pagamento encontrado"
        rowActions={(item) => (
          <Button size="sm" variant="secondary" onClick={() => openReceipt(item)}>
            <FileText size={14} />
            2ª via
          </Button>
        )}
      />

      <Modal
        isOpen={!!receiptPayment}
        onClose={() => {
          setReceiptPayment(null);
          setReceiptCommissions([]);
        }}
        title="2ª via do comprovante"
        size="lg"
        scrollBody
      >
        {loadingReceipt ? (
          <p className="text-sm text-gray-500">Carregando comprovante...</p>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">
              Pagamento #{String(receiptPayment?.id ?? '')} ·{' '}
              {formatCurrency(Number(receiptPayment?.total_amount || 0))}
            </p>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-500 border-b">
                  <th className="text-left py-1">Proposta</th>
                  <th className="text-left py-1">Cliente</th>
                  <th className="text-left py-1">Comissão</th>
                </tr>
              </thead>
              <tbody>
                {receiptCommissions.map((c) => (
                  <tr key={c.id} className="border-b border-gray-50">
                    <td className="py-1">{c.proposal_details?.contract_number ?? c.proposal}</td>
                    <td className="py-1">{c.proposal_details?.client_name ?? '—'}</td>
                    <td className="py-1">{formatCurrency(Number(c.value || 0))}</td>
                  </tr>
                ))}
                {receiptCommissions.length === 0 && (
                  <tr>
                    <td colSpan={3} className="py-2 text-xs text-gray-400">
                      Nenhuma comissão vinculada.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            <div className="flex justify-end">
              <Button size="sm" onClick={printReceipt}>
                Imprimir
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
