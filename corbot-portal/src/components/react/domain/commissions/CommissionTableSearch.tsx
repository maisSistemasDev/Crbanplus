import { useEffect, useMemo, useState } from 'react';
import { Percent } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { formatCurrency, formatDate, formatPercent } from '../../../../lib/utils/format';
import type { Agreement, Bank, CommissionTableRow, PaginatedResponse, Table } from '../../../../lib/api/types';
import { SearchSelect } from '../../ui/SearchSelect';
import { Button } from '../../ui/Button';
import { EmptyState } from '../../ui/EmptyState';
import { SectionSpinner } from '../../ui/Spinner';

const FORMAT_OPTIONS = [{ value: 'digital', label: 'Digital' }];
const PRODUCT_TYPE_OPTIONS = [{ value: 'novo', label: 'Novo' }];
const VIGENCY_OPTIONS = [{ value: 'current', label: 'Vigente' }];
const SORT_OPTIONS = [
  { value: 'range', label: 'Parcelas' },
  { value: 'commission', label: 'Comissão' },
];

function asList<T>(res: T[] | PaginatedResponse<T> | { results?: T[] }): T[] {
  if (Array.isArray(res)) return res;
  return res.results || [];
}

function rangeLabel(minValue: string, maxValue: string) {
  const min = Number(minValue);
  const max = Number(maxValue);
  if (!min && !max) return '—';
  return `${formatCurrency(min)} até ${formatCurrency(max)}`;
}

function commissionLabel(row: CommissionTableRow) {
  if (row.fixed_value !== null && row.fixed_value !== undefined && row.fixed_value !== '') {
    return formatCurrency(row.fixed_value);
  }
  return formatPercent(row.commission_rate);
}

function operationLabel(row: CommissionTableRow) {
  return [row.bank_name, row.agreement_name, row.product].filter(Boolean).join(' – ');
}

export function CommissionTableSearch() {
  const [banks, setBanks] = useState<Bank[]>([]);
  const [agreements, setAgreements] = useState<Agreement[]>([]);
  const [products, setProducts] = useState<Table[]>([]);
  const [bankId, setBankId] = useState('');
  const [agreementId, setAgreementId] = useState('');
  const [productId, setProductId] = useState('');
  const [sort, setSort] = useState<'range' | 'commission'>('range');
  const [rows, setRows] = useState<CommissionTableRow[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [truncated, setTruncated] = useState(false);

  const bankOptions = useMemo(
    () =>
      banks
        .filter((bank) => bank.is_active !== false)
        .map((bank) => ({ value: bank.id, label: bank.name })),
    [banks],
  );
  const agreementOptions = useMemo(
    () =>
      agreements
        .filter((agreement) => agreement.is_active !== false)
        .map((agreement) => ({ value: agreement.id, label: agreement.name })),
    [agreements],
  );
  const productOptions = useMemo(
    () =>
      products
        .filter((table) => table.is_active !== false)
        .map((table) => ({
          value: table.id,
          label: table.name_in_bank || table.code_in_bank || table.id,
        })),
    [products],
  );

  useEffect(() => {
    api
      .get<Bank[] | PaginatedResponse<Bank>>(ENDPOINTS.BANKS)
      .then((res) => setBanks(asList(res)))
      .catch(() => setBanks([]));
  }, []);

  useEffect(() => {
    const url = bankId
      ? `${ENDPOINTS.AGREEMENTS}?bank=${encodeURIComponent(bankId)}`
      : ENDPOINTS.AGREEMENTS;
    api
      .get<Agreement[] | PaginatedResponse<Agreement>>(url)
      .then((res) => {
        const list = asList(res);
        setAgreements(list);
        setAgreementId((current) => (current && list.some((item) => item.id === current) ? current : ''));
      })
      .catch(() => setAgreements([]));
  }, [bankId]);

  useEffect(() => {
    if (!bankId) {
      setProducts([]);
      setProductId('');
      return;
    }
    const params = new URLSearchParams({ page_size: '500', bank: bankId });
    if (agreementId) params.set('agreement', agreementId);
    api
      .get<PaginatedResponse<Table> | Table[]>(`${ENDPOINTS.TABLES}?${params.toString()}`)
      .then((res) => {
        const list = asList(res);
        setProducts(list);
        setProductId((current) => (current && list.some((item) => item.id === current) ? current : ''));
      })
      .catch(() => setProducts([]));
  }, [bankId, agreementId]);

  async function handleSearch(event?: React.FormEvent) {
    event?.preventDefault();
    setLoading(true);
    setSearched(true);
    try {
      const params = new URLSearchParams({ sort });
      if (bankId) params.set('bank', bankId);
      if (agreementId) params.set('agreement', agreementId);
      if (productId) params.set('table', productId);
      const response = await api.get<{ results: CommissionTableRow[]; truncated?: boolean }>(
        `${ENDPOINTS.TABLES_CATALOG}?${params.toString()}`,
      );
      setRows(response.results || []);
      setTruncated(Boolean(response.truncated));
    } catch (error) {
      toast.error(extractErrorMessage(error) || 'Erro ao consultar tabelas');
      setRows([]);
    } finally {
      setLoading(false);
    }
  }

  function handleExport() {
    if (rows.length === 0) {
      toast.error('Faça uma busca antes de exportar.');
      return;
    }
    const header = ['Operação', 'Parcelas', 'Comissão', 'Vigência', 'Tipo', 'Formalização'];
    const lines = [
      header.join(';'),
      ...rows.map((row) =>
        [
          operationLabel(row),
          rangeLabel(row.min_value, row.max_value),
          commissionLabel(row),
          row.vigency_date ? formatDate(row.vigency_date) : '',
          row.product_type,
          row.format,
        ]
          .map((value) => `"${String(value).replace(/"/g, '""')}"`)
          .join(';'),
      ),
    ];
    const blob = new Blob([`\uFEFF${lines.join('\n')}`], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `tabelas_comissionamento_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      <section className="overflow-hidden rounded-lg border border-[var(--color-border)] bg-white">
        <div className="border-b-2 border-[var(--color-primary)] bg-[var(--color-sidebar-bg)] px-4 py-3">
          <h1 className="text-sm font-semibold text-white">Tabela de Comissionamento</h1>
        </div>

        <form onSubmit={handleSearch} className="space-y-4 p-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <SearchSelect
              label="Vigência"
              value="current"
              options={VIGENCY_OPTIONS}
              onChange={() => {}}
            />
            <SearchSelect
              label="Banco"
              placeholder="Selecione..."
              allowEmpty
              value={bankId}
              options={bankOptions}
              onChange={(value) => {
                setBankId(value);
                setAgreementId('');
                setProductId('');
              }}
            />
            <SearchSelect
              label="Convênio"
              placeholder="Selecione..."
              allowEmpty
              value={agreementId}
              options={agreementOptions}
              onChange={(value) => {
                setAgreementId(value);
                setProductId('');
              }}
            />
            <SearchSelect
              label="Tipo de Produto"
              value="novo"
              options={PRODUCT_TYPE_OPTIONS}
              onChange={() => {}}
            />
            <SearchSelect
              label="Produto"
              placeholder="Selecione..."
              allowEmpty
              value={productId}
              options={productOptions}
              onChange={setProductId}
              disabled={!bankId}
            />
          </div>

          <div className="flex flex-wrap items-end gap-4">
            <div className="w-full sm:w-44">
              <SearchSelect
                label="Formato"
                value="digital"
                options={FORMAT_OPTIONS}
                onChange={() => {}}
              />
            </div>
            <div>
              <p className="mb-1 text-sm font-medium text-gray-700">Ordenar por</p>
              <div className="flex items-center gap-4 py-1.5 text-sm text-gray-700">
                {SORT_OPTIONS.map((option) => (
                  <label key={option.value} className="inline-flex items-center gap-1.5">
                    <input
                      type="radio"
                      name="sort"
                      checked={sort === option.value}
                      onChange={() => setSort(option.value as 'range' | 'commission')}
                    />
                    {option.label}
                  </label>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <Button type="submit" loading={loading}>
                Buscar
              </Button>
              {searched && rows.length > 0 && (
                <Button type="button" variant="secondary" onClick={handleExport}>
                  Gerar Excel
                </Button>
              )}
            </div>
          </div>
        </form>
      </section>

      {loading ? (
        <SectionSpinner />
      ) : !searched ? (
        <EmptyState
          icon={Percent}
          title="Consulte as tabelas"
          description="Use os filtros e clique em Buscar para ver as comissões vigentes."
        />
      ) : rows.length === 0 ? (
        <EmptyState
          icon={Percent}
          title="Nenhuma tabela encontrada"
          description="Não há tabelas vigentes para os filtros selecionados."
        />
      ) : (
        <section className="overflow-hidden rounded-lg border border-[var(--color-border)] bg-white">
          {truncated && (
            <p className="border-b border-amber-100 bg-amber-50 px-4 py-2 text-xs text-amber-800">
              A busca foi limitada às primeiras 5.000 faixas. Refine os filtros para ver o restante.
            </p>
          )}
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
                  <th className="px-4 py-2 font-medium">Operação</th>
                  <th className="px-4 py-2 font-medium">Parcelas</th>
                  <th className="px-4 py-2 font-medium">Comissão</th>
                  <th className="px-4 py-2 font-medium">Vigência</th>
                  <th className="px-4 py-2 font-medium">Formalização</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr
                    key={`${row.table_id}-${row.range_id || 'base'}`}
                    className="border-b border-gray-100 last:border-0"
                  >
                    <td className="px-4 py-2 text-gray-800">{operationLabel(row)}</td>
                    <td className="px-4 py-2 text-gray-600">{rangeLabel(row.min_value, row.max_value)}</td>
                    <td className="px-4 py-2">
                      <span className="rounded bg-[var(--color-primary-bg)] px-2 py-0.5 font-semibold text-[var(--color-primary-dark)]">
                        {commissionLabel(row)}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-gray-600">
                      {row.vigency_date ? formatDate(row.vigency_date) : '—'}
                    </td>
                    <td className="px-4 py-2 text-gray-600">{row.format}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
