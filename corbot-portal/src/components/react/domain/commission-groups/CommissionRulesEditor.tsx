import { useState, useEffect, useMemo } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Button } from '../../ui/Button';
import { SearchSelect } from '../../ui/SearchSelect';
import { Plus, Trash2, Save } from 'lucide-react';
import toast from 'react-hot-toast';

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
  agreement_name?: string;
  bank_name?: string;
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
  initialRules: (PromoRule | UserRule)[];
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

export function CommissionRulesEditor({ groupId, ruleType, initialRules }: CommissionRulesEditorProps) {
  const [rules, setRules] = useState<(PromoRule | UserRule)[]>(initialRules);
  const [banks, setBanks] = useState<Bank[]>([]);
  const [tables, setTables] = useState<TableOption[]>([]);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  const bankOptions = useMemo(() => banks.map((b) => ({ value: b.id, label: b.name })), [banks]);

  useEffect(() => {
    async function load() {
      try {
        const banksData = await api.get<Bank[]>(ENDPOINTS.BANKS);
        setBanks(Array.isArray(banksData) ? banksData : (banksData as any).results || []);
      } catch {
        toast.error('Erro ao carregar bancos');
      }
      try {
        const tablesData = await api.get<TableOption[]>(ENDPOINTS.TABLES);
        setTables(Array.isArray(tablesData) ? tablesData : (tablesData as any).results || []);
      } catch {
        toast.error('Erro ao carregar tabelas');
      }
      setLoading(false);
    }
    load();
  }, []);

  // Quando as tabelas chegam, enriquece as regras já salvas no banco com
  // o `_rangeLabel` (campo só de UI). Sem isso a coluna "Faixa" fica "—"
  // porque o backend só retorna o id da CommissionRange, não os valores
  // min/max formatados.
  useEffect(() => {
    if (loading || tables.length === 0) return;
    setRules((prev) => {
      let mutated = false;
      const next = prev.map((rule) => {
        if (!rule.table || !rule.commission_range) return rule;
        if ((rule as any)._rangeLabel) return rule;
        const table = tables.find((t) => t.id === rule.table);
        const range = table?.commission_ranges.find(
          (r) => r.id === rule.commission_range,
        );
        if (!range) return rule;
        mutated = true;
        return {
          ...rule,
          _rangeLabel: rangeLabel(range),
        };
      });
      return mutated ? next : prev;
    });
  }, [loading, tables]);

  // Initialize rules with all tables if initialRules is empty
  useEffect(() => {
    if (!loading && tables.length > 0 && (!initialRules || initialRules.length === 0)) {
      const initialRulesFromTables: (PromoRule | UserRule)[] = [];
      for (const table of tables) {
        // Separar ranges válidos (min e max não zero) dos placeholders (min=0 e max=0)
        const allRanges = table.commission_ranges ?? [];
        const ranges = allRanges.filter((r) => !isPlaceholderRange(r));
        if (ranges.length > 0) {
          // One rule per range
          for (const range of ranges) {
            const rawRate = parseFloat(range.commission_rate);
            const rate = isFinite(rawRate) ? Math.max(0, rawRate) : 0;
            if (ruleType === 'promotora' || ruleType === 'company') {
              const rawFixed = parseFloat(String(range.fixed_value ?? ''));
              initialRulesFromTables.push({
                bank: table.bank,
                table: table.id,
                commission_range: range.id,
                commission_rate: rate.toString(),
                fixed_value: isFinite(rawFixed) ? String(range.fixed_value) : null,
                _rangeLabel: rangeLabel(range),
              } as PromoRule);
            } else {
              initialRulesFromTables.push({
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
          // Sem ranges válidos: regra por tabela. Taxa vem do campo commission_rate da tabela
          // ou, se null, da taxa do range zero (se existir) como fallback.
          const zeroRangeRate = allRanges.length > 0 ? parseFloat(allRanges[0].commission_rate) : NaN;
          const tableRate = parseFloat(table.commission_rate ?? 'NaN');
          const rawRate = isFinite(tableRate) ? tableRate : isFinite(zeroRangeRate) ? zeroRangeRate : 0;
          const rate = Math.max(0, rawRate);
          if (ruleType === 'promotora' || ruleType === 'company') {
            initialRulesFromTables.push({
              bank: table.bank,
              table: table.id,
              commission_range: null,
              commission_rate: rate.toString(),
            } as PromoRule);
          } else {
            initialRulesFromTables.push({
              bank: table.bank,
              table: table.id,
              commission_range: null,
              leader_commission_rate: rate.toString(),
              seller_commission_rate: rate.toString(),
            } as UserRule);
          }
        }
      }
      setRules(initialRulesFromTables);
    }
  }, [loading, tables, initialRules, ruleType]);

  function getTablesForBank(bankId: string | null) {
    if (!bankId) return [];
    return tables.filter((t) => t.bank === bankId);
  }

  function getTableById(tableId: string | null) {
    if (!tableId) return null;
    return tables.find((t) => t.id === tableId) ?? null;
  }

  function getTableDisplayName(table: TableOption): string {
    if (table.name_in_bank?.trim()) return table.name_in_bank;
    if (table.agreement_name) {
      const date = table.vigency_date
        ? ` (${new Date(table.vigency_date).toLocaleDateString('pt-BR')})`
        : '';
      return `${table.agreement_name}${date}`;
    }
    return `Tabela ${table.id.substring(0, 8)}`;
  }

  /** When a table is selected, expand the rule group into one row per range
   *  (or keep as single row if the table has no ranges). */
  function handleTableChange(index: number, tableId: string) {
    const table = getTableById(tableId);
    const bankId = rules[index].bank;

    if (!table) {
      updateRule(index, 'table', tableId);
      return;
    }

    const ranges = table.commission_ranges ?? [];

    if (ranges.length <= 1) {
      // Single-range or no-range table: just update the row
      const rangeId = ranges.length === 1 ? ranges[0].id : null;
      setRules((prev) =>
        prev.map((r, i) =>
          i === index
            ? ruleType === 'promotora' || ruleType === 'company'
              ? ({ ...r, table: tableId, commission_range: rangeId, _rangeLabel: ranges[0] ? rangeLabel(ranges[0]) : undefined } as PromoRule)
              : ({ ...r, table: tableId, commission_range: rangeId, _rangeLabel: ranges[0] ? rangeLabel(ranges[0]) : undefined } as UserRule)
            : r,
        ),
      );
      return;
    }

    // Multi-range table: replace the current row with one row per range
    const newRows = ranges.map((cr) =>
      ruleType === 'promotora' || ruleType === 'company'
        ? ({
            bank: bankId,
            table: tableId,
            commission_range: cr.id,
            commission_rate: '0',
            _rangeLabel: rangeLabel(cr),
          } as PromoRule)
        : ({
            bank: bankId,
            table: tableId,
            commission_range: cr.id,
            leader_commission_rate: '0',
            seller_commission_rate: '0',
            _rangeLabel: rangeLabel(cr),
          } as UserRule),
    );

    setRules((prev) => [
      ...prev.slice(0, index),
      ...newRows,
      ...prev.slice(index + 1),
    ]);
  }

  function addRule() {
    if (ruleType === 'promotora' || ruleType === 'company') {
      setRules((prev) => [...prev, { bank: null, table: null, commission_range: null, commission_rate: '0' } as PromoRule]);
    } else {
      setRules((prev) => [
        ...prev,
        { bank: null, table: null, commission_range: null, leader_commission_rate: '0', seller_commission_rate: '0' } as UserRule,
      ]);
    }
  }

  function removeRule(index: number) {
    setRules((prev) => prev.filter((_, i) => i !== index));
  }

  function updateRule(index: number, field: string, value: string) {
    setRules((prev) =>
      prev.map((rule, i) => {
        if (i !== index) return rule;
        const updated = { ...rule, [field]: value };
        if (field === 'bank') {
          (updated as any).table = null;
          (updated as any).commission_range = null;
          (updated as any)._rangeLabel = undefined;
        }
        return updated;
      }),
    );
  }

  async function handleSave() {
    for (const rule of rules) {
      if (!rule.bank || !rule.table) {
        toast.error('Selecione banco e tabela para todas as regras');
        return;
      }
    }

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
        // Field-level errors like {"commission_rate": ["msg"]}
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
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-sm text-gray-700">Regras de Comissão por Tabela</h3>
          {ruleType === 'promotora' && (
            <p className="text-xs text-gray-400 mt-0.5">
              Taxa única paga pela promotora à empresa do corban. Tabelas com múltiplas faixas geram uma linha por faixa automaticamente.
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={addRule}>
            <Plus size={14} />
            Adicionar Regra
          </Button>
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
                <th className="px-4 py-2 text-left font-medium text-gray-600">Taxa (%)</th>
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
            {rules.length === 0 ? (
              <tr>
                <td colSpan={isPromoOrCompany ? 5 : 6} className="px-4 py-8 text-center text-gray-400">
                  Nenhuma regra definida. Clique em "Adicionar Regra" para começar.
                </td>
              </tr>
            ) : (
              rules.map((rule, index) => {
                const availableTables = getTablesForBank(rule.bank);

                return (
                  <tr key={index} className="border-b border-gray-50 hover:bg-gray-50/50">
                    {/* Banco */}
                    <td className="px-4 py-2">
                      <SearchSelect
                        placeholder="Selecione..."
                        allowEmpty
                        value={rule.bank || ''}
                        options={bankOptions}
                        onChange={(value) => updateRule(index, 'bank', value)}
                      />
                    </td>

                    {/* Tabela */}
                    <td className="px-4 py-2">
                      <SearchSelect
                        placeholder="Selecione..."
                        allowEmpty
                        value={rule.table || ''}
                        options={availableTables.map((t) => ({ value: t.id, label: getTableDisplayName(t) }))}
                        onChange={(value) => handleTableChange(index, value)}
                        disabled={!rule.bank}
                      />
                    </td>

                    {/* Faixa */}
                    <td className="px-4 py-2">
                      {(rule as any)._rangeLabel ? (
                        <span className="inline-block px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full font-medium whitespace-nowrap">
                          {(rule as any)._rangeLabel}
                        </span>
                      ) : (
                        <span className="text-gray-300 text-xs">—</span>
                      )}
                    </td>

                    {/* Taxas */}
                    {isPromoOrCompany ? (
                      <td className="px-4 py-2">
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          max="100"
                          value={(rule as PromoRule).commission_rate}
                          onChange={(e) => updateRule(index, 'commission_rate', e.target.value)}
                          className="w-24 px-2 py-1.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
                        />
                      </td>
                    ) : (
                      <>
                        <td className="px-4 py-2">
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            max="100"
                            value={(rule as UserRule).leader_commission_rate}
                            onChange={(e) => updateRule(index, 'leader_commission_rate', e.target.value)}
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
                            onChange={(e) => updateRule(index, 'seller_commission_rate', e.target.value)}
                            className="w-24 px-2 py-1.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
                          />
                        </td>
                      </>
                    )}

                    <td className="px-2 py-2">
                      <button
                        onClick={() => removeRule(index)}
                        className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
