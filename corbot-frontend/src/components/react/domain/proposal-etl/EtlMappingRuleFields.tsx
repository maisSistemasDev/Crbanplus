import { useMemo } from 'react';
import type { EtlFieldMapping, EtlMappingWhen } from '../../../../lib/api/types/etl';
import { Input } from '../../ui/Input';
import { SearchSelect } from '../../ui/SearchSelect';

interface MetaOption {
  id: string;
  label: string;
}

interface EtlMappingRuleFieldsProps {
  mapping: EtlFieldMapping;
  fieldTransforms: MetaOption[];
  conditionOperators: MetaOption[];
  onChange: (patch: Partial<EtlFieldMapping>) => void;
}

export function EtlMappingRuleFields({
  mapping,
  fieldTransforms,
  conditionOperators,
  onChange,
}: EtlMappingRuleFieldsProps) {
  const hasWhen = mapping.when != null;
  const transformOptions = useMemo(
    () => fieldTransforms.map((t) => ({ value: t.id, label: t.label })),
    [fieldTransforms],
  );
  const operatorOptions = useMemo(
    () => conditionOperators.map((op) => ({ value: op.id, label: op.label })),
    [conditionOperators],
  );

  return (
    <div className="space-y-2 border-t border-gray-100 pt-2 mt-1">
      <label className="block text-xs font-medium text-gray-600">Transformação</label>
      <SearchSelect
        value={mapping.transform || ''}
        options={transformOptions}
        onChange={(e) => onChange({ transform: e.target.value || undefined })}
      />

      <Input
        label="Fallback se vazio (outro path JSON)"
        value={mapping.fallback_source_path || ''}
        onChange={(e) => onChange({ fallback_source_path: e.target.value || undefined })}
        placeholder="ex: customer.document"
      />

      <label className="flex items-center gap-2 text-xs text-gray-700">
        <input
          type="checkbox"
          checked={hasWhen}
          onChange={(e) => {
            if (e.target.checked) {
              onChange({ when: mapping.when || { path: '', op: 'eq', value: '' } });
            } else {
              onChange({ when: undefined, else_source_path: undefined, skip_if_unmatched: undefined });
            }
          }}
        />
        Usar condição
      </label>

      {hasWhen && (
        <div className="space-y-2 rounded-lg bg-gray-50 p-2">
          <Input
            label="Campo da condição (JSON path)"
            value={mapping.when?.path || ''}
            onChange={(e) =>
              onChange({
                when: { ...(mapping.when || { op: 'eq' }), path: e.target.value },
              })
            }
            placeholder="ex: status ou loan.type"
          />
          <label className="block text-xs font-medium text-gray-600">Operador</label>
          <SearchSelect
            value={mapping.when?.op || 'eq'}
            options={operatorOptions}
            onChange={(e) =>
              onChange({
                when: {
                  ...(mapping.when || { path: '' }),
                  op: e.target.value as EtlMappingWhen['op'],
                },
              })
            }
          />
          {!['empty', 'not_empty'].includes(mapping.when?.op || '') && (
            <Input
              label="Valor esperado"
              value={mapping.when?.value || ''}
              onChange={(e) =>
                onChange({
                  when: { ...(mapping.when || { path: '', op: 'eq' }), value: e.target.value },
                })
              }
            />
          )}
          <Input
            label="Senão, usar path alternativo"
            value={mapping.else_source_path || ''}
            onChange={(e) => onChange({ else_source_path: e.target.value || undefined })}
            placeholder="ex: partner.cpf"
          />
          <label className="flex items-center gap-2 text-xs text-gray-700">
            <input
              type="checkbox"
              checked={Boolean(mapping.skip_if_unmatched)}
              onChange={(e) => onChange({ skip_if_unmatched: e.target.checked })}
            />
            Omitir campo se a condição não for atendida
          </label>
          <p className="text-[10px] text-gray-500 leading-snug">
            Ex.: se <code className="bg-white px-1 rounded">status</code> igual a{' '}
            <code className="bg-white px-1 rounded">APPROVED</code>, usa o path principal;
            senão usa o alternativo ou omite o campo.
          </p>
        </div>
      )}
    </div>
  );
}
