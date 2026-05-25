import { useState, useEffect, useMemo } from 'react';
import { useStore } from '@nanostores/react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { $currentUser } from '../../../../lib/stores/auth';
import { Button } from '../../ui/Button';
import { Input } from '../../ui/Input';
import { Badge } from '../../ui/Badge';
import { ROLE_LABELS, ROLE_COLORS } from '../../../../lib/utils/roles';
import type { Role } from '../../../../lib/utils/roles';
import type { User, CommissionGroup } from '../../../../lib/api/types';
import clsx from 'clsx';
import { Search, ChevronRight, ChevronLeft, Check } from 'lucide-react';
import toast from 'react-hot-toast';
import { CommissionRulesEditor } from './CommissionRulesEditor';

interface TeamBuilderProps {
  groupId: number;
}

export function TeamBuilder({ groupId }: TeamBuilderProps) {
  const currentUser = useStore($currentUser);
  const [group, setGroup] = useState<CommissionGroup | null>(null);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [teamMemberIds, setTeamMemberIds] = useState<number[]>([]);
  const [selectedAvailable, setSelectedAvailable] = useState<Set<number>>(new Set());
  const [selectedTeam, setSelectedTeam] = useState<Set<number>>(new Set());
  const [searchAvailable, setSearchAvailable] = useState('');
  const [searchTeam, setSearchTeam] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [groupData, sellers] = await Promise.all([
          api.get<CommissionGroup>(ENDPOINTS.COMMISSION_GROUP_DETAIL(groupId)),
          api.get<User[]>(ENDPOINTS.SELLERS),
        ]);

        setGroup(groupData);
        const memberIds = [
          ...groupData.sellers,
          ...groupData.leaders,
        ];
        setTeamMemberIds(memberIds);

        // Load all available sellers (and leaders for gerente)
        const usersList = Array.isArray(sellers) ? sellers : (sellers as any).results || [];
        setAllUsers(usersList);
      } catch (error) {
        toast.error(extractErrorMessage(error));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [groupId]);

  // Filter by group type before splitting available/team
  const eligibleUsers = useMemo(() => {
    if (!group) return allUsers;
    if (group.company === null) {
      // Grupo por promotora: apenas empresa_admin (um por corban)
      return allUsers.filter((u) => u.role === 'empresa_admin');
    } else {
      // Grupo por empresa: apenas usuários da empresa vinculada ao grupo
      return allUsers.filter((u) => u.company === group.company);
    }
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
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{group?.name || 'Equipe'}</h1>
          {group?.description && (
            <p className="text-sm text-gray-500 mt-1">{group.description}</p>
          )}
        </div>
        <Button onClick={handleSave} loading={saving}>
          <Check size={16} />
          Salvar Equipe
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto_1fr] gap-4">
        {/* LEFT: Available */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-sm text-gray-700">Disponiveis</h3>
              <span className="text-xs text-gray-400">{availableUsers.length} pessoas</span>
            </div>
            <div className="mt-2 relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar..."
                value={searchAvailable}
                onChange={(e) => setSearchAvailable(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
              />
            </div>
          </div>
          <div className="max-h-96 overflow-y-auto divide-y divide-gray-50">
            {filteredAvailable.length === 0 ? (
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
            disabled={selectedAvailable.size === 0}
          >
            <span className="hidden lg:inline">Adicionar</span>
            <ChevronRight size={16} />
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleRemoveFromTeam}
            disabled={selectedTeam.size === 0}
          >
            <ChevronLeft size={16} />
            <span className="hidden lg:inline">Remover</span>
          </Button>
        </div>

        {/* RIGHT: Team Members */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-sm text-gray-700">Na Equipe</h3>
              <span className="text-xs text-gray-400">{teamMembers.length} pessoas</span>
            </div>
            <div className="mt-2 relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar..."
                value={searchTeam}
                onChange={(e) => setSearchTeam(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
              />
            </div>
          </div>
          <div className="max-h-96 overflow-y-auto divide-y divide-gray-50">
            {filteredTeam.length === 0 ? (
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
