import { useState, useEffect, useMemo } from 'react';
import { api } from '../../../../lib/api/client';
import { fetchAllPaginated } from '../../../../lib/api/pagination';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Button } from '../../ui/Button';
import { SearchSelect } from '../../ui/SearchSelect';
import { Trash2, Save, ChevronLeft, ChevronRight } from 'lucide-react';
import toast from 'react-hot-toast';
import clsx from 'clsx';

interface Bank {
  id: string;
  name: string;
}

interface CommissionRange {
  id: string;
  min_value: string;
  max_value: string;
  commission_rate: string;
  fixed_value?: string | null;
}

interface TableOption {
  id: string;
  name_in_bank: string | null;
  bank: string;
  bank_name?: string;
  agreement_name?: string;
  vigency_date?: string;
  commission_rate: string | null;
  commission_ranges: CommissionRange[];
}

// CommissionRules (promotora - taxa única por faixa/tabela)
interface PromoRule {
  id?: number;
  bank: string | null;
  table: string | null;
  commission_range: string | null;
  commission_rate: string;
  fixed_value?: string | null;
  // UI helpers
  _rangeLabel?: string;
}

// CommissionRulesByUser (corban - split vendedor/líder)
interface UserRule {
  id?: number;
  bank: string | null;
  table: string | null;
  commission_range: string | null;
  leader_commission_rate: string;
  seller_commission_rate: string;
  // UI helpers
  _rangeLabel?: string;
}

type RuleType = 'company' | 'group' | 'promotora';

interface CommissionRulesEditorProps {
  groupId: number;
  ruleType: RuleType;
  initialRules: PromoRule[] | UserRule[];
}

function formatCurrency(value: string) {
  return Number(value).toLocaleString('pt-BR', { minimumFractionDigits: 2 });
}

function rangeLabel(range: CommissionRange) {
  if (parseFloat(range.min_value) === 0 && parseFloat(range.max_value) === 0) {
    return '';
  }
  return `R$${formatCurrency(range.min_value)} – R$${formatCurrency(range.max_value)}`;
}

function isPlaceholderRange(range: CommissionRange) {
  if (!(parseFloat(range.min_value) === 0 && parseFloat(range.max_value) === 0)) {
    return false;
  }
  const rate = parseFloat(range.commission_rate);
  const fixed = parseFloat(String(range.fixed_value ?? ''));
  const hasRate = isFinite(rate) && rate !== 0;
  const hasFixed = isFinite(fixed) && fixed !== 0;
  return !hasRate && !hasFixed;
}

function buildRulesFromTables(tables: TableOption[], ruleType: RuleType): (PromoRule | UserRule)[] {
  const out: (PromoRule | UserRule)[] = [];
  for (const table of tables) {
    const allRanges = table.commission_ranges ?? [];
    const ranges = allRanges.filter((r) => !isPlaceholderRange(r));
    if (ranges.length > 0) {
      for (const range of ranges) {
        const rawRate = parseFloat(range.commission_rate);
        const rate = isFinite(rawRate) ? Math.max(0, rawRate) : 0;
        const rawFixed = parseFloat(String(range.fixed_value ?? ''));
        const fixed = isFinite(rawFixed) ? String(range.fixed_value) : null;
        if (ruleType === 'promotora' || ruleType === 'company') {
          out.push({
            bank: table.bank,
            table: table.id,
            commission_range: range.id,
            commission_rate: rate.toString(),
            fixed_value: fixed,
            _rangeLabel: rangeLabel(range),
          } as PromoRule);
        } else {
          out.push({
            bank: table.bank,
            table: table.id,
            commission_range: range.id,
            leader_commission_rate: rate.toString(),
            seller_commission_rate: rate.toString(),
            _rangeLabel: rangeLabel(range),
          } as UserRule);
        }
      }
    } else {
      // Quando a tabela não tem faixas, não usamos table.commission_rate como
      // default porque esse campo é a taxa base do banco (pode ser > 100).
      // A taxa de comissão da promotora/corban deve ser preenchida pelo admin.
      const rate = '0';
      if (ruleType === 'promotora' || ruleType === 'company') {
        out.push({
          bank: table.bank,
          table: table.id,
          commission_range: null,
          commission_rate: rate,
        } as PromoRule);
      } else {
        out.push({
          bank: table.bank,
          table: table.id,
          commission_range: null,
          leader_commission_rate: rate,
          seller_commission_rate: rate,
        } as UserRule);
      }
    }
  }
  return out;
}

export function CommissionRulesEditor({ groupId, ruleType, initialRules }: CommissionRulesEditorProps) {
  const [rules, setRules] = useState<(PromoRule | UserRule)[]>([]);
  const [banks, setBanks] = useState<Bank[]>([]);
  const [tables, setTables] = useState<TableOption[]>([]);
  const [bankFilter, setBankFilter] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 25;

  useEffect(() => {
    async function load() {
      try {
        const banksData = await api.get<Bank[]>(ENDPOINTS.BANKS);
        setBanks(Array.isArray(banksData) ? banksData : (banksData as any).results || []);
      } catch {
        toast.error('Erro ao carregar bancos');
      }
      try {
        const tablesList = await fetchAllPaginated<TableOption>(ENDPOINTS.TABLES);
        setTables(tablesList);
      } catch {
        toast.error('Erro ao carregar tabelas');
      }
      setLoading(false);
    }
    load();
  }, []);

  // Merge existing saved rules with all tables. Saved values win; missing tables are appended.
  useEffect(() => {
    if (loading || tables.length === 0) return;

    const baseRules = buildRulesFromTables(tables, ruleType);
    const savedByKey = new Map<string, PromoRule | UserRule>();

    (initialRules || []).forEach((saved) => {
      const key = saved.commission_range
        ? `${saved.table}::${saved.commission_range}`
        : `${saved.table}::`;
      savedByKey.set(key, saved);
    });

    const merged = baseRules.map((base) => {
      const key = base.commission_range
        ? `${base.table}::${base.commission_range}`
        : `${base.table}::`;
      const saved = savedByKey.get(key);
      if (!saved) return base;
      if (ruleType === 'promotora' || ruleType === 'company') {
        return {
          ...base,
          commission_rate: (saved as PromoRule).commission_rate,
          fixed_value: (saved as PromoRule).fixed_value,
          id: saved.id,
        };
      }
      return {
        ...base,
        leader_commission_rate: (saved as UserRule).leader_commission_rate,
        seller_commission_rate: (saved as UserRule).seller_commission_rate,
        id: saved.id,
      };
    });

    setRules(merged);
  }, [loading, tables, initialRules, ruleType]);

  const bankOptions = useMemo(() => banks.map((b) => ({ value: b.id, label: b.name })), [banks]);

  const banksById = useMemo(() => {
    const map: Record<string, Bank> = {};
    banks.forEach((b) => (map[b.id] = b));
    return map;
  }, [banks]);

  const tablesById = useMemo(() => {
    const map: Record<string, TableOption> = {};
    tables.forEach((t) => (map[t.id] = t));
    return map;
  }, [tables]);

  const filteredRules = useMemo(() => {
    if (!bankFilter) return rules;
    return rules.filter((r) => r.bank === bankFilter);
  }, [rules, bankFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredRules.length / pageSize));
  const pagedRules = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredRules.slice(start, start + pageSize);
  }, [filteredRules, page]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [totalPages, page]);

  function getTableDisplayName(tableId: string | null): string {
    const table = tableId ? tablesById[tableId] : null;
    if (!table) return '—';
    if (table.name_in_bank?.trim()) return table.name_in_bank;
    if (table.agreement_name) {
      const date = table.vigency_date
        ? ` (${new Date(table.vigency_date).toLocaleDateString('pt-BR')})`
        : '';
      return `${table.agreement_name}${date}`;
    }
    return `Tabela ${table.id.substring(0, 8)}`;
  }

  function removeRule(index: number) {
    setRules((prev) => prev.filter((_, i) => i !== index));
  }

  function updateRate(index: number, field: string, value: string) {
    setRules((prev) =>
      prev.map((rule, i) => {
        if (i !== index) return rule;
        return { ...rule, [field]: value } as PromoRule | UserRule;
      }),
    );
  }

  async function handleSave() {
    setSaving(true);
    try {
      const endpoint =
        ruleType === 'company'
          ? ENDPOINTS.COMMISSION_GROUP_BY_COMPANY_DETAIL(groupId)
          : ENDPOINTS.COMMISSION_GROUP_DETAIL(groupId);

      // Strip UI-only _rangeLabel field before saving
      const cleanRules = rules.map(({ _rangeLabel, ...r }: any) => r);

      const payload =
        ruleType === 'promotora'
          ? { promotora_rules: cleanRules }
          : { commission_rules: cleanRules };

      await api.patch(endpoint, payload);
      toast.success('Regras de comissão atualizadas!');
    } catch (err: any) {
      const data = err?.response?.data || err?.data;
      if (data?.errors && Array.isArray(data.errors)) {
        data.errors.forEach((e: string) => toast.error(e));
      } else if (data && typeof data === 'object') {
        const messages = Object.entries(data)
          .flatMap(([field, msgs]) =>
            Array.isArray(msgs) ? msgs.map((m: string) => `${field}: ${m}`) : [`${field}: ${msgs}`],
          );
        if (messages.length > 0) {
          messages.forEach((m) => toast.error(m));
        } else {
          toast.error('Erro ao salvar regras de comissão');
        }
      } else {
        toast.error('Erro ao salvar regras de comissão');
      }
    } finally {
      setSaving(false);
    }
  }

  const isPromoOrCompany = ruleType === 'promotora' || ruleType === 'company';

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin h-6 w-6 border-4 border-[var(--color-primary)] border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-sm text-gray-700">Regras de Comissão por Tabela</h3>
          {ruleType === 'promotora' && (
            <p className="text-xs text-gray-400 mt-0.5">
              Todas as tabelas são carregadas automaticamente. Exclua apenas as que não devem ter regra.
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <SearchSelect
            className="min-w-[10rem] w-auto"
            placeholder="Todos os bancos"
            allowEmpty
            value={bankFilter}
            options={bankOptions}
            onChange={(e) => {
              setBankFilter(e.target.value);
              setPage(1);
            }}
          />
          <Button size="sm" onClick={handleSave} loading={saving}>
            <Save size={14} />
            Salvar
          </Button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/50">
              <th className="px-4 py-2 text-left font-medium text-gray-600">Banco</th>
              <th className="px-4 py-2 text-left font-medium text-gray-600">Tabela</th>
              <th className="px-4 py-2 text-left font-medium text-gray-600">Faixa</th>
              {isPromoOrCompany ? (
                <>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Taxa (%)</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Valor Fixo (R$)</th>
                </>
              ) : (
                <>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Taxa Líder (%)</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Taxa Vendedor (%)</th>
                </>
              )}
              <th className="px-4 py-2 w-12"></th>
            </tr>
          </thead>
          <tbody>
            {pagedRules.length === 0 ? (
              <tr>
                <td colSpan={isPromoOrCompany ? 6 : 6} className="px-4 py-8 text-center text-gray-400">
                  Nenhuma tabela encontrada.
                </td>
              </tr>
            ) : (
              pagedRules.map((rule, idx) => {
                const globalIndex = (page - 1) * pageSize + idx;
                const bankName = rule.bank ? banksById[rule.bank]?.name || '—' : '—';
                return (
                  <tr key={globalIndex} className="border-b border-gray-50 hover:bg-gray-50/50">
                    <td className="px-4 py-2 text-gray-800 font-medium">{bankName}</td>
                    <td className="px-4 py-2 text-gray-700">{getTableDisplayName(rule.table)}</td>
                    <td className="px-4 py-2">
                      {rule._rangeLabel ? (
                        <span className="inline-block px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full font-medium whitespace-nowrap">
                          {rule._rangeLabel}
                        </span>
                      ) : (
                        <span className="text-gray-300 text-xs">—</span>
                      )}
                    </td>
                    {isPromoOrCompany ? (
                      <>
                        <td className="px-4 py-2">
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            max="100"
                            value={(rule as PromoRule).commission_rate}
                            onChange={(e) => updateRate(globalIndex, 'commission_rate', e.target.value)}
                            className="w-24 px-2 py-1.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
                          />
                        </td>
                        <td className="px-4 py-2">
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            placeholder="R$ 0,00"
                            value={(rule as PromoRule).fixed_value ?? ''}
                            onChange={(e) => updateRate(globalIndex, 'fixed_value', e.target.value)}
                            className="w-28 px-2 py-1.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
                          />
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="px-4 py-2">
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            max="100"
                            value={(rule as UserRule).leader_commission_rate}
                            onChange={(e) => updateRate(globalIndex, 'leader_commission_rate', e.target.value)}
                            className="w-24 px-2 py-1.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
                          />
                        </td>
                        <td className="px-4 py-2">
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            max="100"
                            value={(rule as UserRule).seller_commission_rate}
                            onChange={(e) => updateRate(globalIndex, 'seller_commission_rate', e.target.value)}
                            className="w-24 px-2 py-1.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
                          />
                        </td>
                      </>
                    )}
                    <td className="px-4 py-2">
                      <button
                        type="button"
                        onClick={() => removeRule(globalIndex)}
                        className="text-gray-400 hover:text-red-500 transition-colors"
                        title="Remover regra"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between gap-4">
        <p className="text-xs text-gray-500">
          Mostrando {filteredRules.length === 0 ? 0 : (page - 1) * pageSize + 1} a{' '}
          {Math.min(page * pageSize, filteredRules.length)} de {filteredRules.length} regras
        </p>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="p-1.5 rounded-lg hover:bg-gray-200 disabled:opacity-30 disabled:hover:bg-transparent"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="text-sm text-gray-700 px-2">
            {page} / {totalPages}
          </span>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="p-1.5 rounded-lg hover:bg-gray-200 disabled:opacity-30 disabled:hover:bg-transparent"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
