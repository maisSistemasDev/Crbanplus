import { useState, useEffect, useMemo } from 'react';
import { CrudPage } from '../shared/CrudPage';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { api, API_URL } from '../../../../lib/api/client';
import { Badge } from '../../ui/Badge';
import { Button } from '../../ui/Button';
import { SearchSelect } from '../../ui/SearchSelect';
import { TableCSVImport } from './TableCSVImport';
import { TableRangesForm } from './TableRangesForm';
import { Upload, Download } from 'lucide-react';
import type { Column } from '../../ui/DataTable';
import toast from 'react-hot-toast';

interface CommissionRange {
  min_value: string | number;
  max_value: string | number;
  commission_rate: string | number;
  fixed_value?: string | number | null;
}

function formatRangeBounds(r: CommissionRange) {
  if (Number(r.min_value) === 0 && Number(r.max_value) === 0) {
    return '';
  }
  const min = Number(r.min_value).toLocaleString('pt-BR', { minimumFractionDigits: 2 });
  const max = Number(r.max_value).toLocaleString('pt-BR', { minimumFractionDigits: 2 });
  return `R$${min} – R$${max}`;
}

function formatRangeCommission(r: CommissionRange) {
  if (r.fixed_value !== null && r.fixed_value !== undefined && r.fixed_value !== '') {
    return `R$ ${Number(r.fixed_value).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
  }
  return `${r.commission_rate}%`;
}

const columns: Column<Record<string, unknown>>[] = [
  { key: 'name_in_bank', header: 'Nome no Banco', sortable: true },
  {
    key: 'code_in_bank',
    header: 'Codigo da Tabela',
    sortable: true,
    render: (item) => String(item.code_in_bank || '-'),
  },
  { key: 'bank_name', header: 'Banco', sortable: true },
  { key: 'agreement_name', header: 'Convênio', sortable: true },
  {
    key: 'commission_ranges',
    header: 'Faixas',
    render: (item) => {
      const ranges = item.commission_ranges as CommissionRange[] | undefined;
      if (!ranges || ranges.length === 0) return <span className="text-gray-400 text-xs">Sem faixas</span>;
      return (
        <div className="flex flex-col gap-0.5">
          {ranges.map((r, i) => {
            const bounds = formatRangeBounds(r);
            return (
              <span key={i} className="text-xs text-gray-700">
                {bounds ? <>{bounds}: </> : null}
                <strong>{formatRangeCommission(r)}</strong>
              </span>
            );
          })}
        </div>
      );
    },
  },
  {
    key: 'is_active',
    header: 'Status',
    render: (item) => (
      <Badge variant={item.is_active ? 'success' : 'error'}>
        {item.is_active ? 'Ativa' : 'Inativa'}
      </Badge>
    ),
  },
];

export function TableList() {
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [bankFilter, setBankFilter] = useState('');
  const [agreementFilter, setAgreementFilter] = useState('');
  const [codeFilter, setCodeFilter] = useState('');
  const [banks, setBanks] = useState<{ id: string; name: string }[]>([]);
  const [agreements, setAgreements] = useState<{ id: string; name: string }[]>([]);

  const bankOptions = useMemo(() => banks.map((b) => ({ value: b.id, label: b.name })), [banks]);
  const agreementOptions = useMemo(() => agreements.map((a) => ({ value: a.id, label: a.name })), [agreements]);

  useEffect(() => {
    api.get<{ id: string; name: string }[]>(ENDPOINTS.BANKS).then(setBanks).catch(() => {});
  }, []);

  useEffect(() => {
    const url = bankFilter ? `${ENDPOINTS.AGREEMENTS}?bank=${encodeURIComponent(bankFilter)}` : ENDPOINTS.AGREEMENTS;
    api
      .get<{ id: string; name: string }[] | { results: { id: string; name: string }[] }>(url)
      .then((res) => {
        const list = Array.isArray(res) ? res : res.results || [];
        setAgreements(list);
        setAgreementFilter((current) =>
          current && list.some((item) => item.id === current) ? current : '',
        );
      })
      .catch(() => setAgreements([]));
  }, [bankFilter]);

  const extraParams = useMemo(() => {
    const p: Record<string, string> = {};
    if (bankFilter) p.bank = bankFilter;
    if (agreementFilter) p.agreement = agreementFilter;
    if (codeFilter) p.code_in_bank = codeFilter;
    return p;
  }, [bankFilter, agreementFilter, codeFilter]);

  async function handleExportCSV() {
    try {
      const tokens = localStorage.getItem('tokens');
      const accessToken = tokens ? JSON.parse(tokens).access : '';
      
      const response = await fetch(`${API_URL}${ENDPOINTS.TABLES_EXPORT_CSV}`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
      
      if (!response.ok) throw new Error('Erro ao exportar');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tabelas_${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('Tabelas exportadas com sucesso!');
    } catch (error) {
      toast.error('Erro ao exportar tabelas');
    }
  }

  function handleImportSuccess() {
    setRefreshKey((prev) => prev + 1);
    setImportModalOpen(false);
  }

  const customActions = (
    <div className="flex gap-2">
      <Button variant="secondary" onClick={handleExportCSV} size="sm">
        <Download size={16} />
        Exportar CSV
      </Button>
      <Button variant="secondary" onClick={() => setImportModalOpen(true)} size="sm">
        <Upload size={16} />
        Importar CSV
      </Button>
    </div>
  );

  const filterBar = (
    <>
      <SearchSelect
        className="w-full sm:w-52"
        placeholder="Todos os bancos"
        allowEmpty
        value={bankFilter}
        options={bankOptions}
        onChange={(e) => setBankFilter(e.target.value)}
      />
      <SearchSelect
        className="w-full sm:w-52"
        placeholder="Todos os convênios"
        allowEmpty
        value={agreementFilter}
        options={agreementOptions}
        onChange={(e) => setAgreementFilter(e.target.value)}
      />
      <input
        type="text"
        value={codeFilter}
        onChange={(e) => setCodeFilter(e.target.value)}
        placeholder="Filtrar por código"
        className="text-sm border border-gray-200 rounded-lg px-3 py-2 outline-none focus:border-[var(--color-primary)] bg-white text-gray-700"
      />
    </>
  );

  return (
    <>
      <CrudPage
        key={refreshKey}
        title="Tabelas"
        endpoint={ENDPOINTS.TABLES}
        formFieldsEndpoint={ENDPOINTS.FORM_FIELDS_TABLES}
        columns={columns}
        createLabel="Nova Tabela"
        searchPlaceholder="Buscar tabela..."
        customActions={customActions}
        filterBar={filterBar}
        extraParams={extraParams}
        selectable
        bulkDeleteEndpoint={ENDPOINTS.TABLES_BULK_DELETE}
        renderForm={({ item, onSubmit, onClose, saving }) => (
          <TableRangesForm
            item={item}
            onSubmit={onSubmit}
            onClose={onClose}
            saving={saving}
          />
        )}
      />
      
      <TableCSVImport
        isOpen={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        onSuccess={handleImportSuccess}
      />
    </>
  );
}
