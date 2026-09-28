import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Button } from '../../ui/Button';
import { Badge } from '../../ui/Badge';
import { SearchInput } from '../../ui/SearchInput';
import { PageSpinner } from '../../ui/Spinner';
import clsx from 'clsx';
import { Link, Unlink, Save, Play, ChevronLeft, ChevronRight } from 'lucide-react';
import toast from 'react-hot-toast';
import type { PaginatedResponse } from '../../../../lib/api/types';

// ===== Types =====

interface RelationItem {
  name_in_bank: string;
  id: string | null;
  name: string | null;
}

interface PreviewResponse {
  relation_tables: RelationItem[];
  relation_users: RelationItem[];
  relation_agreements: RelationItem[];
  relation_statuses: RelationItem[];
}

interface OptionItem {
  id: string | number;
  name?: string;
  first_name?: string;
  last_name?: string;
  // Table fields
  name_in_bank?: string;
  agreement_name?: string;
  description?: string;
  bank_name?: string;
}

interface ValueMatcherProps {
  batchId: string;
  bankId: string;
  onProcessStart: () => void;
}

type CategoryKey = 'users' | 'agreements' | 'tables' | 'statuses';

interface CategoryConfig {
  key: CategoryKey;
  label: string;
  relationKey: keyof PreviewResponse;
}

const CATEGORIES: CategoryConfig[] = [
  { key: 'users', label: 'Digitadores / Acessos', relationKey: 'relation_users' },
  { key: 'agreements', label: 'Convenios', relationKey: 'relation_agreements' },
  { key: 'tables', label: 'Tabelas', relationKey: 'relation_tables' },
  { key: 'statuses', label: 'Status', relationKey: 'relation_statuses' },
];

const PAIR_COLORS = [
  'bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500',
  'bg-pink-500', 'bg-cyan-500', 'bg-yellow-500', 'bg-red-500',
  'bg-indigo-500', 'bg-teal-500', 'bg-lime-500', 'bg-fuchsia-500',
  'bg-rose-500', 'bg-emerald-500', 'bg-violet-500', 'bg-amber-500',
];

const ENTITY_PAGE_SIZE = 25;
const SEARCH_DEBOUNCE_MS = 400;

function extractList<T>(val: T[] | PaginatedResponse<T> | { results: T[] }): T[] {
  if (Array.isArray(val)) return val;
  return (val as PaginatedResponse<T>).results ?? [];
}

function extractCount<T>(val: T[] | PaginatedResponse<T>): number {
  if (Array.isArray(val)) return val.length;
  return (val as PaginatedResponse<T>).count ?? 0;
}

// ===== Component =====

export function ValueMatcher({ batchId, bankId, onProcessStart }: ValueMatcherProps) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [activeTab, setActiveTab] = useState<CategoryKey>('users');

  // Mappings: category -> { name_in_bank -> entity_id }
  const [mappings, setMappings] = useState<Record<CategoryKey, Record<string, string>>>({
    tables: {}, users: {}, agreements: {}, statuses: {},
  });

  // Entidades do painel direito (paginado para users/tables)
  const [entityOptions, setEntityOptions] = useState<OptionItem[]>([]);
  const [entityTotal, setEntityTotal] = useState(0);
  const [entityPage, setEntityPage] = useState(1);
  const [entityOptionsLoading, setEntityOptionsLoading] = useState(false);

  // Convênios e status (listas menores, carregadas uma vez)
  const [staticOptions, setStaticOptions] = useState<{ agreements: OptionItem[]; statuses: OptionItem[] }>({
    agreements: [],
    statuses: [],
  });
  const staticLoadedRef = useRef({ agreements: false, statuses: false });

  // Cache de entidades já usadas no mapeamento (rótulos fora da página atual)
  const [entityCache, setEntityCache] = useState<Record<string, OptionItem>>({});

  // Selection: which file value is selected (waiting for right-side click)
  const [selectedFileValue, setSelectedFileValue] = useState<string | null>(null);

  // Search
  const [searchLeft, setSearchLeft] = useState('');
  const [searchRight, setSearchRight] = useState('');
  const [searchRightDebounced, setSearchRightDebounced] = useState('');

  // ===== Data fetching =====

  const fetchPreview = useCallback(async () => {
    try {
      const data = await api.get<PreviewResponse>(ENDPOINTS.PROPOSAL_PREVIEW(batchId));
      setPreview(data);
      const m: Record<CategoryKey, Record<string, string>> = {
        tables: {}, users: {}, agreements: {}, statuses: {},
      };
      for (const cat of CATEGORIES) {
        for (const item of data[cat.relationKey]) {
          if (item.id) m[cat.key][item.name_in_bank] = String(item.id);
        }
      }
      setMappings(m);
    } catch {
      toast.error('Erro ao carregar preview do lote');
    }
  }, [batchId]);

  const usesServerEntitySearch = activeTab === 'users' || activeTab === 'tables';

  const fetchStaticOptions = useCallback(async (category: 'agreements' | 'statuses') => {
    if (staticLoadedRef.current[category]) return;
    try {
      if (category === 'agreements') {
        const res = await api.get<OptionItem[] | PaginatedResponse<OptionItem>>(ENDPOINTS.AGREEMENTS);
        setStaticOptions((prev) => ({ ...prev, agreements: extractList(res) }));
      } else {
        const res = await api.get<OptionItem[] | PaginatedResponse<OptionItem>>(
          `${ENDPOINTS.STATUS_PAYMENT}?bank_id=${bankId}`,
        );
        setStaticOptions((prev) => ({ ...prev, statuses: extractList(res) }));
      }
      staticLoadedRef.current[category] = true;
    } catch {
      toast.error(category === 'agreements' ? 'Erro ao carregar convênios' : 'Erro ao carregar status');
    }
  }, [bankId]);

  const fetchEntityOptions = useCallback(async () => {
    if (activeTab === 'agreements' || activeTab === 'statuses') {
      await fetchStaticOptions(activeTab);
      return;
    }

    setEntityOptionsLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(entityPage),
        page_size: String(ENTITY_PAGE_SIZE),
      });
      if (searchRightDebounced) params.set('search', searchRightDebounced);

      let res: OptionItem[] | PaginatedResponse<OptionItem>;
      if (activeTab === 'users') {
        res = await api.get<OptionItem[] | PaginatedResponse<OptionItem>>(`${ENDPOINTS.SELLERS}?${params}`);
      } else {
        params.set('bank', bankId);
        res = await api.get<OptionItem[] | PaginatedResponse<OptionItem>>(`${ENDPOINTS.TABLES}?${params}`);
      }

      setEntityOptions(extractList(res));
      setEntityTotal(extractCount(res));
    } catch {
      setEntityOptions([]);
      setEntityTotal(0);
      toast.error('Erro ao carregar entidades');
    } finally {
      setEntityOptionsLoading(false);
    }
  }, [activeTab, bankId, entityPage, searchRightDebounced, fetchStaticOptions]);

  useEffect(() => {
    (async () => {
      setLoading(true);
      await fetchPreview();
      setLoading(false);
    })();
  }, [fetchPreview]);

  useEffect(() => {
    const t = setTimeout(() => {
      setSearchRightDebounced(searchRight);
      setEntityPage(1);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [searchRight]);

  useEffect(() => {
    if (loading || !preview) return;
    fetchEntityOptions();
  }, [loading, preview, fetchEntityOptions]);

  // Reset selection on tab change
  useEffect(() => {
    setSelectedFileValue(null);
    setSearchLeft('');
    setSearchRight('');
    setSearchRightDebounced('');
    setEntityPage(1);
    if (activeTab === 'users' || activeTab === 'tables') {
      setEntityOptions([]);
      setEntityTotal(0);
    }
  }, [activeTab]);

  // ===== Helpers =====

  function getOptionLabel(category: CategoryKey, item: OptionItem): string {
    if (category === 'users') {
      const parts = [item.first_name, item.last_name].filter(Boolean);
      return parts.length ? parts.join(' ') : item.name || String(item.id);
    }
    if (category === 'tables') {
      const tableName = item.name_in_bank || item.description || item.name;
      if (tableName && item.agreement_name) return `${item.agreement_name} - ${tableName}`;
      return tableName || item.agreement_name || String(item.id);
    }
    return item.name || String(item.id);
  }

  function getMappedEntityName(entityId: string): string {
    const cached = entityCache[entityId];
    if (cached) return getOptionLabel(activeTab, cached);
    const opt = entityOptions.find((o) => String(o.id) === entityId);
    if (opt) return getOptionLabel(activeTab, opt);
    const cat = CATEGORIES.find((c) => c.key === activeTab)!;
    const item = preview?.[cat.relationKey].find((i) => String(i.id) === entityId);
    return item?.name || entityId;
  }

  function getPairColorIndex(nameInBank: string): number {
    return Object.keys(mappings[activeTab]).indexOf(nameInBank);
  }

  function getFileValuesForEntity(entityId: string): string[] {
    const result: string[] = [];
    for (const [name, id] of Object.entries(mappings[activeTab])) {
      if (id === entityId) result.push(name);
    }
    return result;
  }

  // ===== Interactions =====

  function handleFileValueClick(nameInBank: string) {
    const isMapped = !!mappings[activeTab][nameInBank];
    if (isMapped) {
      // Unmap
      setMappings((prev) => {
        const copy = { ...prev[activeTab] };
        delete copy[nameInBank];
        return { ...prev, [activeTab]: copy };
      });
      setSelectedFileValue(null);
    } else if (selectedFileValue === nameInBank) {
      setSelectedFileValue(null);
    } else {
      setSelectedFileValue(nameInBank);
    }
  }

  function handleEntityClick(entityId: string, entity?: OptionItem) {
    if (!selectedFileValue) return;
    if (entity) {
      setEntityCache((prev) => ({ ...prev, [entityId]: entity }));
    }
    // Multiple file values CAN map to the same entity (N:1)
    setMappings((prev) => ({
      ...prev,
      [activeTab]: { ...prev[activeTab], [selectedFileValue!]: entityId },
    }));
    setSelectedFileValue(null);
  }

  // ===== Save & Process =====

  function buildRelationships(category: CategoryKey, items: RelationItem[]) {
    const catMappings = mappings[category];
    // Group active mappings: entity_id -> [names_in_bank]
    const grouped: Record<string, string[]> = {};
    for (const item of items) {
      const selectedId = catMappings[item.name_in_bank];
      if (selectedId) {
        if (!grouped[selectedId]) grouped[selectedId] = [];
        grouped[selectedId].push(item.name_in_bank);
      }
    }
    // For items that WERE matched (preview had id) but are now unmapped:
    // send names_in_bank: [] to clear the alias on that entity
    for (const item of items) {
      if (item.id && !catMappings[item.name_in_bank] && !grouped[String(item.id)]) {
        grouped[String(item.id)] = [];
      }
    }
    return Object.entries(grouped).map(([id, names]) => ({ id, names_in_bank: names }));
  }

  async function handleSave() {
    if (!preview) return false;
    setSaving(true);
    try {
      const promises: Promise<unknown>[] = [];
      const am = buildRelationships('agreements', preview.relation_agreements);
      if (am.length) promises.push(api.post(ENDPOINTS.AGREEMENT_NAMES, { relationships: am }));
      if (preview.relation_tables.length > 0) {
        const tm = buildRelationships('tables', preview.relation_tables);
        promises.push(api.post(ENDPOINTS.TABLE_NAMES, { bank_id: bankId, relationships: tm }));
      }
      const um = buildRelationships('users', preview.relation_users);
      if (um.length) promises.push(api.post(ENDPOINTS.USER_NAMES, { proposal_batch: batchId, relationships: um }));
      const sm = buildRelationships('statuses', preview.relation_statuses);
      if (sm.length) promises.push(api.post(ENDPOINTS.STATUS_PAYMENT, { relationships: sm }));

      await Promise.all(promises);
      toast.success('Mapeamentos salvos!');
      await fetchPreview();
      return true;
    } catch {
      toast.error('Erro ao salvar mapeamentos');
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function handleProcess() {
    if (!preview) return;
    setProcessing(true);
    try {
      const saved = await handleSave();
      if (!saved) return;
      await api.upload(ENDPOINTS.BATCH_DETAIL(batchId), new FormData(), 'PUT');
      toast.success('Processamento iniciado!');
      onProcessStart();
    } catch {
      toast.error('Erro ao iniciar processamento');
    } finally {
      setProcessing(false);
    }
  }

  // ===== Render =====

  if (loading) return <PageSpinner />;
  if (!preview) return null;

  const activeCat = CATEGORIES.find((c) => c.key === activeTab)!;
  const fileValues = preview[activeCat.relationKey];
  const catMappings = mappings[activeTab];

  const staticEntityList = activeTab === 'agreements'
    ? staticOptions.agreements
    : activeTab === 'statuses'
      ? staticOptions.statuses
      : entityOptions;

  const filteredLeft = fileValues.filter((i) =>
    i.name_in_bank.toLowerCase().includes(searchLeft.toLowerCase()),
  );

  const filteredRight = (() => {
    if (usesServerEntitySearch) return entityOptions;
    const q = searchRight.toLowerCase();
    if (!q) return staticEntityList;
    return staticEntityList.filter((i) =>
      getOptionLabel(activeTab, i).toLowerCase().includes(q),
    );
  })();

  const entityPageCount = usesServerEntitySearch
    ? Math.max(1, Math.ceil(entityTotal / ENTITY_PAGE_SIZE))
    : 1;

  const totalPending = CATEGORIES.reduce((acc, cat) => {
    return acc + preview[cat.relationKey].filter((i) => !mappings[cat.key][i.name_in_bank]).length;
  }, 0);
  const hasAnyValues = CATEGORIES.some((cat) => preview[cat.relationKey].length > 0);
  const allMapped = totalPending === 0 && hasAnyValues;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Resolucao de Valores</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {selectedFileValue
              ? <span>Clique na entidade para mapear <strong>"{selectedFileValue}"</strong></span>
              : 'Clique em um valor do arquivo, depois na entidade correspondente'}
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          {allMapped ? (
            <Badge variant="success">Pronto para processar</Badge>
          ) : totalPending > 0 ? (
            <Badge variant="warning">{totalPending} pendente{totalPending !== 1 ? 's' : ''}</Badge>
          ) : null}
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-200">
        {CATEGORIES.map((cat) => {
          const items = preview[cat.relationKey];
          const pending = items.filter((i) => !mappings[cat.key][i.name_in_bank]).length;
          const total = items.length;
          return (
            <button
              key={cat.key}
              onClick={() => setActiveTab(cat.key)}
              className={clsx(
                'px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-2',
                activeTab === cat.key
                  ? 'border-[var(--color-primary)] text-[var(--color-primary)]'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
              )}
            >
              {cat.label}
              {total > 0 && (
                <span className={clsx(
                  'text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center',
                  pending > 0 ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700',
                )}>
                  {pending > 0 ? pending : <span>&#10003;</span>}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Two side-by-side panels */}
      {fileValues.length === 0 ? (
        <div className="text-center py-12 text-gray-400 bg-white rounded-xl border border-gray-100">
          Nenhum valor encontrado nesta categoria
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          {/* LEFT: File Values */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
              <h3 className="font-semibold text-sm text-gray-700">Valores do Arquivo</h3>
              <p className="text-xs text-gray-500 mt-0.5">Clique para selecionar ou desfazer mapeamento</p>
            </div>
            <div className="px-3 py-2 border-b border-gray-100">
              <SearchInput value={searchLeft} onChange={setSearchLeft} placeholder="Buscar valor..." />
            </div>
            <div className="divide-y divide-gray-50 max-h-[420px] overflow-y-auto">
              {filteredLeft.map((item) => {
                const isMapped = !!catMappings[item.name_in_bank];
                const isSelected = selectedFileValue === item.name_in_bank;
                const colorIdx = isMapped ? getPairColorIndex(item.name_in_bank) : -1;

                return (
                  <button
                    key={item.name_in_bank}
                    onClick={() => handleFileValueClick(item.name_in_bank)}
                    className={clsx(
                      'w-full px-4 py-3 text-left flex items-center gap-3 transition-colors',
                      isSelected && 'bg-[var(--color-primary-bg)] ring-2 ring-inset ring-[var(--color-primary)]',
                      isMapped && !isSelected && 'bg-green-50 hover:bg-green-100',
                      !isMapped && !isSelected && 'hover:bg-gray-50',
                    )}
                  >
                    {isMapped ? (
                      <span className={clsx('h-3 w-3 rounded-full shrink-0', PAIR_COLORS[colorIdx % PAIR_COLORS.length])} />
                    ) : (
                      <span className="h-3 w-3 rounded-full shrink-0 border-2 border-gray-300" />
                    )}
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-gray-800 break-all">{item.name_in_bank}</span>
                      {isMapped && (
                        <p className="text-xs text-green-600 mt-0.5 flex items-center gap-1">
                          <Link size={10} /> {getMappedEntityName(catMappings[item.name_in_bank])}
                        </p>
                      )}
                    </div>
                    {isMapped && <Unlink size={14} className="text-gray-400 shrink-0 hover:text-red-500" />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* RIGHT: System Entities */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
              <h3 className="font-semibold text-sm text-gray-700">Entidades do Sistema</h3>
              <p className="text-xs text-gray-500 mt-0.5">
                {selectedFileValue
                  ? <span>Clique para mapear <strong>"{selectedFileValue}"</strong></span>
                  : 'Selecione um valor do arquivo primeiro'}
              </p>
            </div>
            <div className="px-3 py-2 border-b border-gray-100">
              <SearchInput
                value={searchRight}
                onChange={setSearchRight}
                placeholder={usesServerEntitySearch ? 'Buscar por nome, CPF, e-mail...' : 'Buscar entidade...'}
              />
            </div>
            <div className="divide-y divide-gray-50 max-h-[420px] overflow-y-auto relative">
              {entityOptionsLoading && usesServerEntitySearch && (
                <div className="absolute inset-0 bg-white/60 flex items-center justify-center z-10">
                  <PageSpinner />
                </div>
              )}
              {filteredRight.map((entity) => {
                const entityId = String(entity.id);
                const pairedFileValues = getFileValuesForEntity(entityId);
                const isPaired = pairedFileValues.length > 0;
                const colorIdx = isPaired ? getPairColorIndex(pairedFileValues[0]) : -1;
                const canSelect = !!selectedFileValue;
                const label = getOptionLabel(activeTab, entity);

                return (
                  <button
                    key={entityId}
                    onClick={() => handleEntityClick(entityId, entity)}
                    disabled={!canSelect}
                    className={clsx(
                      'w-full px-4 py-3 text-left flex items-center gap-3 transition-colors',
                      canSelect && 'hover:bg-[var(--color-primary-bg)] cursor-pointer',
                      isPaired && !canSelect && 'bg-green-50',
                      !canSelect && !isPaired && 'opacity-50',
                    )}
                  >
                    {isPaired ? (
                      <span className={clsx('h-3 w-3 rounded-full shrink-0', PAIR_COLORS[colorIdx % PAIR_COLORS.length])} />
                    ) : (
                      <span className="h-3 w-3 rounded-full shrink-0 border-2 border-gray-300" />
                    )}
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-gray-800">{label}</span>
                      {isPaired && (
                        <div className="mt-0.5 flex flex-wrap gap-1">
                          {pairedFileValues.map((fv) => (
                            <span key={fv} className="text-xs text-green-600 flex items-center gap-0.5">
                              <Link size={9} /> {fv}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    {isPaired && (
                      <span className="text-[10px] font-bold text-green-700 bg-green-100 px-1.5 py-0.5 rounded-full shrink-0">
                        {pairedFileValues.length}
                      </span>
                    )}
                  </button>
                );
              })}
              {!entityOptionsLoading && filteredRight.length === 0 && (
                <div className="px-4 py-8 text-center text-sm text-gray-400">
                  {searchRight ? 'Nenhum resultado' : 'Nenhuma entidade disponivel'}
                </div>
              )}
            </div>
            {usesServerEntitySearch && entityTotal > 0 && (
              <div className="px-3 py-2 border-t border-gray-100 flex items-center justify-between gap-2 bg-gray-50">
                <span className="text-xs text-gray-500">
                  {entityTotal} resultado{entityTotal !== 1 ? 's' : ''}
                  {entityPageCount > 1 && ` · Página ${entityPage} de ${entityPageCount}`}
                </span>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={entityPage <= 1 || entityOptionsLoading}
                    onClick={() => setEntityPage((p) => Math.max(1, p - 1))}
                    aria-label="Página anterior"
                  >
                    <ChevronLeft size={16} />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={entityPage >= entityPageCount || entityOptionsLoading}
                    onClick={() => setEntityPage((p) => p + 1)}
                    aria-label="Próxima página"
                  >
                    <ChevronRight size={16} />
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 flex items-center justify-between">
        <div className="text-sm">
          {allMapped ? (
            <span className="text-green-600 font-medium">Todos os valores mapeados</span>
          ) : (
            <span className="text-amber-600">{totalPending} pendente{totalPending !== 1 ? 's' : ''} (sera registrado no log)</span>
          )}
        </div>
        <div className="flex gap-3">
          <Button variant="secondary" onClick={handleSave} loading={saving} disabled={saving}>
            <Save size={14} />
            Salvar Mapeamentos
          </Button>
          <Button onClick={handleProcess} loading={processing} disabled={processing}>
            <Play size={14} />
            Processar Lote
          </Button>
        </div>
      </div>
    </div>
  );
}
