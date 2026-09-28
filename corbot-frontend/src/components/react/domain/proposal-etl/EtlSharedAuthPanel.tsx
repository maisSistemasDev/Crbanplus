import { useMemo } from 'react';
import type { EtlMetaAuthType } from '../../../../lib/api/types/etl';
import { Input } from '../../ui/Input';
import { SearchSelect } from '../../ui/SearchSelect';

interface EtlSharedAuthPanelProps {
  enabled: boolean;
  authType: string;
  authConfig: Record<string, string>;
  authTypes: EtlMetaAuthType[];
  onEnabledChange: (enabled: boolean) => void;
  onAuthTypeChange: (authType: string, defaults: Record<string, string>) => void;
  onAuthConfigChange: (config: Record<string, string>) => void;
}

function authDefaultsForType(authTypeId: string, authTypes: EtlMetaAuthType[]): Record<string, string> {
  const authType = authTypes.find((a) => a.id === authTypeId);
  if (!authType) return {};
  return Object.fromEntries(
    authType.fields.filter((f) => f.default).map((f) => [f.name, f.default as string]),
  );
}

export function EtlSharedAuthPanel({
  enabled,
  authType,
  authConfig,
  authTypes,
  onEnabledChange,
  onAuthTypeChange,
  onAuthConfigChange,
}: EtlSharedAuthPanelProps) {
  const selectedType = authTypes.find((a) => a.id === (authType || 'none'));
  const authTypeOptions = useMemo(
    () => authTypes.map((a) => ({ value: a.id, label: a.label })),
    [authTypes],
  );

  return (
    <div className="space-y-2 border-t border-gray-100 pt-3">
      <p className="text-xs font-medium text-gray-700">Autenticação compartilhada</p>
      <p className="text-[10px] text-gray-500 leading-snug">
        Salve credenciais uma vez. A cada execução, o token é obtido uma única vez e reutilizado em todos os nós HTTP.
      </p>
      <label className="flex items-center gap-2 text-xs text-gray-700 rounded-lg border border-gray-200 bg-white px-3 py-2">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onEnabledChange(e.target.checked)}
        />
        Usar auth compartilhada no fluxo
      </label>

      {enabled && (
        <>
          <label className="block text-xs font-medium text-gray-600">Tipo</label>
          <SearchSelect
            value={authType || 'none'}
            options={authTypeOptions}
            onChange={(e) => onAuthTypeChange(e.target.value, authDefaultsForType(e.target.value, authTypes))}
          />
          {selectedType?.fields.map((field) => (
            <Input
              key={field.name}
              label={field.label}
              type={field.type === 'password' ? 'password' : 'text'}
              value={authConfig[field.name] ?? ''}
              placeholder={field.default ? String(field.default) : undefined}
              onChange={(e) =>
                onAuthConfigChange({ ...authConfig, [field.name]: e.target.value })
              }
            />
          ))}
        </>
      )}
    </div>
  );
}
