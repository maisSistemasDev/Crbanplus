import { useState, useEffect, useMemo, useRef } from 'react';
import { api } from '../../../../lib/api/client';
import { fetchAllPaginated } from '../../../../lib/api/pagination';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { Button } from '../../ui/Button';
import { PageHeader } from '../../ui/PageHeader';
import { ROLE_LABELS, ROLE_COLORS } from '../../../../lib/utils/roles';
import type { Role } from '../../../../lib/utils/roles';
import type { User, CommissionGroup } from '../../../../lib/api/types';
import clsx from 'clsx';
import { Search, ChevronRight, ChevronLeft, Check } from 'lucide-react';
import toast from 'react-hot-toast';
import { CommissionRulesEditor } from './CommissionRulesEditor';
import { RegistrationLinksPanel } from './RegistrationLinksPanel';

interface TeamBuilderProps {
  groupId: number;
}

export function TeamBuilder({ groupId }: TeamBuilderProps) {
  const [group, setGroup] = useState<CommissionGroup | null>(null);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [teamMemberIds, setTeamMemberIds] = useState<number[]>([]);
  const [selectedAvailable, setSelectedAvailable] = useState<Set<number>>(new Set());
  const [selectedTeam, setSelectedTeam] = useState<Set<number>>(new Set());
  const [searchAvailable, setSearchAvailable] = useState('');
  const [searchTeam, setSearchTeam] = useState('');
  const [loading, setLoading] = useState(true);
  const [usersLoading, setUsersLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // 1) Carrega o grupo primeiro para liberar a tela (regras, links, cabeçalho)
  useEffect(() => {
    let cancelled = false;

    async function loadGroup() {
      setLoading(true);
      setUsersLoading(true);
      setAllUsers([]);
      setSelectedAvailable(new Set());
      setSelectedTeam(new Set());
      try {
        const groupData = await api.get<CommissionGroup>(
          ENDPOINTS.COMMISSION_GROUP_DETAIL(groupId),
        );
        if (cancelled) return;
        setGroup(groupData);
        setTeamMemberIds([...groupData.sellers, ...groupData.leaders]);
      } catch (error) {
        if (!cancelled) toast.error(extractErrorMessage(error));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadGroup();
    return () => {
      cancelled = true;
    };
  }, [groupId]);

  // 2) Usuários em paralelo depois — filtra por empresa/role para reduzir volume
  useEffect(() => {
    if (!group || group.id !== groupId) return;
    let cancelled = false;
    const companyId = group.company;
    const isPromotora = companyId === null;

    async function loadUsers() {
      setUsersLoading(true);
      try {
        const params: Record<string, string> = {};
        if (!isPromotora && companyId) {
          params.company = String(companyId);
        } else {
          // Grupo da promotora: só empresa_admin (vínculos por Corban)
          params.role = 'empresa_admin';
        }

        const usersList = await fetchAllPaginated<User>(ENDPOINTS.USERS, params);
        if (cancelled) return;
        setAllUsers(usersList);
      } catch (error) {
        if (!cancelled) toast.error(extractErrorMessage(error));
      } finally {
        if (!cancelled) setUsersLoading(false);
      }
    }

    loadUsers();
    return () => {
      cancelled = true;
    };
  }, [groupId, group?.id, group?.company]);

  // Filter by group type before splitting available/team
  const eligibleUsers = useMemo(() => {
    if (!group) return allUsers;
    if (group.company === null) {
      // Grupo da promotora: vínculos via empresa_admin
      return allUsers.filter((u) => u.role === 'empresa_admin');
    }

    // Grupo por Corban: apenas hierarquia daquele Corban
    const companyUsers = allUsers.filter((u) => u.company === group.company);
    if (group.by_leader && group.leader) {
      return companyUsers.filter(
        (u) =>
          u.id === group.leader ||
          (u.role === 'vendedor' && u.leader === group.leader),
      );
    }
    return companyUsers.filter((u) =>
      ['vendedor', 'lider', 'gerente', 'empresa_admin'].includes(u.role),
    );
  }, [allUsers, group]);

  // Split users into available and team members
  const availableUsers = useMemo(() => {
    return eligibleUsers.filter((u) => !teamMemberIds.includes(u.id));
  }, [eligibleUsers, teamMemberIds]);

  const teamMembers = useMemo(() => {
    return eligibleUsers.filter((u) => teamMemberIds.includes(u.id));
  }, [eligibleUsers, teamMemberIds]);

  // Filter by search
  const filteredAvailable = useMemo(() => {
    if (!searchAvailable) return availableUsers;
    const q = searchAvailable.toLowerCase();
    return availableUsers.filter(
      (u) =>
        u.first_name.toLowerCase().includes(q) ||
        u.last_name.toLowerCase().includes(q) ||
        u.cpf.includes(q),
    );
  }, [availableUsers, searchAvailable]);

  const filteredTeam = useMemo(() => {
    if (!searchTeam) return teamMembers;
    const q = searchTeam.toLowerCase();
    return teamMembers.filter(
      (u) =>
        u.first_name.toLowerCase().includes(q) ||
        u.last_name.toLowerCase().includes(q) ||
        u.cpf.includes(q),
    );
  }, [teamMembers, searchTeam]);

  function toggleAvailableSelection(userId: number) {
    setSelectedAvailable((prev) => {
      const next = new Set(prev);
      if (next.has(userId)) next.delete(userId);
      else next.add(userId);
      return next;
    });
  }

  function toggleTeamSelection(userId: number) {
    setSelectedTeam((prev) => {
      const next = new Set(prev);
      if (next.has(userId)) next.delete(userId);
      else next.add(userId);
      return next;
    });
  }

  const allFilteredAvailableSelected =
    filteredAvailable.length > 0 &&
    filteredAvailable.every((u) => selectedAvailable.has(u.id));
  const someFilteredAvailableSelected = filteredAvailable.some((u) =>
    selectedAvailable.has(u.id),
  );

  const allFilteredTeamSelected =
    filteredTeam.length > 0 && filteredTeam.every((u) => selectedTeam.has(u.id));
  const someFilteredTeamSelected = filteredTeam.some((u) => selectedTeam.has(u.id));

  const selectAllAvailableRef = useRef<HTMLInputElement>(null);
  const selectAllTeamRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const el = selectAllAvailableRef.current;
    if (el) {
      el.indeterminate = someFilteredAvailableSelected && !allFilteredAvailableSelected;
    }
  }, [someFilteredAvailableSelected, allFilteredAvailableSelected]);

  useEffect(() => {
    const el = selectAllTeamRef.current;
    if (el) {
      el.indeterminate = someFilteredTeamSelected && !allFilteredTeamSelected;
    }
  }, [someFilteredTeamSelected, allFilteredTeamSelected]);

  function toggleSelectAllAvailable() {
    setSelectedAvailable((prev) => {
      const next = new Set(prev);
      if (allFilteredAvailableSelected) {
        filteredAvailable.forEach((u) => next.delete(u.id));
      } else {
        filteredAvailable.forEach((u) => next.add(u.id));
      }
      return next;
    });
  }

  function toggleSelectAllTeam() {
    setSelectedTeam((prev) => {
      const next = new Set(prev);
      if (allFilteredTeamSelected) {
        filteredTeam.forEach((u) => next.delete(u.id));
      } else {
        filteredTeam.forEach((u) => next.add(u.id));
      }
      return next;
    });
  }

  function handleAddToTeam() {
    if (selectedAvailable.size === 0) return;
    setTeamMemberIds((prev) => [...prev, ...Array.from(selectedAvailable)]);
    setSelectedAvailable(new Set());
  }

  function handleRemoveFromTeam() {
    if (selectedTeam.size === 0) return;
    setTeamMemberIds((prev) => prev.filter((id) => !selectedTeam.has(id)));
    setSelectedTeam(new Set());
  }

  async function handleSave() {
    setSaving(true);
    try {
      await api.put(ENDPOINTS.COMMISSION_GROUP_MEMBERS(groupId), {
        user_ids: teamMemberIds,
      });
      toast.success('Equipe atualizada com sucesso!');
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin h-8 w-8 border-4 border-[var(--color-primary)] border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title={group?.name || 'Equipe'}
        subtitle={
          group?.company
            ? `${group.company_name || 'Corban'} — apenas usuários da hierarquia deste Corban`
            : group?.description || undefined
        }
        actions={
          <Button size="sm" onClick={handleSave} loading={saving} disabled={usersLoading}>
            <Check size={16} />
            Salvar equipe
          </Button>
        }
      />

      {group?.company !== null && <RegistrationLinksPanel groupId={groupId} />}

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto_1fr] gap-4">
        {/* LEFT: Available */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
            <div className="flex items-center justify-between gap-2">
              <label className="flex items-center gap-2 cursor-pointer min-w-0">
                <input
                  ref={selectAllAvailableRef}
                  type="checkbox"
                  checked={allFilteredAvailableSelected}
                  onChange={toggleSelectAllAvailable}
                  disabled={usersLoading || filteredAvailable.length === 0}
                  className="h-4 w-4 rounded border-gray-300 text-[var(--color-primary)] shrink-0"
                  title="Selecionar todos (visíveis)"
                />
                <h3 className="font-semibold text-sm text-gray-700 truncate">Disponiveis</h3>
              </label>
              <span className="text-xs text-gray-400 shrink-0">
                {usersLoading ? '…' : `${availableUsers.length} pessoas`}
              </span>
            </div>
            <div className="mt-2 relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar..."
                value={searchAvailable}
                onChange={(e) => setSearchAvailable(e.target.value)}
                disabled={usersLoading}
                className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)] disabled:bg-gray-50"
              />
            </div>
          </div>
          <div className="max-h-96 overflow-y-auto divide-y divide-gray-50">
            {usersLoading ? (
              <div className="flex flex-col items-center justify-center gap-2 px-4 py-10">
                <div className="animate-spin h-6 w-6 border-2 border-[var(--color-primary)] border-t-transparent rounded-full" />
                <p className="text-xs text-gray-400">Carregando usuários…</p>
              </div>
            ) : filteredAvailable.length === 0 ? (
              <p className="px-4 py-6 text-sm text-gray-400 text-center">Nenhuma pessoa disponivel</p>
            ) : (
              filteredAvailable.map((user) => (
                <button
                  key={user.id}
                  onClick={() => toggleAvailableSelection(user.id)}
                  className={clsx(
                    'w-full px-4 py-3 text-left flex items-center gap-3 transition-colors',
                    selectedAvailable.has(user.id)
                      ? 'bg-[var(--color-primary-bg)]'
                      : 'hover:bg-gray-50',
                  )}
                >
                  <input
                    type="checkbox"
                    checked={selectedAvailable.has(user.id)}
                    readOnly
                    className="h-4 w-4 rounded border-gray-300 text-[var(--color-primary)]"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">
                      {user.first_name} {user.last_name}
                    </p>
                    <p className="text-xs text-gray-400">{user.cpf}</p>
                  </div>
                  <span className={clsx('text-[10px] font-medium px-1.5 py-0.5 rounded-full', ROLE_COLORS[user.role as Role])}>
                    {ROLE_LABELS[user.role as Role]}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>

        {/* CENTER: Action buttons */}
        <div className="flex lg:flex-col items-center justify-center gap-2 py-4">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleAddToTeam}
            disabled={usersLoading || selectedAvailable.size === 0}
          >
            <span className="hidden lg:inline">Adicionar</span>
            <ChevronRight size={16} />
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleRemoveFromTeam}
            disabled={usersLoading || selectedTeam.size === 0}
          >
            <ChevronLeft size={16} />
            <span className="hidden lg:inline">Remover</span>
          </Button>
        </div>

        {/* RIGHT: Team Members */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
            <div className="flex items-center justify-between gap-2">
              <label className="flex items-center gap-2 cursor-pointer min-w-0">
                <input
                  ref={selectAllTeamRef}
                  type="checkbox"
                  checked={allFilteredTeamSelected}
                  onChange={toggleSelectAllTeam}
                  disabled={usersLoading || filteredTeam.length === 0}
                  className="h-4 w-4 rounded border-gray-300 text-red-500 shrink-0"
                  title="Selecionar todos (visíveis)"
                />
                <h3 className="font-semibold text-sm text-gray-700 truncate">Na Equipe</h3>
              </label>
              <span className="text-xs text-gray-400 shrink-0">
                {usersLoading ? '…' : `${teamMembers.length} pessoas`}
              </span>
            </div>
            <div className="mt-2 relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar..."
                value={searchTeam}
                onChange={(e) => setSearchTeam(e.target.value)}
                disabled={usersLoading}
                className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)] disabled:bg-gray-50"
              />
            </div>
          </div>
          <div className="max-h-96 overflow-y-auto divide-y divide-gray-50">
            {usersLoading ? (
              <div className="flex flex-col items-center justify-center gap-2 px-4 py-10">
                <div className="animate-spin h-6 w-6 border-2 border-[var(--color-primary)] border-t-transparent rounded-full" />
                <p className="text-xs text-gray-400">Carregando usuários…</p>
              </div>
            ) : filteredTeam.length === 0 ? (
              <p className="px-4 py-6 text-sm text-gray-400 text-center">Nenhum membro na equipe</p>
            ) : (
              filteredTeam.map((user) => (
                <button
                  key={user.id}
                  onClick={() => toggleTeamSelection(user.id)}
                  className={clsx(
                    'w-full px-4 py-3 text-left flex items-center gap-3 transition-colors',
                    selectedTeam.has(user.id)
                      ? 'bg-red-50'
                      : 'hover:bg-gray-50',
                  )}
                >
                  <input
                    type="checkbox"
                    checked={selectedTeam.has(user.id)}
                    readOnly
                    className="h-4 w-4 rounded border-gray-300 text-red-500"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">
                      {user.first_name} {user.last_name}
                    </p>
                    <p className="text-xs text-gray-400">{user.cpf}</p>
                  </div>
                  <span className={clsx('text-[10px] font-medium px-1.5 py-0.5 rounded-full', ROLE_COLORS[user.role as Role])}>
                    {ROLE_LABELS[user.role as Role]}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Commission Rules */}
      <div className="mt-8" data-tour="commission-rules-table">
        <CommissionRulesEditor
          groupId={groupId}
          ruleType={group?.company === null ? 'promotora' : 'group'}
          initialRules={
            group?.company === null
              ? (group?.promotora_rules || [])
              : (group?.commission_rules || [])
          }
        />
      </div>
    </div>
  );
}
