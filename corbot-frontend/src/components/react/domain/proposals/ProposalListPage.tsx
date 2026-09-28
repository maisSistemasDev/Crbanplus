import { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { DataTable } from '../../ui/DataTable';
import { StatusBadge } from '../../ui/Badge';
import { Button } from '../../ui/Button';
import { PageHeader } from '../../ui/PageHeader';
import { MultiValueFilter } from '../../ui/MultiValueFilter';
import { SearchSelect } from '../../ui/SearchSelect';
import { formatCurrency, formatDate } from '../../../../lib/utils/format';
import type { Column } from '../../ui/DataTable';
import type { PaginatedResponse, ProposalClaimSummary } from '../../../../lib/api/types';
import { Search, Filter, AlertTriangle, Download } from 'lucide-react';
import toast from 'react-hot-toast';
import { useStore } from '@nanostores/react';
import { PageShell } from '../../layout/PageShell';
import { ClaimModal, type ClaimProposal } from './ClaimModal';
import { isPromotoraAdmin } from '../../../../lib/utils/roles';
import { $currentUser } from '../../../../lib/stores/auth';
import { extractErrorMessage } from '../../../../lib/api/errors';

interface Proposal {
  id: string;
  contract_number: string;
  client_name: string;
  client_document: string;
  seller: number | null;
  seller_details?: { first_name: string; last_name: string; display_name?: string };
  digitador: string | null;
  bank_access: number | null;
  bank_access_details?: { id: number; username: string; display_name?: string };
  company: string;
  company_details?: { name: string };
  bank: string;
  bank_details?: { name: string };
  agreement: string;
  agreement_details?: { name: string };
  table: string;
  table_details?: { name_in_bank: string };
  amount: number;
  status: string;
  payment_status?: string;
  payment_status_display?: string;
  commission_value?: string | number | null;
  disbursement_date: string;
  created_at: string;
  claim_details?: ProposalClaimSummary | null;
}

interface FilterOptions {
  banks: Array<{ id: string; name: string }>;
  companies: Array<{ id: string; name: string }>;
  sellers: Array<{ id: number; first_name: string; last_name: string }>;
  agreements: Array<{ id: string; name: string }>;
  tables: Array<{ id: string; name_in_bank: string }>;
}

type DateRangePreset = '' | 'today' | 'last7' | 'last30' | 'thisMonth' | 'custom';
type DateField = 'created_at' | 'disbursement_date';

const PAYMENT_STATUS_OPTIONS = [
  { value: 'not_released', label: 'Não liberado' },
  { value: 'pending_manual_payment', label: 'Aguardando pagamento' },
  { value: 'withdraw_available', label: 'Saque liberado' },
  { value: 'paid', label: 'Pago' },
  { value: 'sinistro', label: 'Sinistro' },
];

const DATE_FIELD_OPTIONS = [
  { value: 'created_at', label: 'Data de cadastro' },
  { value: 'disbursement_date', label: 'Data de liberação' },
];

const DATE_PRESET_OPTIONS = [
  { value: 'today', label: 'Hoje' },
  { value: 'last7', label: 'Últimos 7 dias' },
  { value: 'last30', label: 'Últimos 30 dias' },
  { value: 'thisMonth', label: 'Este mês' },
  { value: 'custom', label: 'Selecionar período' },
];

function formatDateInput(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function resolveDateRange(preset: DateRangePreset, customBegin: string, customEnd: string) {
  const today = new Date();

  if (preset === 'custom') {
    return { begin: customBegin, end: customEnd };
  }
  if (preset === 'today') {
    const value = formatDateInput(today);
    return { begin: value, end: value };
  }
  if (preset === 'last7') {
    const begin = new Date(today);
    begin.setDate(today.getDate() - 6);
    return { begin: formatDateInput(begin), end: formatDateInput(today) };
  }
  if (preset === 'last30') {
    const begin = new Date(today);
    begin.setDate(today.getDate() - 29);
    return { begin: formatDateInput(begin), end: formatDateInput(today) };
  }
  if (preset === 'thisMonth') {
    const begin = new Date(today.getFullYear(), today.getMonth(), 1);
    return { begin: formatDateInput(begin), end: formatDateInput(today) };
  }
  return { begin: '', end: '' };
}

export function ProposalListPage() {
  const [data, setData] = useState<Proposal[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    banks: [],
    companies: [],
    sellers: [],
    agreements: [],
    tables: [],
  });

  const bankOptions = useMemo(
    () => filterOptions.banks.map((bank) => ({ value: bank.id, label: bank.name })),
    [filterOptions.banks],
  );
  const companyOptions = useMemo(
    () => filterOptions.companies.map((company) => ({ value: company.id, label: company.name })),
    [filterOptions.companies],
  );
  const sellerOptions = useMemo(
    () =>
      filterOptions.sellers.map((seller) => ({
        value: String(seller.id),
        label: `${seller.first_name} ${seller.last_name}`.trim(),
      })),
    [filterOptions.sellers],
  );
  const agreementOptions = useMemo(
    () => filterOptions.agreements.map((agreement) => ({ value: agreement.id, label: agreement.name })),
    [filterOptions.agreements],
  );
  const tableOptions = useMemo(
    () => filterOptions.tables.map((table) => ({ value: table.id, label: table.name_in_bank })),
    [filterOptions.tables],
  );

  // Filtros
  const [search, setSearch] = useState('');
  const [bankFilter, setBankFilter] = useState('');
  const [companyFilter, setCompanyFilter] = useState('');
  const [sellerFilter, setSellerFilter] = useState('');
  const [agreementFilter, setAgreementFilter] = useState('');
  const [tableFilter, setTableFilter] = useState('');
  const [matriculaFilter, setMatriculaFilter] = useState('');
  const [clientCpfFilter, setClientCpfFilter] = useState('');
  const [contractFilter, setContractFilter] = useState('');
  const [paymentStatusFilter, setPaymentStatusFilter] = useState('');
  const [dateField, setDateField] = useState<DateField>('created_at');
  const [dateRangePreset, setDateRangePreset] = useState<DateRangePreset>('');
  const [customBeginDate, setCustomBeginDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [claimProposal, setClaimProposal] = useState<ClaimProposal | null>(null);

  const currentUser = useStore($currentUser);
  const canRegisterClaim = isPromotoraAdmin(currentUser?.role ?? null, currentUser?.company ?? null);

  const buildFilterParams = useCallback(() => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (bankFilter) params.set('bank', bankFilter);
    if (companyFilter) params.set('company', companyFilter);
    if (sellerFilter) params.set('seller', sellerFilter);
    if (agreementFilter) params.set('agreement', agreementFilter);
    if (tableFilter) params.set('table', tableFilter);
    if (matriculaFilter) params.set('matricula', matriculaFilter);
    if (clientCpfFilter) params.set('client_cpf', clientCpfFilter);
    if (contractFilter) params.set('contract_number', contractFilter);
    if (paymentStatusFilter) params.set('payment_status', paymentStatusFilter);
    const { begin, end } = resolveDateRange(dateRangePreset, customBeginDate, customEndDate);
    if (begin) params.set('begin_date', begin);
    if (end) params.set('end_date', end);
    if (begin || end) params.set('date_field', dateField);
    return params;
  }, [
    search,
    bankFilter,
    companyFilter,
    sellerFilter,
    agreementFilter,
    tableFilter,
    matriculaFilter,
    clientCpfFilter,
    contractFilter,
    paymentStatusFilter,
    dateField,
    dateRangePreset,
    customBeginDate,
    customEndDate,
  ]);

  const fetchFilterOptions = useCallback(async () => {
    try {
      const [banks, companies, sellers, tables] = await Promise.all([
        api.get(ENDPOINTS.BANKS),
        api.get(`${ENDPOINTS.COMPANIES}?page_size=500`),
        api.get(ENDPOINTS.SELLERS),
        api.get('/tables/'),
      ]);
      
      setFilterOptions((prev) => ({
        ...prev,
        banks: banks.results || banks,
        companies: companies.results || companies,
        sellers: sellers.results || sellers,
        tables: tables.results || tables,
      }));
    } catch (error) {
      console.error('Error fetching filter options:', error);
    }
  }, []);

  useEffect(() => {
    const url = bankFilter
      ? `${ENDPOINTS.AGREEMENTS}?bank=${encodeURIComponent(bankFilter)}`
      : ENDPOINTS.AGREEMENTS;
    api
      .get<{ id: string; name: string }[] | { results: { id: string; name: string }[] }>(url)
      .then((res) => {
        const list = Array.isArray(res) ? res : res.results || [];
        setFilterOptions((prev) => ({ ...prev, agreements: list }));
        setAgreementFilter((current) =>
          current && list.some((item) => item.id === current) ? current : '',
        );
      })
      .catch(() => setFilterOptions((prev) => ({ ...prev, agreements: [] })));
  }, [bankFilter]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = buildFilterParams();
      params.set('page', currentPage.toString());
      params.set('page_size', '20');

      const response = await api.get<PaginatedResponse<Proposal>>(
        `${ENDPOINTS.PROPOSALS}?${params.toString()}`
      );
      
      setData(response.results);
      setTotalItems(response.count);
    } catch (error) {
      console.error('Error fetching proposals:', error);
      toast.error('Erro ao carregar propostas');
      setData([]);
      setTotalItems(0);
    } finally {
      setLoading(false);
    }
  }, [buildFilterParams, currentPage]);

  async function handleExport() {
    setExporting(true);
    try {
      const { blob, filename } = await api.getBlob(
        `${ENDPOINTS.PROPOSALS_EXPORT}?${buildFilterParams().toString()}`
      );
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename || 'propostas.xlsx';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(extractErrorMessage(error) || 'Erro ao exportar propostas');
    } finally {
      setExporting(false);
    }
  }

  useEffect(() => {
    fetchFilterOptions();
  }, [fetchFilterOptions]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const columns: Column<Proposal>[] = [
    {
      key: 'contract_number',
      header: 'Contrato',
      className: 'whitespace-nowrap',
      render: (item) => (
        <span className="font-mono">{item.contract_number}</span>
      ),
    },
    {
      key: 'client_name',
      header: 'Cliente',
      className: 'max-w-[120px]',
      render: (item) => (
        <div className="min-w-0">
          <div className="font-medium truncate" title={item.client_name}>{item.client_name}</div>
          <div className="text-[10px] text-gray-500 truncate">{item.client_document}</div>
        </div>
      ),
    },
    {
      key: 'digitador',
      header: 'Digitador / Acesso',
      className: 'max-w-[140px]',
      render: (item) => {
        const digitador = item.digitador?.trim();
        const accessName = item.bank_access_details?.display_name || item.bank_access_details?.username;
        const seller = item.seller_details;
        const sellerName = seller ? `${seller.first_name} ${seller.last_name}`.trim() : '';
        const primary = digitador || accessName || sellerName || '-';
        const secondary = digitador && accessName ? accessName : '';
        return (
          <div className="min-w-0">
            <div className="truncate" title={primary}>{primary}</div>
            {secondary ? <div className="text-[10px] text-gray-500 truncate" title={secondary}>{secondary}</div> : null}
          </div>
        );
      },
    },
    {
      key: 'company',
      header: 'Empresa',
      className: 'max-w-[110px]',
      render: (item) => (
        <span className="block truncate" title={item.company_details?.name}>{item.company_details?.name || '-'}</span>
      ),
    },
    {
      key: 'bank',
      header: 'Banco',
      className: 'whitespace-nowrap',
      render: (item) => item.bank_details?.name || '-',
    },
    {
      key: 'agreement',
      header: 'Convênio',
      className: 'max-w-[160px]',
      render: (item) => {
        const agreement = item.agreement_details?.name || '-';
        const table = item.table_details?.name_in_bank || '';
        return (
          <div className="min-w-0">
            <div className="truncate" title={agreement}>{agreement}</div>
            {table ? <div className="text-[10px] text-gray-500 truncate" title={table}>{table}</div> : null}
          </div>
        );
      },
    },
    {
      key: 'amount',
      header: 'Valor',
      className: 'whitespace-nowrap',
      render: (item) => (
        <span className="font-semibold text-green-600">
          {formatCurrency(item.amount)}
        </span>
      ),
    },
    {
      key: 'commission_value',
      header: 'Comissão',
      className: 'whitespace-nowrap',
      render: (item) => (
        item.commission_value == null
          ? '-'
          : <span className="font-medium text-emerald-700">{formatCurrency(item.commission_value)}</span>
      ),
    },
    {
      key: 'processing_status',
      header: 'Status',
      className: 'whitespace-nowrap',
      render: () => <StatusBadge status="processed" className="text-[10px] px-1.5 py-0" />,
    },
    {
      key: 'status',
      header: 'Status Pagamento',
      className: 'whitespace-nowrap',
      render: (item) => (
        <StatusBadge
          status={item.payment_status || item.status || 'pending'}
          className="text-[10px] px-1.5 py-0"
        />
      ),
    },
    {
      key: 'disbursement_date',
      header: 'Liberação',
      className: 'whitespace-nowrap',
      render: (item) => formatDate(item.disbursement_date),
    },
    {
      key: 'created_at',
      header: 'Criado em',
      className: 'whitespace-nowrap',
      render: (item) => formatDate(item.created_at),
    },
    {
      key: 'claim',
      header: 'Sinistro',
      className: 'whitespace-nowrap',
      render: (item: Proposal) => {
        const claim = item.claim_details;
        if (claim) {
          const detail =
            claim.claim_type === 'pago_corban_errado' && claim.correct_company_name
              ? `Corban correto: ${claim.correct_company_name}`
              : claim.claim_type_display;
          return (
            <div title={`${detail} — ${formatCurrency(claim.amount)} em ${formatDate(claim.created_at)}`}>
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                <AlertTriangle size={11} />
                {claim.claim_type === 'fraude' ? 'Fraude' : 'Corban errado'}
              </span>
              {claim.total > 1 && (
                <span className="ml-1 text-[10px] text-gray-400">+{claim.total - 1}</span>
              )}
              {canRegisterClaim && (
                <button
                  type="button"
                  onClick={() =>
                    setClaimProposal({
                      id: item.id,
                      contract_number: item.contract_number,
                      client_name: item.client_name,
                      amount: item.amount,
                      company_name: item.company_details?.name,
                    })
                  }
                  className="ml-1 text-[10px] text-gray-400 hover:text-amber-700"
                  title="Registrar outro sinistro"
                >
                  +
                </button>
              )}
            </div>
          );
        }
        if (!canRegisterClaim) return <span className="text-xs text-gray-300">-</span>;
        return (
          <button
            type="button"
            onClick={() =>
              setClaimProposal({
                id: item.id,
                contract_number: item.contract_number,
                client_name: item.client_name,
                amount: item.amount,
                company_name: item.company_details?.name,
              })
            }
            title="Registrar sinistro"
            className="inline-flex items-center gap-1 rounded px-2 py-1 text-[10px] font-medium text-amber-700 hover:bg-amber-50"
          >
            <AlertTriangle size={13} />
            Registrar
          </button>
        );
      },
    },
  ];

  return (
    <PageShell>
    <div>
      <PageHeader
        title="Propostas"
        subtitle="Listagem de todas as propostas"
        actions={
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="secondary"
              icon={<Download size={16} />}
              loading={exporting}
              onClick={handleExport}
            >
              Exportar para Excel
            </Button>
            <Button
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              variant="secondary"
              icon={<Filter size={16} />}
            >
              {showFilters ? 'Ocultar filtros' : 'Mostrar filtros'}
            </Button>
          </div>
        }
      />

      <div className="space-y-4 mb-4">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar por contrato, CPF, cliente, parceiro ou matrícula..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
          />
        </div>

        {showFilters && (
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3 bg-gray-50 p-4 rounded-lg border border-gray-200">
            <SearchSelect
              placeholder="Todos os Bancos"
              allowEmpty
              value={bankFilter}
              options={bankOptions}
              onChange={(e) => {
                setBankFilter(e.target.value);
                setCurrentPage(1);
              }}
            />

            <SearchSelect
              placeholder="Todos os Corbans"
              allowEmpty
              value={companyFilter}
              options={companyOptions}
              onChange={(e) => {
                setCompanyFilter(e.target.value);
                setCurrentPage(1);
              }}
            />

            <SearchSelect
              placeholder="Nome do parceiro"
              allowEmpty
              value={sellerFilter}
              options={sellerOptions}
              onChange={(e) => {
                setSellerFilter(e.target.value);
                setCurrentPage(1);
              }}
            />

            <SearchSelect
              placeholder="Todos os Convênios"
              allowEmpty
              value={agreementFilter}
              options={agreementOptions}
              onChange={(e) => {
                setAgreementFilter(e.target.value);
                setCurrentPage(1);
              }}
            />

            <SearchSelect
              placeholder="Todas as Tabelas"
              allowEmpty
              value={tableFilter}
              options={tableOptions}
              onChange={(e) => {
                setTableFilter(e.target.value);
                setCurrentPage(1);
              }}
            />

            <MultiValueFilter
              placeholder="Código do parceiro"
              addLabel="+ Matrícula"
              value={matriculaFilter}
              onChange={(value) => {
                setMatriculaFilter(value);
                setCurrentPage(1);
              }}
            />

            <MultiValueFilter
              placeholder="CPF do Cliente"
              addLabel="+ CPF"
              value={clientCpfFilter}
              onChange={(value) => {
                setClientCpfFilter(value);
                setCurrentPage(1);
              }}
            />

            <MultiValueFilter
              placeholder="Cód. da proposta"
              addLabel="+ Cód. da proposta"
              value={contractFilter}
              onChange={(value) => {
                setContractFilter(value);
                setCurrentPage(1);
              }}
            />

            <SearchSelect
              placeholder="Todos os status de pagamento"
              allowEmpty
              value={paymentStatusFilter}
              options={PAYMENT_STATUS_OPTIONS}
              onChange={(e) => {
                setPaymentStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
            />

            <div className="lg:col-span-2 space-y-2 rounded-lg border border-gray-200 bg-white p-3">
              <SearchSelect
                placeholder="Data de cadastro"
                value={dateField}
                options={DATE_FIELD_OPTIONS}
                onChange={(e) => {
                  setDateField(e.target.value as DateField);
                  setCurrentPage(1);
                }}
              />
              <SearchSelect
                placeholder="Qualquer data"
                allowEmpty
                value={dateRangePreset}
                options={DATE_PRESET_OPTIONS}
                onChange={(e) => {
                  setDateRangePreset(e.target.value as DateRangePreset);
                  setCurrentPage(1);
                }}
              />
              {dateRangePreset === 'custom' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <input
                    type="date"
                    value={customBeginDate}
                    onChange={(e) => {
                      setCustomBeginDate(e.target.value);
                      setCurrentPage(1);
                    }}
                    className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
                  />
                  <input
                    type="date"
                    value={customEndDate}
                    onChange={(e) => {
                      setCustomEndDate(e.target.value);
                      setCurrentPage(1);
                    }}
                    className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
                  />
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <DataTable
          data={data}
          columns={columns}
          loading={loading}
          compact
          emptyMessage="Nenhuma proposta encontrada"
          totalItems={totalItems}
          currentPage={currentPage}
          pageSize={20}
          onPageChange={setCurrentPage}
          keyExtractor={(item) => item.id}
        />
      </div>

      <ClaimModal
        isOpen={claimProposal !== null}
        onClose={() => setClaimProposal(null)}
        proposal={claimProposal}
        onSuccess={fetchData}
      />
    </div>
    </PageShell>
  );
}
