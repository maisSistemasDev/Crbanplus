import { useEffect, useMemo, useState } from 'react';
import { useStore } from '@nanostores/react';
import { Users } from 'lucide-react';
import { api } from '../../../../lib/api/client';
import { fetchAllPaginated } from '../../../../lib/api/pagination';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { formatPercent } from '../../../../lib/utils/format';
import { ROLE_LABELS, ROLE_COLORS, type Role } from '../../../../lib/utils/roles';
import { $currentUser } from '../../../../lib/stores/auth';
import type { Bank, CommissionGroup, Table, User } from '../../../../lib/api/types';
import { PageHeader } from '../../ui/PageHeader';
import { EmptyState } from '../../ui/EmptyState';
import { SectionSpinner } from '../../ui/Spinner';
import clsx from 'clsx';

interface ReadOnlyGroupViewProps {
  groupId: number;
}

export function ReadOnlyGroupView({ groupId }: ReadOnlyGroupViewProps) {
  const currentUser = useStore($currentUser);
  const [group, setGroup] = useState<CommissionGroup | null>(null);
  const [members, setMembers] = useState<User[]>([]);
  const [banks, setBanks] = useState<Bank[]>([]);
  const [tables, setTables] = useState<Table[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError('');
      try {
        const groupData = await api.get<CommissionGroup>(ENDPOINTS.COMMISSION_GROUP_DETAIL(groupId));
        if (cancelled) return;
        setGroup(groupData);

        const memberIds = [...groupData.sellers, ...groupData.leaders];
        const [usersList, banksList, tablesList] = await Promise.all([
          fetchAllPaginated<User>(ENDPOINTS.USERS),
          api.get<Bank[]>(ENDPOINTS.BANKS).catch(() => []),
          fetchAllPaginated<Table>(ENDPOINTS.TABLES).catch(() => []),
        ]);
        if (cancelled) return;
        setMembers(usersList.filter((u) => memberIds.includes(u.id)));
        setBanks(Array.isArray(banksList) ? banksList : []);
        setTables(tablesList);
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
  }, [groupId]);

  const bankNameById = useMemo(() => Object.fromEntries(banks.map((b) => [b.id, b.name])), [banks]);
  const tableNameById = useMemo(() => Object.fromEntries(tables.map((t) => [t.id, t.name_in_bank])), [tables]);

  const myRule = useMemo(() => {
    if (!group || !currentUser) return null;
    if (currentUser.role === 'lider') {
      return group.commission_rules.filter((r) => Number(r.leader_commission_rate) > 0);
    }
    return group.commission_rules;
  }, [group, currentUser]);

  if (loading) return <SectionSpinner />;
  if (error) return <div className="card text-sm text-red-600">{error}</div>;
  if (!group) return null;

  return (
    <div>
      <PageHeader
        title={group.name}
        subtitle={group.company_name ? `${group.company_name} · Equipe (somente leitura)` : 'Equipe (somente leitura)'}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="section-title mb-3">Membros da equipe</h2>
          {members.length === 0 ? (
            <EmptyState icon={Users} title="Nenhum membro cadastrado" />
          ) : (
            <ul className="divide-y divide-gray-100">
              {members.map((member) => (
                <li key={member.id} className="flex items-center justify-between gap-3 py-2.5">
                  <div>
                    <p className="text-sm font-medium text-[var(--color-text)]">
                      {member.first_name} {member.last_name}
                    </p>
                    <p className="text-xs text-[var(--color-text-muted)]">{member.cpf}</p>
                  </div>
                  <span
                    className={clsx(
                      'rounded-full px-2 py-0.5 text-[10px] font-medium',
                      ROLE_COLORS[member.role as Role],
                    )}
                  >
                    {ROLE_LABELS[member.role as Role] ?? member.role}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card">
          <h2 className="section-title mb-3">Regras de comissão</h2>
          {!myRule || myRule.length === 0 ? (
            <p className="text-sm text-[var(--color-text-muted)]">Nenhuma regra de comissão configurada.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--color-border)] text-left text-xs uppercase text-[var(--color-text-muted)]">
                    <th className="py-2 pr-3">Banco</th>
                    <th className="py-2 pr-3">Tabela</th>
                    <th className="py-2 pr-3">Líder</th>
                    <th className="py-2 pr-3">Vendedor</th>
                  </tr>
                </thead>
                <tbody>
                  {myRule.map((rule, idx) => (
                    <tr key={rule.id ?? idx} className="border-b border-gray-100">
                      <td className="py-2 pr-3">{rule.bank ? bankNameById[rule.bank] ?? '—' : '—'}</td>
                      <td className="py-2 pr-3">{rule.table ? tableNameById[rule.table] ?? '—' : '—'}</td>
                      <td className="py-2 pr-3">{formatPercent(rule.leader_commission_rate)}</td>
                      <td className="py-2 pr-3">{formatPercent(rule.seller_commission_rate)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
