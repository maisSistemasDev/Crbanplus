import { useEffect, useMemo, useState } from 'react';
import { FileText, X } from 'lucide-react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { formatCurrency, formatDate } from '../../../../lib/utils/format';
import type { Agreement, Bank, Proposal } from '../../../../lib/api/types';
import { PageHeader } from '../../ui/PageHeader';
import { Button } from '../../ui/Button';
import { StatusBadge } from '../../ui/Badge';
import { EmptyState } from '../../ui/EmptyState';
import { SectionSpinner } from '../../ui/Spinner';
import { SearchSelect } from '../../ui/SearchSelect';

interface ProposalListResponse {
  count: number;
  page: number;
  page_size: number;
  results: Proposal[];
}

const PAGE_SIZE = 20;

interface ProposalFilters {
  personType: 'cpf' | 'cnpj';
  personDocument: string;
  clientName: string;
  bank: string;
  agreement: string;
  contractNumber: string;
  dateMode: 'dia' | 'periodo';
  dayDate: string;
  beginDate: string;
  endDate: string;
}

const INITIAL_FILTERS: ProposalFilters = {
  personType: 'cpf',
  personDocument: '',
  clientName: '',
  bank: '',
  agreement: '',
  contractNumber: '',
  dateMode: 'dia',
  dayDate: '',
  beginDate: '',
  endDate: '',
};

function countBulkValues(value: string): number {
  return value
    .split(/[\n\r,;]+/)
    .map((part) => part.trim())
    .filter(Boolean).length;
}

function BulkSearchModal({
  title,
  placeholder,
  value,
  onClose,
  onApply,
}: {
  title: string;
  placeholder: string;
  value: string;
  onClose: () => void;
  onApply: (next: string) => void;
}) {
  const [draft, setDraft] = useState(value);
  const count = countBulkValues(draft);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
          <h2 className="text-base font-semibold text-gray-800">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100"
          >
            <X size={18} />
          </button>
        </div>
        <div className="px-5 py-4">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={10}
            placeholder={placeholder}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm outline-none focus:border-[var(--color-primary)]"
          />
          <p className="mt-2 text-xs text-gray-500">
            Um valor por linha. {count > 0 ? `${count} item(ns) informado(s).` : 'Cole a lista e aplique para filtrar.'}
          </p>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-gray-100 px-5 py-3">
          <Button variant="secondary" size="sm" type="button" onClick={onClose}>
            Cancelar
          </Button>
          <Button size="sm" type="button" onClick={() => onApply(draft)}>
            Aplicar
          </Button>
        </div>
      </div>
    </div>
  );
}

export function ProposalList() {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<ProposalFilters>(INITIAL_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<ProposalFilters>(INITIAL_FILTERS);
  const [bulkDocuments, setBulkDocuments] = useState('');
  const [appliedBulkDocuments, setAppliedBulkDocuments] = useState('');
  const [bulkContracts, setBulkContracts] = useState('');
  const [appliedBulkContracts, setAppliedBulkContracts] = useState('');
  const [bulkModal, setBulkModal] = useState<null | 'cpf' | 'contract'>(null);
  const [banks, setBanks] = useState<Bank[]>([]);
  const [agreements, setAgreements] = useState<Agreement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const bankOptions = useMemo(() => banks.map((bank) => ({ value: bank.id, label: bank.name })), [banks]);
  const agreementOptions = useMemo(
    () => agreements.map((agreement) => ({ value: agreement.id, label: agreement.name })),
    [agreements],
  );

  useEffect(() => {
    api
      .get<Bank[]>(ENDPOINTS.BANKS)
      .then((res) => setBanks(Array.isArray(res) ? res : []))
      .catch(() => {});

    api
      .get<Agreement[]>(ENDPOINTS.AGREEMENTS)
      .then((res) => setAgreements(Array.isArray(res) ? res : []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError('');
      try {
        const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
        if (appliedBulkDocuments || appliedFilters.personDocument) {
          params.set('client_cpf', appliedBulkDocuments || appliedFilters.personDocument);
        }
        if (appliedFilters.clientName) params.set('search', appliedFilters.clientName);
        if (appliedFilters.bank) params.set('bank', appliedFilters.bank);
        if (appliedFilters.agreement) params.set('agreement', appliedFilters.agreement);
        if (appliedBulkContracts || appliedFilters.contractNumber) {
          params.set('contract_number', appliedBulkContracts || appliedFilters.contractNumber);
        }

        if (appliedFilters.dateMode === 'dia' && appliedFilters.dayDate) {
          params.set('begin_date', appliedFilters.dayDate);
          params.set('end_date', appliedFilters.dayDate);
        }

        if (
          appliedFilters.dateMode === 'periodo' &&
          appliedFilters.beginDate &&
          appliedFilters.endDate
        ) {
          params.set('begin_date', appliedFilters.beginDate);
          params.set('end_date', appliedFilters.endDate);
        }

        const res = await api.get<ProposalListResponse>(`${ENDPOINTS.PROPOSALS}?${params}`);
        if (cancelled) return;
        setProposals(res.results);
        setCount(res.count);
      } catch (err) {
        if (!cancelled) setError(extractErrorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [page, appliedFilters, appliedBulkDocuments, appliedBulkContracts]);

  function updateFilter<K extends keyof ProposalFilters>(key: K, value: ProposalFilters[K]) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  function handleSearch() {
    setPage(1);
    setAppliedFilters(filters);
    setAppliedBulkDocuments(bulkDocuments);
    setAppliedBulkContracts(bulkContracts);
  }

  function clearFilters() {
    setFilters(INITIAL_FILTERS);
    setBulkDocuments('');
    setBulkContracts('');
    setAppliedBulkDocuments('');
    setAppliedBulkContracts('');
    setPage(1);
    setAppliedFilters(INITIAL_FILTERS);
  }

  function applyBulk(kind: 'cpf' | 'contract', next: string) {
    const first = next
      .split(/[\n\r,;]+/)
      .map((part) => part.trim())
      .filter(Boolean)[0] || '';
    const isSingle = countBulkValues(next) <= 1;

    if (kind === 'cpf') {
      setBulkDocuments(next);
      updateFilter('personDocument', isSingle ? first : filters.personDocument);
      setAppliedBulkDocuments(next);
      setAppliedBulkContracts(bulkContracts);
    } else {
      setBulkContracts(next);
      updateFilter('contractNumber', isSingle ? first : filters.contractNumber);
      setAppliedBulkContracts(next);
      setAppliedBulkDocuments(bulkDocuments);
    }
    setAppliedFilters(filters);
    setPage(1);
    setBulkModal(null);
  }

  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));

  return (
    <div>
      <PageHeader title="Minhas Propostas" subtitle="Consulta de propostas" />

      <div className="card">
        <div className="mb-4 rounded-md border border-gray-300">
            <div className="grid gap-0 border-t-2 border-t-amber-500 md:grid-cols-2">
            <div className="flex flex-wrap items-center gap-2 border-b border-gray-200 px-3 py-2 text-sm md:border-r">
              <label className="inline-flex items-center gap-1.5">
                <input
                  type="radio"
                  name="personType"
                  checked={filters.personType === 'cpf'}
                  onChange={() => updateFilter('personType', 'cpf')}
                />
                CPF
              </label>
              <label className="inline-flex items-center gap-1.5">
                <input
                  type="radio"
                  name="personType"
                  checked={filters.personType === 'cnpj'}
                  onChange={() => updateFilter('personType', 'cnpj')}
                />
                CNPJ
              </label>
              <input
                type="text"
                value={countBulkValues(bulkDocuments) > 1 ? `${countBulkValues(bulkDocuments)} CPFs` : filters.personDocument}
                onChange={(e) => {
                  updateFilter('personDocument', e.target.value);
                  if (countBulkValues(bulkDocuments) <= 1) setBulkDocuments(e.target.value);
                }}
                disabled={countBulkValues(bulkDocuments) > 1}
                className="h-8 flex-1 rounded border border-gray-300 px-2 text-sm outline-none focus:border-[var(--color-primary)] disabled:bg-gray-50"
              />
              <button
                type="button"
                onClick={() => setBulkModal('cpf')}
                className="rounded bg-amber-400 px-2.5 py-1 text-sm font-medium text-gray-900"
              >
                {countBulkValues(bulkDocuments) > 1 ? `+ CPFs (${countBulkValues(bulkDocuments)})` : '+ CPFs'}
              </button>
            </div>

            <div className="flex flex-col gap-1 border-b border-gray-200 px-3 py-2 text-sm sm:grid sm:grid-cols-[140px_1fr] sm:items-center">
              <span>Nome do cliente:</span>
              <input
                type="text"
                value={filters.clientName}
                onChange={(e) => updateFilter('clientName', e.target.value)}
                className="h-8 rounded border border-gray-300 px-2 text-sm outline-none focus:border-[var(--color-primary)]"
              />
            </div>

            <div className="flex flex-col gap-1 border-b border-gray-200 px-3 py-2 text-sm sm:grid sm:grid-cols-[140px_1fr] sm:items-center md:border-r">
              <span>Averbador:</span>
              <SearchSelect
                compact
                placeholder="Selecione"
                allowEmpty
                value={filters.bank}
                options={bankOptions}
                onChange={(value) => updateFilter('bank', value)}
              />
            </div>

            <div className="flex flex-col gap-1 border-b border-gray-200 px-3 py-2 text-sm sm:grid sm:grid-cols-[140px_1fr] sm:items-center">
              <span>Convenio:</span>
              <SearchSelect
                compact
                placeholder="Selecione"
                allowEmpty
                value={filters.agreement}
                options={agreementOptions}
                onChange={(value) => updateFilter('agreement', value)}
              />
            </div>

            <div className="flex flex-col gap-1 border-b border-gray-200 px-3 py-2 text-sm sm:grid sm:grid-cols-[140px_1fr] sm:items-center md:border-r">
              <span>Bordero:</span>
              <input
                type="text"
                disabled
                className="h-8 rounded border border-gray-200 bg-gray-50 px-2 text-sm text-gray-400"
              />
            </div>

            <div className="flex flex-col gap-1 border-b border-gray-200 px-3 py-2 text-sm sm:flex-row sm:items-center sm:gap-2">
              <span className="sm:w-[140px] sm:shrink-0">Codigo da Proposta:</span>
              <input
                type="text"
                value={countBulkValues(bulkContracts) > 1 ? `${countBulkValues(bulkContracts)} propostas` : filters.contractNumber}
                onChange={(e) => {
                  updateFilter('contractNumber', e.target.value);
                  if (countBulkValues(bulkContracts) <= 1) setBulkContracts(e.target.value);
                }}
                disabled={countBulkValues(bulkContracts) > 1}
                className="h-8 flex-1 rounded border border-gray-300 px-2 text-sm outline-none focus:border-[var(--color-primary)] disabled:bg-gray-50"
              />
              <button
                type="button"
                onClick={() => setBulkModal('contract')}
                className="rounded bg-amber-400 px-2.5 py-1 text-sm font-medium text-gray-900"
              >
                {countBulkValues(bulkContracts) > 1 ? `+ Propostas (${countBulkValues(bulkContracts)})` : '+ Propostas'}
              </button>
            </div>

            <div className="flex flex-col gap-1 border-b border-gray-200 px-3 py-2 text-sm sm:grid sm:grid-cols-[140px_1fr] sm:items-center md:border-r">
              <span>Fisico:</span>
              <SearchSelect
                compact
                disabled
                placeholder="TODOS"
                value=""
                options={[]}
                onChange={() => {}}
              />
            </div>

            <div className="flex flex-col gap-1 border-b border-gray-200 px-3 py-2 text-sm sm:grid sm:grid-cols-[140px_1fr] sm:items-center">
              <span>Pendencias:</span>
              <SearchSelect
                compact
                disabled
                className="w-[130px]"
                placeholder="Ambos"
                value=""
                options={[]}
                onChange={() => {}}
              />
            </div>

            <div className="flex flex-col gap-2 border-b border-gray-200 px-3 py-2 text-sm md:col-span-2 sm:grid sm:grid-cols-[140px_1fr] sm:items-center">
              <span>Data Cadastro:</span>
              <div className="flex flex-wrap items-center gap-4">
                <label className="inline-flex items-center gap-1.5">
                  <input
                    type="radio"
                    name="dateMode"
                    checked={filters.dateMode === 'dia'}
                    onChange={() => updateFilter('dateMode', 'dia')}
                  />
                  Dia
                </label>
                <label className="inline-flex items-center gap-1.5">
                  <input
                    type="radio"
                    name="dateMode"
                    checked={filters.dateMode === 'periodo'}
                    onChange={() => updateFilter('dateMode', 'periodo')}
                  />
                  Periodo
                </label>

                {filters.dateMode === 'dia' ? (
                  <input
                    type="date"
                    value={filters.dayDate}
                    onChange={(e) => updateFilter('dayDate', e.target.value)}
                    className="h-8 rounded border border-gray-300 px-2 text-sm outline-none focus:border-[var(--color-primary)]"
                  />
                ) : (
                  <div className="flex flex-wrap items-center gap-2">
                    <input
                      type="date"
                      value={filters.beginDate}
                      onChange={(e) => updateFilter('beginDate', e.target.value)}
                      className="h-8 rounded border border-gray-300 px-2 text-sm outline-none focus:border-[var(--color-primary)]"
                    />
                    <span className="text-xs text-gray-500">ate</span>
                    <input
                      type="date"
                      value={filters.endDate}
                      onChange={(e) => updateFilter('endDate', e.target.value)}
                      className="h-8 rounded border border-gray-300 px-2 text-sm outline-none focus:border-[var(--color-primary)]"
                    />
                  </div>
                )}
              </div>
            </div>

            <div className="px-3 py-3 md:col-span-2">
              <div className="flex flex-wrap items-center justify-center gap-2">
                <Button onClick={handleSearch} size="sm">
                  Buscar
                </Button>
                <Button variant="secondary" size="sm" onClick={clearFilters}>
                  Limpar filtros
                </Button>
              </div>
            </div>
          </div>
        </div>

        {loading ? (
          <SectionSpinner />
        ) : error ? (
          <p className="py-6 text-center text-sm text-red-600">{error}</p>
        ) : proposals.length === 0 ? (
          <EmptyState icon={FileText} title="Nenhuma proposta encontrada" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase text-[var(--color-text-muted)]">
                  <th className="py-2 pr-3">Contrato</th>
                  <th className="py-2 pr-3">Cliente</th>
                  <th className="py-2 pr-3">Vendedor</th>
                  <th className="py-2 pr-3">Banco</th>
                  <th className="py-2 pr-3">Convênio / Tabela</th>
                  <th className="py-2 pr-3">Valor</th>
                  <th className="py-2 pr-3">Comissão</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Status Pagamento</th>
                  <th className="py-2 pr-3">Liberação</th>
                </tr>
              </thead>
              <tbody>
                {proposals.map((proposal) => (
                  <tr key={proposal.id} className="border-b border-gray-100">
                    <td className="py-2 pr-3 font-mono text-xs">{proposal.contract_number}</td>
                    <td className="py-2 pr-3">
                      <p className="font-medium text-[var(--color-text)]">{proposal.client_name || '—'}</p>
                      <p className="text-xs text-[var(--color-text-muted)]">{proposal.client_document}</p>
                    </td>
                    <td className="py-2 pr-3">
                      {proposal.seller_details
                        ? `${proposal.seller_details.first_name} ${proposal.seller_details.last_name}`
                        : '—'}
                    </td>
                    <td className="py-2 pr-3">{proposal.bank_details?.name || '—'}</td>
                    <td className="py-2 pr-3">
                      <p>{proposal.agreement_details?.name || '—'}</p>
                      <p className="text-xs text-[var(--color-text-muted)]">
                        {proposal.table_details?.name_in_bank || '—'}
                      </p>
                    </td>
                    <td className="py-2 pr-3 font-medium text-emerald-600">{formatCurrency(proposal.amount)}</td>
                    <td className="py-2 pr-3 font-medium text-emerald-700">
                      {proposal.commission_value == null ? '—' : formatCurrency(proposal.commission_value)}
                    </td>
                    <td className="py-2 pr-3">
                      <StatusBadge status="processed" />
                    </td>
                    <td className="py-2 pr-3">
                      <StatusBadge status={proposal.payment_status || proposal.status || 'pending'} />
                    </td>
                    <td className="py-2 pr-3">{formatDate(proposal.disbursement_date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && count > PAGE_SIZE && (
          <div className="mt-4 flex flex-col gap-3 text-sm text-[var(--color-text-muted)] sm:flex-row sm:items-center sm:justify-between">
            <span>
              Página {page} de {totalPages} · {count} propostas
            </span>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Anterior
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Próxima
              </Button>
            </div>
          </div>
        )}
      </div>

      {bulkModal === 'cpf' && (
        <BulkSearchModal
          title="Pesquisar CPFs"
          placeholder={'123.456.789-00\n987.654.321-00'}
          value={bulkDocuments || filters.personDocument}
          onClose={() => setBulkModal(null)}
          onApply={(next) => applyBulk('cpf', next)}
        />
      )}
      {bulkModal === 'contract' && (
        <BulkSearchModal
          title="Pesquisar propostas"
          placeholder={'A00797B7\nA00733ZN'}
          value={bulkContracts || filters.contractNumber}
          onClose={() => setBulkModal(null)}
          onApply={(next) => applyBulk('contract', next)}
        />
      )}
    </div>
  );
}
