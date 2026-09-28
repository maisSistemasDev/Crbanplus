import { useState, useEffect } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Input } from '../../ui/Input';
import { Select } from '../../ui/Select';
import { SearchSelect } from '../../ui/SearchSelect';
import { Button } from '../../ui/Button';
import { Plus, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

const RANGE_KIND_OPTIONS = [
  { value: 'rate', label: 'Taxa (%)' },
  { value: 'fixed', label: 'Valor (R$)' },
];

interface CommissionRange {
  id?: string;
  min_value: string;
  max_value: string;
  kind: 'rate' | 'fixed';
  amount: string;
}

interface TableFormValues {
  bank: string;
  agreement: string;
  name_in_bank: string;
  code_in_bank: string;
  vigency_date: string;
  is_active: boolean;
  commission_ranges: CommissionRange[];
}

interface SelectOption {
  value: string;
  label: string;
}

interface TableRangesFormProps {
  item: Record<string, unknown> | null;
  onSubmit: (values: Record<string, any>) => Promise<void>;
  onClose: () => void;
  saving: boolean;
}

function emptyRange(): CommissionRange {
  return { min_value: '0', max_value: '0', kind: 'rate', amount: '' };
}

function rangeFromApi(r: Record<string, unknown>): CommissionRange {
  const hasFixed = r.fixed_value !== null && r.fixed_value !== undefined && r.fixed_value !== '';
  return {
    id: r.id != null ? String(r.id) : undefined,
    min_value: String(r.min_value ?? '0'),
    max_value: String(r.max_value ?? '0'),
    kind: hasFixed ? 'fixed' : 'rate',
    amount: hasFixed ? String(r.fixed_value) : String(r.commission_rate ?? ''),
  };
}

export function TableRangesForm({ item, onSubmit, onClose, saving }: TableRangesFormProps) {
  const [banks, setBanks] = useState<SelectOption[]>([]);
  const [agreements, setAgreements] = useState<SelectOption[]>([]);

  const [values, setValues] = useState<TableFormValues>({
    bank: '',
    agreement: '',
    name_in_bank: '',
    code_in_bank: '',
    vigency_date: '',
    is_active: true,
    commission_ranges: [emptyRange()],
  });

  // Populate from existing item when editing
  useEffect(() => {
    if (item) {
      const ranges: CommissionRange[] = Array.isArray(item.commission_ranges)
        ? (item.commission_ranges as Record<string, unknown>[]).map(rangeFromApi)
        : [emptyRange()];

      setValues({
        bank: String(item.bank ?? ''),
        agreement: String(item.agreement ?? ''),
        name_in_bank: String(item.name_in_bank ?? ''),
        code_in_bank: String(item.code_in_bank ?? ''),
        vigency_date: String(item.vigency_date ?? ''),
        is_active: item.is_active !== false,
        commission_ranges: ranges.length > 0 ? ranges : [emptyRange()],
      });
    }
  }, [item]);

  // Load bank/agreement options from form_fields endpoint
  useEffect(() => {
    api.get<any[]>(ENDPOINTS.FORM_FIELDS_TABLES).then((fields) => {
      const bankField = fields.find((f) => f.name === 'bank');
      const agreementField = fields.find((f) => f.name === 'agreement');
      if (bankField?.options) setBanks(bankField.options);
      if (agreementField?.options) setAgreements(agreementField.options);
    }).catch(() => {
      toast.error('Erro ao carregar opções de banco/convênio');
    });
  }, []);

  function setField<K extends keyof TableFormValues>(key: K, val: TableFormValues[K]) {
    setValues((prev) => ({ ...prev, [key]: val }));
  }

  function setRange(index: number, key: keyof CommissionRange, val: string) {
    setValues((prev) => {
      const ranges = [...prev.commission_ranges];
      ranges[index] = { ...ranges[index], [key]: val };
      return { ...prev, commission_ranges: ranges };
    });
  }

  function addRange() {
    setValues((prev) => ({
      ...prev,
      commission_ranges: [...prev.commission_ranges, emptyRange()],
    }));
  }

  function removeRange(index: number) {
    setValues((prev) => ({
      ...prev,
      commission_ranges: prev.commission_ranges.filter((_, i) => i !== index),
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!values.bank) { toast.error('Selecione um banco'); return; }
    if (!values.agreement) { toast.error('Selecione um convênio'); return; }
    if (!values.vigency_date) { toast.error('Informe a data de vigência'); return; }
    if (values.commission_ranges.length === 0) { toast.error('Adicione pelo menos uma faixa de comissionamento'); return; }

    for (let i = 0; i < values.commission_ranges.length; i++) {
      const r = values.commission_ranges[i];
      if (r.min_value === '' || r.max_value === '' || !r.amount) {
        toast.error(`Faixa ${i + 1}: preencha mínimo, máximo e ${r.kind === 'fixed' ? 'valor fixo' : 'taxa'}`);
        return;
      }
    }

    const payload = {
      bank: values.bank,
      agreement: values.agreement,
      name_in_bank: values.name_in_bank,
      code_in_bank: values.code_in_bank || null,
      vigency_date: values.vigency_date,
      is_active: values.is_active,
      commission_ranges: values.commission_ranges.map((r) => ({
        min_value: parseFloat(r.min_value),
        max_value: parseFloat(r.max_value),
        commission_rate: r.kind === 'rate' ? parseFloat(r.amount) : 0,
        fixed_value: r.kind === 'fixed' ? parseFloat(r.amount) : null,
      })),
    };

    await onSubmit(payload);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {/* Campos principais */}
      <div className="grid grid-cols-2 gap-4">
        <Select
          label="Banco"
          required
          options={banks}
          value={values.bank}
          onChange={(e) => setField('bank', e.target.value)}
        />
        <Select
          label="Convênio"
          required
          options={agreements}
          value={values.agreement}
          onChange={(e) => setField('agreement', e.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Nome no Banco"
          type="text"
          value={values.name_in_bank}
          onChange={(e) => setField('name_in_bank', e.target.value)}
        />
        <Input
          label="Codigo da Tabela"
          type="text"
          value={values.code_in_bank}
          onChange={(e) => setField('code_in_bank', e.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Vigência (início)"
          type="date"
          required
          value={values.vigency_date}
          onChange={(e) => setField('vigency_date', e.target.value)}
        />
      </div>
      <p className="text-xs text-gray-500 -mt-2">
        Data em que a tabela passa a valer. Não é data de término — vigência em 2025 continua válida em 2026.
      </p>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="is_active"
          checked={values.is_active}
          onChange={(e) => setField('is_active', e.target.checked)}
          className="h-4 w-4 rounded border-gray-300 text-[var(--color-primary)]"
        />
        <label htmlFor="is_active" className="text-sm text-gray-700">Ativo</label>
      </div>

      {/* Faixas de comissionamento */}
      <div className="border-t border-gray-200 pt-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-900">Faixas de Comissionamento</h3>
          <Button type="button" variant="secondary" size="sm" onClick={addRange}>
            <Plus size={14} />
            Adicionar Faixa
          </Button>
        </div>

        <div className="flex flex-col gap-3">
          <p className="text-xs text-gray-500">
            Use 0 e 0 em mínimo e máximo para valer em qualquer valor de proposta. Escolha taxa percentual ou valor fixo em reais.
          </p>

          {/* Header */}
          <div className="grid grid-cols-[1fr_1fr_8.5rem_1fr_2rem] gap-2 text-xs font-medium text-gray-500 px-1">
            <span>Valor Mínimo (R$)</span>
            <span>Valor Máximo (R$)</span>
            <span>Tipo</span>
            <span>Comissão</span>
            <span />
          </div>

          {values.commission_ranges.map((range, i) => (
            <div key={i} className="grid grid-cols-[1fr_1fr_8.5rem_1fr_2rem] gap-2 items-center">
              <Input
                type="number"
                placeholder="0"
                step="0.01"
                min="0"
                required
                value={range.min_value}
                onChange={(e) => setRange(i, 'min_value', e.target.value)}
              />
              <Input
                type="number"
                placeholder="0"
                step="0.01"
                min="0"
                required
                value={range.max_value}
                onChange={(e) => setRange(i, 'max_value', e.target.value)}
              />
              <SearchSelect
                value={range.kind}
                options={RANGE_KIND_OPTIONS}
                onChange={(e) => setRange(i, 'kind', e.target.value as CommissionRange['kind'])}
              />
              <Input
                type="number"
                placeholder={range.kind === 'fixed' ? 'Ex: 960' : 'Ex: 25'}
                step="0.01"
                min="0"
                max={range.kind === 'rate' ? '100' : undefined}
                required
                value={range.amount}
                onChange={(e) => setRange(i, 'amount', e.target.value)}
              />
              <button
                type="button"
                onClick={() => removeRange(i)}
                disabled={values.commission_ranges.length === 1}
                className="flex items-center justify-center w-8 h-8 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title="Remover faixa"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Ações */}
      <div className="flex justify-end gap-2 pt-2 border-t border-gray-200">
        <Button type="button" variant="secondary" onClick={onClose} disabled={saving}>
          Cancelar
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? 'Salvando...' : item ? 'Atualizar' : 'Criar'}
        </Button>
      </div>
    </form>
  );
}
