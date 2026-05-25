import { useState, useEffect } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Badge } from '../../ui/Badge';
import { CommissionRulesEditor } from './CommissionRulesEditor';
import { CompanySelector } from './CompanySelector';
import type { CommissionGroupByCompany } from '../../../../lib/api/types';
import toast from 'react-hot-toast';

interface CompanyGroupDetailProps {
  groupId: number;
}

export function CompanyGroupDetail({ groupId }: CompanyGroupDetailProps) {
  const [group, setGroup] = useState<CommissionGroupByCompany | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadGroup() {
    try {
      const data = await api.get<CommissionGroupByCompany>(
        ENDPOINTS.COMMISSION_GROUP_BY_COMPANY_DETAIL(groupId),
      );
      setGroup(data);
    } catch {
      toast.error('Erro ao carregar grupo');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadGroup();
  }, [groupId]);

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin h-8 w-8 border-4 border-[var(--color-primary)] border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!group) {
    return <p className="text-center text-gray-500 py-12">Grupo não encontrado.</p>;
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          {group.color && (
            <div
              className="w-4 h-4 rounded-full border border-gray-200"
              style={{ backgroundColor: group.color }}
            />
          )}
          <h1 className="text-2xl font-bold text-gray-900">{group.name}</h1>
          <Badge variant={group.is_active ? 'success' : 'secondary'}>
            {group.is_active ? 'Ativo' : 'Inativo'}
          </Badge>
        </div>
        {group.description && (
          <p className="text-sm text-gray-500">{group.description}</p>
        )}
      </div>

      {/* Companies */}
      <div className="mb-8">
        <CompanySelector
          groupId={groupId}
          initialCompanyIds={group.companies.map((c) => c.id)}
          onUpdate={loadGroup}
        />
      </div>

      {/* Commission Rules */}
      <CommissionRulesEditor
        groupId={groupId}
        ruleType="company"
        initialRules={group.commission_rules || []}
      />
    </div>
  );
}
