import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { DataTable } from '../../ui/DataTable';
import { Badge } from '../../ui/Badge';
import { Button } from '../../ui/Button';
import { formatCurrency, formatDate } from '../../../../lib/utils/format';
import type { Column } from '../../ui/DataTable';
import type { PaginatedResponse } from '../../../../lib/api/types';
import { Search, Filter } from 'lucide-react';
import toast from 'react-hot-toast';

interface Proposal {
  id: string;
  contract_number: string;
  client_name: string;
  client_document: string;
  seller: number;
  seller_details?: { first_name: string; last_name: string };
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
  disbursement_date: string;
  created_at: string;
}

interface FilterOptions {
  banks: Array<{ id: string; name: string }>;
  companies: Array<{ id: string; name: string }>;
  sellers: Array<{ id: number; first_name: string; last_name: string }>;
  agreements: Array<{ id: string; name: string }>;
  tables: Array<{ id: string; name_in_bank: string }>;
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

  // Filtros
  const [search, setSearch] = useState('');
  const [bankFilter, setBankFilter] = useState('');
  const [companyFilter, setCompanyFilter] = useState('');
  const [sellerFilter, setSellerFilter] = useState('');
  const [agreementFilter, setAgreementFilter] = useState('');
  const [tableFilter, setTableFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const fetchFilterOptions = useCallback(async () => {
    try {
      const [banks, companies, sellers, agreements, tables] = await Promise.all([
        api.get(ENDPOINTS.BANKS),
        api.get(ENDPOINTS.COMPANIES),
        api.get(ENDPOINTS.SELLERS),
        api.get('/agreements/'),
        api.get('/tables/'),
      ]);
      
      setFilterOptions({
        banks: banks.results || banks,
        companies: companies.results || companies,
        sellers: sellers.results || sellers,
        agreements: agreements.results || agreements,
        tables: tables.results || tables,
      });
    } catch (error) {
      console.error('Error fetching filter options:', error);
    }
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: '20',
      });

      if (search) params.append('search', search);
      if (bankFilter) params.append('bank', bankFilter);
      if (companyFilter) params.append('company', companyFilter);
      if (sellerFilter) params.append('seller', sellerFilter);
      if (agreementFilter) params.append('agreement', agreementFilter);
      if (tableFilter) params.append('table', tableFilter);

      const response = await api.get<PaginatedResponse<Proposal>>(
        `/proposals/?${params.toString()}`
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
  }, [currentPage, search, bankFilter, companyFilter, sellerFilter, agreementFilter, tableFilter]);

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
      render: (item) => (
        <span className="font-mono text-sm">{item.contract_number}</span>
      ),
    },
    {
      key: 'client_name',
      header: 'Cliente',
      render: (item) => (
        <div>
          <div className="font-medium text-sm">{item.client_name}</div>
          <div className="text-xs text-gray-500">{item.client_document}</div>
        </div>
      ),
    },
    {
      key: 'seller',
      header: 'Vendedor',
      render: (item) => {
        const seller = item.seller_details;
        return seller ? `${seller.first_name} ${seller.last_name}` : '-';
      },
    },
    {
      key: 'company',
      header: 'Empresa',
      render: (item) => item.company_details?.name || '-',
    },
    {
      key: 'bank',
      header: 'Banco',
      render: (item) => item.bank_details?.name || '-',
    },
    {
      key: 'agreement',
      header: 'Convênio',
      render: (item) => (
        <div className="text-sm">
          <div>{item.agreement_details?.name || '-'}</div>
          <div className="text-xs text-gray-500">{item.table_details?.name_in_bank || '-'}</div>
        </div>
      ),
    },
    {
      key: 'amount',
      header: 'Valor',
      render: (item) => (
        <span className="font-semibold text-green-600">
          {formatCurrency(item.amount)}
        </span>
      ),
    },
    {
      key: 'disbursement_date',
      header: 'Data Liberação',
      render: (item) => formatDate(item.disbursement_date),
    },
    {
      key: 'created_at',
      header: 'Criado em',
      render: (item) => formatDate(item.created_at),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Propostas</h1>
          <p className="text-sm text-gray-600 mt-1">Listagem de todas as propostas</p>
        </div>
        <Button
          onClick={() => setShowFilters(!showFilters)}
          variant="secondary"
          icon={<Filter size={16} />}
        >
          {showFilters ? 'Ocultar Filtros' : 'Mostrar Filtros'}
        </Button>
      </div>

      <div className="space-y-4 mb-4">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar por contrato, CPF ou nome do cliente..."
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
            <select
              value={bankFilter}
              onChange={(e) => {
                setBankFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
            >
              <option value="">Todos os Bancos</option>
              {filterOptions.banks.map((bank) => (
                <option key={bank.id} value={bank.id}>
                  {bank.name}
                </option>
              ))}
            </select>

            <select
              value={companyFilter}
              onChange={(e) => {
                setCompanyFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
            >
              <option value="">Todos os Corbans</option>
              {filterOptions.companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>

            <select
              value={sellerFilter}
              onChange={(e) => {
                setSellerFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
            >
              <option value="">Todos os Vendedores</option>
              {filterOptions.sellers.map((seller) => (
                <option key={seller.id} value={seller.id}>
                  {seller.first_name} {seller.last_name}
                </option>
              ))}
            </select>

            <select
              value={agreementFilter}
              onChange={(e) => {
                setAgreementFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
            >
              <option value="">Todos os Convênios</option>
              {filterOptions.agreements.map((agreement) => (
                <option key={agreement.id} value={agreement.id}>
                  {agreement.name}
                </option>
              ))}
            </select>

            <select
              value={tableFilter}
              onChange={(e) => {
                setTableFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
            >
              <option value="">Todas as Tabelas</option>
              {filterOptions.tables.map((table) => (
                <option key={table.id} value={table.id}>
                  {table.name_in_bank}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <DataTable
          data={data}
          columns={columns}
          loading={loading}
          emptyMessage="Nenhuma proposta encontrada"
          pagination={{
            currentPage,
            totalItems,
            pageSize: 20,
            onPageChange: setCurrentPage,
          }}
        />
      </div>
    </div>
  );
}
