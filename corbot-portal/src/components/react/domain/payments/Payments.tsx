import { useEffect, useMemo, useState } from 'react';
import { useStore } from '@nanostores/react';
import { Landmark, X } from 'lucide-react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { formatCPF, formatCurrency, formatDate, formatDateTime, formatPercent } from '../../../../lib/utils/format';
import { $currentUser } from '../../../../lib/stores/auth';
import type { Commission, Payment } from '../../../../lib/api/types';
import { PageHeader } from '../../ui/PageHeader';
import { EmptyState } from '../../ui/EmptyState';
import { SectionSpinner } from '../../ui/Spinner';
import { StatusBadge } from '../../ui/Badge';
import { Button } from '../../ui/Button';
import { SearchSelect } from '../../ui/SearchSelect';

const METHOD_LABELS: Record<string, string> = {
  manual: 'Manual',
  withdraw: 'Saque',
};

const MONTH_OPTIONS = [
  { value: '1', label: 'Janeiro' },
  { value: '2', label: 'Fevereiro' },
  { value: '3', label: 'Março' },
  { value: '4', label: 'Abril' },
  { value: '5', label: 'Maio' },
  { value: '6', label: 'Junho' },
  { value: '7', label: 'Julho' },
  { value: '8', label: 'Agosto' },
  { value: '9', label: 'Setembro' },
  { value: '10', label: 'Outubro' },
  { value: '11', label: 'Novembro' },
  { value: '12', label: 'Dezembro' },
];

function yearsAroundNow(): number[] {
  const current = new Date().getFullYear();
  return [current - 2, current - 1, current, current + 1];
}

const yearOptions = yearsAroundNow().map((year) => ({ value: String(year), label: String(year) }));

function getPaymentReferenceDate(payment: Payment): Date | null {
  const raw = payment.paid_at || payment.approved_at || payment.created_at;
  if (!raw) return null;
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return null;
  return date;
}

function includesPeriod(date: Date | null, beginDate: string, endDate: string): boolean {
  if (!date || !beginDate || !endDate) return false;
  const begin = new Date(`${beginDate}T00:00:00`);
  const end = new Date(`${endDate}T23:59:59`);
  if (Number.isNaN(begin.getTime()) || Number.isNaN(end.getTime())) return false;
  return date >= begin && date <= end;
}

function buildCsv(commissions: Commission[]): string {
  const headers = ['Proposta', 'Data', 'Cliente', 'Produto', 'Valor', 'Percentual', 'Comissao'];
  const lines = commissions.map((commission) => {
    const proposal = commission.proposal_details;
    return [
      proposal?.contract_number ?? String(commission.proposal),
      proposal?.disbursement_date ? formatDate(proposal.disbursement_date) : '',
      proposal?.client_name ?? '',
      proposal?.table_details?.name_in_bank ?? '',
      String(proposal?.amount ?? '0'),
      String(commission.percentage ?? '0'),
      String(commission.value ?? '0'),
    ];
  });

  return [headers, ...lines]
    .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(';'))
    .join('\n');
}

function downloadTextFile(content: string, filename: string, type = 'text/csv;charset=utf-8;'): void {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function Payments() {
  const user = useStore($currentUser);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [month, setMonth] = useState(String(new Date().getMonth() + 1));
  const [year, setYear] = useState(String(new Date().getFullYear()));
  const [beginDate, setBeginDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [appliedFilters, setAppliedFilters] = useState({
    month: String(new Date().getMonth() + 1),
    year: String(new Date().getFullYear()),
    beginDate: '',
    endDate: '',
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedPayment, setSelectedPayment] = useState<Payment | null>(null);
  const [paymentCommissions, setPaymentCommissions] = useState<Commission[]>([]);
  const [loadingCommissions, setLoadingCommissions] = useState(false);
  const [receiptError, setReceiptError] = useState('');

  useEffect(() => {
    if (!user) return;
    if (user.role !== 'empresa_admin' && user.role !== 'gerente') {
      window.location.href = '/dashboard';
      return;
    }
    api
      .get<Payment[]>(ENDPOINTS.PAYMENTS)
      .then(setPayments)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [user]);

  const filteredPayments = useMemo(() => {
    return payments.filter((payment) => {
      const refDate = getPaymentReferenceDate(payment);
      if (!refDate) return false;

      if (appliedFilters.beginDate && appliedFilters.endDate) {
        return includesPeriod(refDate, appliedFilters.beginDate, appliedFilters.endDate);
      }

      return (
        refDate.getFullYear() === Number(appliedFilters.year) &&
        refDate.getMonth() + 1 === Number(appliedFilters.month)
      );
    });
  }, [payments, appliedFilters]);

  async function emitReceipt(payment: Payment) {
    setSelectedPayment(payment);
    setLoadingCommissions(true);
    setReceiptError('');

    try {
      const query = new URLSearchParams({ payment_id: String(payment.id) });
      const commissions = await api.get<Commission[]>(`${ENDPOINTS.COMMISSIONS}?${query}`);
      setPaymentCommissions(Array.isArray(commissions) ? commissions : []);
    } catch (err) {
      setReceiptError(extractErrorMessage(err));
      setPaymentCommissions([]);
    } finally {
      setLoadingCommissions(false);
    }
  }

  function closeReceipt() {
    setSelectedPayment(null);
    setPaymentCommissions([]);
    setReceiptError('');
  }

  function applySearch() {
    setAppliedFilters({ month, year, beginDate, endDate });
  }

  function printReceipt() {
    window.print();
  }

  function exportReceiptExcel() {
    if (!selectedPayment) return;
    const csv = buildCsv(paymentCommissions);
    downloadTextFile(csv, `segunda-via-pagamento-${selectedPayment.id}.csv`);
  }

  const totalCommission = paymentCommissions.reduce((acc, item) => acc + Number(item.value || 0), 0);

  return (
    <div>
      <PageHeader title="2ª Via de Pagamento" subtitle="Consulta por período com emissão individual de comprovante." />

      <div className="card mb-4 overflow-hidden p-0">
        <div className="bg-[#1e242f] px-4 py-2 text-center font-semibold uppercase text-white">2ª Via de Pagamento</div>
        <div className="border-t-2 border-amber-500 p-3">
          <div className="grid gap-2 md:grid-cols-[180px_1fr] md:items-center">
            <span className="text-sm font-medium">Mensal:</span>
            <div className="flex flex-wrap items-center gap-2">
              <SearchSelect
                className="w-40"
                compact
                value={month}
                options={MONTH_OPTIONS}
                onChange={setMonth}
              />
              <span className="text-sm font-semibold">/ Ano:</span>
              <SearchSelect
                className="w-28"
                compact
                value={year}
                options={yearOptions}
                onChange={setYear}
              />
            </div>

            <span className="text-sm font-medium">Período:</span>
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="date"
                value={beginDate}
                onChange={(e) => setBeginDate(e.target.value)}
                className="h-8 rounded border border-gray-300 px-2 text-sm"
              />
              <span className="text-sm">-</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="h-8 rounded border border-gray-300 px-2 text-sm"
              />
            </div>
          </div>

          <div className="mt-3 flex justify-center">
            <Button size="sm" onClick={applySearch}>
              Buscar
            </Button>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="mb-3 border-b-2 border-amber-500 bg-[#666] px-3 py-1.5 text-center font-semibold uppercase text-white">
          Resultado
        </div>

        {loading ? (
          <SectionSpinner />
        ) : error ? (
          <p className="text-sm text-red-600">{error}</p>
        ) : filteredPayments.length === 0 ? (
          <EmptyState icon={Landmark} title="Nenhum pagamento encontrado" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b border-gray-300 bg-[#9a9a9a] text-left text-xs uppercase text-white">
                  <th className="py-2 pr-3">Pagamento</th>
                  <th className="py-2 pr-3">Data</th>
                  <th className="py-2 pr-3">Nome do corretor</th>
                  <th className="py-2 pr-3">Valor</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Opções</th>
                </tr>
              </thead>
              <tbody>
                {filteredPayments.map((payment) => (
                  <tr key={payment.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-2 pr-3 font-medium">{payment.id}</td>
                    <td className="py-2 pr-3 text-[var(--color-text-muted)]">
                      {payment.paid_at ? formatDate(payment.paid_at) : formatDate(payment.created_at)}
                    </td>
                    <td className="py-2 pr-3">
                      {payment.user_details
                        ? `${payment.user_details.id} - ${payment.user_details.cpf} ${payment.user_details.first_name} ${payment.user_details.last_name}`.trim()
                        : `#${payment.user}`}
                    </td>
                    <td className="py-2 pr-3 font-medium text-emerald-700">{formatCurrency(payment.total_amount)}</td>
                    <td className="py-2 pr-3">
                      <StatusBadge status={payment.status} label={payment.status_display} />
                    </td>
                    <td className="py-2 pr-3">
                      <button
                        type="button"
                        onClick={() => emitReceipt(payment)}
                        className="rounded bg-amber-400 px-3 py-1 font-semibold text-gray-900"
                      >
                        Emitir
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedPayment && (
        <div className="fixed inset-0 z-50 bg-black/35 p-4">
          <div className="mx-auto max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-md bg-white shadow-xl">
            <div className="flex flex-col gap-2 bg-[#1e242f] px-4 py-3 text-white sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-lg font-semibold md:text-xl">Recibo de Pagamento</h2>
              <div className="flex flex-wrap items-center gap-2">
                <button type="button" onClick={printReceipt} className="rounded bg-amber-400 px-3 py-1 text-sm font-semibold text-gray-900">
                  Imprimir
                </button>
                <button type="button" onClick={exportReceiptExcel} className="rounded bg-amber-400 px-3 py-1 text-sm font-semibold text-gray-900">
                  Gerar Excel
                </button>
                <button type="button" onClick={closeReceipt} className="rounded bg-amber-400 px-3 py-1 text-sm font-semibold text-gray-900">
                  Voltar
                </button>
              </div>
            </div>

            <div className="border-t-2 border-amber-500 p-4">
              <div className="mb-4 grid gap-3 border border-gray-200 p-3 md:grid-cols-2">
                <div>
                  <p className="text-sm text-gray-500">Pagamento</p>
                  <p className="font-semibold">#{selectedPayment.id}</p>
                  <p className="text-sm text-gray-600">
                    Data: {selectedPayment.paid_at ? formatDateTime(selectedPayment.paid_at) : formatDateTime(selectedPayment.created_at)}
                  </p>
                  <p className="text-sm text-gray-600">Metodo: {METHOD_LABELS[selectedPayment.payment_method] ?? selectedPayment.payment_method ?? '—'}</p>
                </div>
                <div className="md:text-right">
                  <p className="text-sm text-gray-500">Corretor</p>
                  <p className="font-semibold">
                    {selectedPayment.user_details?.cpf ? formatCPF(selectedPayment.user_details.cpf) : '—'}
                  </p>
                  <p>
                    {selectedPayment.user_details?.first_name} {selectedPayment.user_details?.last_name}
                  </p>
                  <p className="text-sm font-semibold text-emerald-700">Total: {formatCurrency(selectedPayment.total_amount)}</p>
                </div>
              </div>

              {loadingCommissions ? (
                <SectionSpinner />
              ) : receiptError ? (
                <p className="text-sm text-red-600">{receiptError}</p>
              ) : (
                <>
                  <div className="mb-3 border-b-2 border-amber-500 bg-[#1e242f] px-3 py-1.5 text-center font-semibold uppercase text-white">
                    Propostas
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-300 text-left text-xs uppercase text-[var(--color-text-muted)]">
                          <th className="py-2 pr-2">Proposta</th>
                          <th className="py-2 pr-2">Data</th>
                          <th className="py-2 pr-2">Cliente</th>
                          <th className="py-2 pr-2">Produto</th>
                          <th className="py-2 pr-2">Valor</th>
                          <th className="py-2 pr-2">(%)</th>
                          <th className="py-2 pr-2">Comissão</th>
                        </tr>
                      </thead>
                      <tbody>
                        {paymentCommissions.map((commission) => (
                          <tr key={commission.id} className="border-b border-gray-100">
                            <td className="py-2 pr-2 font-mono text-xs">
                              {commission.proposal_details?.contract_number ?? String(commission.proposal)}
                            </td>
                            <td className="py-2 pr-2">
                              {commission.proposal_details?.disbursement_date
                                ? formatDate(commission.proposal_details.disbursement_date)
                                : '—'}
                            </td>
                            <td className="py-2 pr-2">{commission.proposal_details?.client_name ?? '—'}</td>
                            <td className="py-2 pr-2">{commission.proposal_details?.table_details?.name_in_bank ?? '—'}</td>
                            <td className="py-2 pr-2">{formatCurrency(commission.proposal_details?.amount ?? 0)}</td>
                            <td className="py-2 pr-2">{formatPercent(commission.percentage)}</td>
                            <td className="py-2 pr-2 font-semibold text-emerald-700">{formatCurrency(commission.value)}</td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="bg-gray-100 font-semibold">
                          <td className="py-2 pr-2" colSpan={6}>
                            Total pago ao corretor
                          </td>
                          <td className="py-2 pr-2 text-emerald-700">{formatCurrency(totalCommission)}</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>

                  <div className="mt-4 rounded border border-gray-300 p-4 text-[15px] leading-7 text-[#1f2937]">
                    <h3 className="mb-3 text-center text-2xl font-semibold">Empresa (2ª via de pagamento)</h3>
                    <p className="mb-3 font-semibold">
                      Corretor: {selectedPayment.user_details?.cpf ? formatCPF(selectedPayment.user_details.cpf) : '—'}
                      {' - '}
                      {selectedPayment.user_details?.first_name} {selectedPayment.user_details?.last_name}
                    </p>
                    <p>
                      Recebi a importancia acima referente ao pagamento de servicos de venda, declarando que nao trabalho com exclusividade e estou em condicao de prestador autonomo.
                    </p>
                    <p className="mt-4">
                      Valor: <strong>{formatCurrency(totalCommission)}</strong>
                    </p>
                    <p>
                      Data: <strong>{selectedPayment.paid_at ? formatDate(selectedPayment.paid_at) : formatDate(selectedPayment.created_at)}</strong>
                    </p>
                    <p className="mt-8 text-center font-semibold">
                      ________________________________________________
                    </p>
                    <p className="text-center font-semibold">
                      {selectedPayment.user_details?.first_name} {selectedPayment.user_details?.last_name}
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>

          <button
            type="button"
            aria-label="Fechar"
            onClick={closeReceipt}
            className="absolute right-7 top-6 rounded-full bg-black p-1 text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      )}
    </div>
  );
}
