import { useState, useEffect, useMemo } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import type { Company } from '../../../../lib/api/types';
import { Button } from '../../ui/Button';
import { SearchSelect } from '../../ui/SearchSelect';

type GroupType = 'promotora' | 'corban';

interface Props {
  onSubmit: (values: Record<string, any>) => Promise<void>;
  loading: boolean;
  onCancel: () => void;
  /** Força o tipo do grupo (esconde o seletor). */
  forcedType?: GroupType;
}

export function CommissionGroupForm({ onSubmit, loading, onCancel, forcedType }: Props) {
  const [groupType, setGroupType] = useState<GroupType>(forcedType || 'promotora');
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loadingCompanies, setLoadingCompanies] = useState(false);
  const companyOptions = useMemo(
    () => companies.map((c) => ({ value: String(c.id), label: c.name })),
    [companies],
  );
  const [form, setForm] = useState({
    name: '',
    description: '',
    company: '',
    color: '#3b82f6',
    is_active: true,
  });

  useEffect(() => {
    if (forcedType) setGroupType(forcedType);
  }, [forcedType]);

  useEffect(() => {
    if (groupType === 'corban' && companies.length === 0) {
      setLoadingCompanies(true);
      api
        .get<Company[] | { results: Company[] }>(`${ENDPOINTS.COMPANIES}?page_size=500`)
        .then((res) => {
          const list = Array.isArray(res) ? res : (res as any).results ?? [];
          setCompanies(list);
        })
        .finally(() => setLoadingCompanies(false));
    }
  }, [groupType, companies.length]);

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) {
    const { name, type } = e.target;
    const value =
      type === 'checkbox' ? (e.target as HTMLInputElement).checked : e.target.value;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload: Record<string, any> = {
      name: form.name,
      description: form.description || '',
      color: form.color,
      is_active: form.is_active,
    };
    if (groupType === 'corban') {
      payload.company = form.company;
    }
    await onSubmit(payload);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Tipo de grupo */}
      {!forcedType && (
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Tipo de grupo
        </label>
        <div className="flex gap-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="group_type"
              value="promotora"
              checked={groupType === 'promotora'}
              onChange={() => {
                setGroupType('promotora');
                setForm((prev) => ({ ...prev, company: '' }));
              }}
              className="accent-[var(--color-primary)]"
            />
            <span className="text-sm text-gray-700">Grupo da Promotora</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="group_type"
              value="corban"
              checked={groupType === 'corban'}
              onChange={() => setGroupType('corban')}
              className="accent-[var(--color-primary)]"
            />
            <span className="text-sm text-gray-700">Grupo para o Corban</span>
          </label>
        </div>
        {groupType === 'promotora' && (
          <p className="mt-1 text-xs text-gray-500">
            Sem empresa vinculada — usado para regras/tetos da promotora com vínculos de Corban.
          </p>
        )}
        {groupType === 'corban' && (
          <p className="mt-1 text-xs text-gray-500">
            Vinculado a 1 Corban — só aceita usuários da hierarquia dessa empresa.
          </p>
        )}
      </div>
      )}
      {forcedType === 'corban' && (
        <p className="text-xs text-gray-500">
          Este grupo fica vinculado a 1 Corban e só aceita usuários da hierarquia dessa empresa.
        </p>
      )}
      {forcedType === 'promotora' && (
        <p className="text-xs text-gray-500">
          Grupo da promotora, sem Corban vinculado no cadastro.
        </p>
      )}

      {/* Empresa (somente para corban) */}
      {groupType === 'corban' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Empresa do Corban <span className="text-red-500">*</span>
          </label>
          <SearchSelect
            name="company"
            value={form.company}
            onChange={handleChange}
            required
            disabled={loadingCompanies}
            placeholder={loadingCompanies ? 'Carregando...' : 'Selecione a empresa'}
            options={companyOptions}
          />
        </div>
      )}

      {/* Nome */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Nome <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          name="name"
          value={form.name}
          onChange={handleChange}
          required
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
        />
      </div>

      {/* Descrição */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Descrição</label>
        <textarea
          name="description"
          value={form.description}
          onChange={handleChange}
          rows={3}
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
        />
      </div>

      {/* Cor */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Cor</label>
        <input
          type="color"
          name="color"
          value={form.color}
          onChange={handleChange}
          className="h-9 w-16 border border-gray-200 rounded-lg p-1 cursor-pointer"
        />
      </div>

      {/* Ativo */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="is_active_cg"
          name="is_active"
          checked={form.is_active}
          onChange={handleChange}
          className="rounded border-gray-300"
        />
        <label htmlFor="is_active_cg" className="text-sm text-gray-700">
          Ativo
        </label>
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" loading={loading}>
          Criar Grupo
        </Button>
      </div>
    </form>
  );
}
