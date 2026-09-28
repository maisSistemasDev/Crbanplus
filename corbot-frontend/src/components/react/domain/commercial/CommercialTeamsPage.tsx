import { useState, useEffect, useCallback, useMemo } from 'react';
import { useStore } from '@nanostores/react';
import { api } from '../../../../lib/api/client';
import { fetchAllPaginated } from '../../../../lib/api/pagination';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { $currentUser } from '../../../../lib/stores/auth';
import { isPromotoraAdmin } from '../../../../lib/utils/roles';
import type { Role } from '../../../../lib/utils/roles';
import type { PaginatedResponse } from '../../../../lib/api/types';
import { PageHeader } from '../../ui/PageHeader';
import { Button } from '../../ui/Button';
import { Select } from '../../ui/Select';
import { PageSpinner } from '../../ui/Spinner';
import { Badge } from '../../ui/Badge';
import { Search, ChevronRight, ChevronLeft, Check, X, Users } from 'lucide-react';
import toast from 'react-hot-toast';
import clsx from 'clsx';
import type { CommercialManager, TeamMember } from './types';
import { managerLabel, shortManagerName } from './types';

interface CorbanItem {
  id: string;
  name: string;
  trading_name?: string | null;
  document?: string | null;
  is_active?: boolean;
}

function readManagerQuery(): string {
  if (typeof window === 'undefined') return '';
  return new URLSearchParams(window.location.search).get('manager') || '';
}

function corbanSearchText(c: CorbanItem) {
  return `${c.name} ${c.trading_name || ''} ${c.document || ''}`.toLowerCase();
}

export function CommercialTeamsPage() {
  const user = useStore($currentUser);
  const canManage = isPromotoraAdmin((user?.role as Role) ?? null, user?.company ?? null);

  const [managers, setManagers] = useState<CommercialManager[]>([]);
  const [managerId, setManagerId] = useState(readManagerQuery);
  const [corbans, setCorbans] = useState<CorbanItem[]>([]);
  /** company_id → vínculo atual no servidor (qualquer gerente) */
  const [assignments, setAssignments] = useState<Record<string, TeamMember>>({});
  /** rascunho da equipe do gerente selecionado */
  const [teamCompanyIds, setTeamCompanyIds] = useState<string[]>([]);
  const [selectedLeft, setSelectedLeft] = useState<Set<string>>(new Set());
  const [selectedRight, setSelectedRight] = useState<Set<string>>(new Set());
  /** Filtro do box esquerdo: '' = todos | 'none' = sem gerente | id do gerente */
  const [leftManagerFilter, setLeftManagerFilter] = useState('');
  /** Filtro por termo do box esquerdo */
  const [leftSearch, setLeftSearch] = useState('');
  /** Filtro por termo do box direito */
  const [rightSearch, setRightSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const managerOptions = useMemo(
    () =>
      managers.map((m) => ({
        value: String(m.id),
        label: `${managerLabel(m)} (${m.cpf})`,
      })),
    [managers],
  );

  const leftManagerFilterOptions = useMemo(
    () => [
      { value: 'none', label: 'Sem Gerente' },
      ...managers.map((m) => ({
        value: String(m.id),
        label: shortManagerName(m),
      })),
    ],
    [managers],
  );

  const selectedManager = useMemo(
    () => managers.find((m) => String(m.id) === managerId) || null,
    [managers, managerId],
  );

  const managersById = useMemo(() => {
    const map: Record<number, CommercialManager> = {};
    managers.forEach((m) => {
      map[m.id] = m;
    });
    return map;
  }, [managers]);

  const loadBase = useCallback(async () => {
    setLoading(true);
    try {
      const [managersRes, corbanList, allAssignments] = await Promise.all([
        api.get<PaginatedResponse<CommercialManager> | CommercialManager[]>(ENDPOINTS.COMMERCIAL_MANAGERS),
        fetchAllPaginated<CorbanItem>(ENDPOINTS.COMPANIES),
        api.get<TeamMember[]>(ENDPOINTS.COMMERCIAL_TEAM),
      ]);
      const managerList = Array.isArray(managersRes) ? managersRes : managersRes.results;
      setManagers(managerList);
      setCorbans(corbanList.filter((c) => c.is_active !== false));

      const map: Record<string, TeamMember> = {};
      allAssignments.forEach((a) => {
        map[String(a.company)] = a;
      });
      setAssignments(map);

      setManagerId((prev) => {
        if (prev && managerList.some((m) => String(m.id) === prev)) return prev;
        return managerList.length > 0 ? String(managerList[0].id) : '';
      });
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!canManage) {
      setLoading(false);
      return;
    }
    loadBase();
  }, [canManage, loadBase]);

  // Ao trocar o gerente, carrega o rascunho a partir dos assignments
  useEffect(() => {
    if (!managerId) {
      setTeamCompanyIds([]);
      setSelectedLeft(new Set());
      setSelectedRight(new Set());
      return;
    }
    const ids = Object.values(assignments)
      .filter((a) => String(a.manager) === managerId)
      .map((a) => String(a.company));
    setTeamCompanyIds(ids);
    setSelectedLeft(new Set());
    setSelectedRight(new Set());

    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.set('manager', managerId);
      window.history.replaceState({}, '', url.toString());
    }
  }, [managerId, assignments]);

  const teamSet = useMemo(() => new Set(teamCompanyIds), [teamCompanyIds]);

  /** Gerente "efetivo" no rascunho (badge/filtro da esquerda). */
  function effectiveManagerId(companyId: string): string | null {
    if (teamSet.has(companyId)) {
      return managerId || null;
    }
    const assignment = assignments[companyId];
    if (!assignment) return null;
    // Saiu do rascunho do gerente atual → fica sem gerente na UI
    if (String(assignment.manager) === managerId) return null;
    return String(assignment.manager);
  }

  const leftCorbans = useMemo(() => {
    const q = leftSearch.trim().toLowerCase();
    return corbans
      .filter((c) => {
        if (!leftManagerFilter) return true;
        const effective = effectiveManagerId(c.id);
        if (leftManagerFilter === 'none') return effective === null;
        return effective === leftManagerFilter;
      })
      .filter((c) => (!q ? true : corbanSearchText(c).includes(q)))
      .sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [corbans, leftManagerFilter, leftSearch, teamSet, assignments, managerId]);

  const rightCorbans = useMemo(() => {
    const q = rightSearch.trim().toLowerCase();
    return corbans
      .filter((c) => teamSet.has(c.id))
      .filter((c) => (!q ? true : corbanSearchText(c).includes(q)))
      .sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'));
  }, [corbans, teamSet, rightSearch]);

  function badgeForCompany(companyId: string): {
    label: string;
    variant: 'default' | 'warning' | 'success' | 'info';
  } {
    if (teamSet.has(companyId) && selectedManager) {
      return { label: shortManagerName(selectedManager), variant: 'success' };
    }
    const assignment = assignments[companyId];
    if (!assignment) {
      return { label: 'Sem Gerente', variant: 'warning' };
    }
    if (String(assignment.manager) === managerId && !teamSet.has(companyId)) {
      return { label: 'Sem Gerente', variant: 'warning' };
    }
    const mgr = managersById[assignment.manager];
    if (mgr) {
      return { label: shortManagerName(mgr), variant: 'info' };
    }
    return {
      label: shortManagerName({
        first_name: assignment.manager_name?.split(' ')[0] || '',
        last_name: assignment.manager_name?.split(' ').slice(1).join(' ') || '',
        cpf: '',
      }),
      variant: 'info',
    };
  }

  function toggleLeft(id: string) {
    setSelectedLeft((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleRight(id: string) {
    setSelectedRight((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function clearRightSelection(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    setSelectedRight((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }

  const allLeftFilteredSelected =
    leftCorbans.length > 0 && leftCorbans.every((c) => selectedLeft.has(c.id));
  const allRightFilteredSelected =
    rightCorbans.length > 0 && rightCorbans.every((c) => selectedRight.has(c.id));

  function toggleSelectAllLeft() {
    if (leftCorbans.length === 0) return;
    setSelectedLeft((prev) => {
      const next = new Set(prev);
      if (allLeftFilteredSelected) {
        leftCorbans.forEach((c) => next.delete(c.id));
      } else {
        leftCorbans.forEach((c) => next.add(c.id));
      }
      return next;
    });
  }

  function toggleSelectAllRight() {
    if (rightCorbans.length === 0) return;
    setSelectedRight((prev) => {
      const next = new Set(prev);
      if (allRightFilteredSelected) {
        rightCorbans.forEach((c) => next.delete(c.id));
      } else {
        rightCorbans.forEach((c) => next.add(c.id));
      }
      return next;
    });
  }

  function handleAdd() {
    if (selectedLeft.size === 0) return;
    setTeamCompanyIds((prev) => [...prev, ...Array.from(selectedLeft).filter((id) => !prev.includes(id))]);
    setSelectedLeft(new Set());
  }

  function handleRemove() {
    if (selectedRight.size === 0) return;
    setTeamCompanyIds((prev) => prev.filter((id) => !selectedRight.has(id)));
    setSelectedRight(new Set());
  }

  async function handleSave() {
    if (!managerId) {
      toast.error('Selecione um gerente comercial.');
      return;
    }
    setSaving(true);
    try {
      const updated = await api.put<TeamMember[]>(ENDPOINTS.COMMERCIAL_TEAM, {
        manager: Number(managerId),
        company_ids: teamCompanyIds,
      });
      setAssignments((prev) => {
        const next: Record<string, TeamMember> = {};
        Object.entries(prev).forEach(([cid, member]) => {
          if (String(member.manager) !== managerId) {
            next[cid] = member;
          }
        });
        updated.forEach((m) => {
          next[String(m.company)] = m;
        });
        return next;
      });
      toast.success('Equipe salva com sucesso!');
      setSelectedLeft(new Set());
      setSelectedRight(new Set());
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  if (!canManage) {
    return (
      <div>
        <PageHeader title="Equipes" subtitle="Acesso restrito ao admin da promotora" />
        <p className="text-sm text-gray-500">Você não tem permissão para gerenciar equipes comerciais.</p>
      </div>
    );
  }

  if (loading) return <PageSpinner />;

  return (
    <div>
      <PageHeader
        title="Equipes"
        subtitle="Monte a carteira de corbans de cada gerente comercial"
        actions={
          <Button size="sm" onClick={handleSave} loading={saving} disabled={!managerId}>
            <Check size={16} />
            Salvar
          </Button>
        }
      />

      <div className="card mb-4 max-w-xl">
        <Select
          label="Gerente comercial"
          value={managerId}
          onChange={(e) => setManagerId(e.target.value)}
          options={managerOptions}
          placeholder="Selecione um gerente"
        />
      </div>

      {!managerId ? (
        <p className="text-sm text-gray-400">Selecione um gerente para montar a equipe.</p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto_1fr] gap-4 items-start">
          {/* LEFT — todos os corbans */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
              <div className="flex items-center justify-between gap-2 mb-2">
                <h3 className="font-semibold text-sm text-gray-700">Todos os corbans</h3>
                <span className="text-xs text-gray-400">{leftCorbans.length}</span>
              </div>
              <Select
                value={leftManagerFilter}
                onChange={(e) => {
                  setLeftManagerFilter(e.target.value);
                  setSelectedLeft(new Set());
                }}
                options={leftManagerFilterOptions}
                placeholder="Todos os gerentes"
              />
              <div className="relative mt-2">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Filtrar por nome, fantasia ou documento..."
                  value={leftSearch}
                  onChange={(e) => setLeftSearch(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
                />
              </div>
              <label className="mt-2 flex items-center gap-2 text-sm cursor-pointer select-none w-fit">
                <input
                  type="checkbox"
                  checked={allLeftFilteredSelected}
                  onChange={toggleSelectAllLeft}
                  disabled={leftCorbans.length === 0}
                  className="h-4 w-4 rounded border-gray-300 text-[var(--color-primary)] focus:ring-[var(--color-primary)] disabled:opacity-40"
                />
                <span className={clsx('text-xs', leftCorbans.length === 0 && 'text-gray-400')}>
                  Selecionar todos os filtrados
                </span>
              </label>
            </div>
            <div className="max-h-[28rem] overflow-y-auto divide-y divide-gray-50">
              {leftCorbans.length === 0 ? (
                <p className="px-4 py-6 text-sm text-gray-400 text-center">Nenhum corban encontrado</p>
              ) : (
                leftCorbans.map((c) => {
                  const badge = badgeForCompany(c.id);
                  const isSelected = selectedLeft.has(c.id);
                  const inCurrentTeam = teamSet.has(c.id);
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => toggleLeft(c.id)}
                      className={clsx(
                        'w-full flex items-center gap-2 px-3 py-2.5 text-left text-sm transition-colors',
                        isSelected
                          ? 'bg-[var(--color-primary)]/10 border-l-2 border-[var(--color-primary)]'
                          : 'hover:bg-gray-50 border-l-2 border-transparent',
                        inCurrentTeam && 'opacity-70',
                      )}
                    >
                      <Badge variant={badge.variant} className="shrink-0 text-[10px] max-w-[7rem] truncate">
                        {badge.label}
                      </Badge>
                      <span className="flex-1 min-w-0 truncate font-medium text-gray-800">{c.name}</span>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          {/* MIDDLE — setas */}
          <div className="flex lg:flex-col items-center justify-center gap-2 py-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={handleAdd}
              disabled={selectedLeft.size === 0}
              title="Incluir na equipe"
            >
              <ChevronRight size={18} />
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={handleRemove}
              disabled={selectedRight.size === 0}
              title="Remover da equipe"
            >
              <ChevronLeft size={18} />
            </Button>
          </div>

          {/* RIGHT — equipe do gerente */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
              <div className="flex items-center justify-between gap-2 mb-2">
                <h3 className="font-semibold text-sm text-gray-700 flex items-center gap-2">
                  <Users size={14} />
                  Equipe de {selectedManager ? shortManagerName(selectedManager) : 'gerente'}
                </h3>
                <span className="text-xs text-gray-400">{rightCorbans.length}</span>
              </div>
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Filtrar por nome, fantasia ou documento..."
                  value={rightSearch}
                  onChange={(e) => setRightSearch(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg outline-none focus:border-[var(--color-primary)]"
                />
              </div>
              <label className="mt-2 flex items-center gap-2 text-sm cursor-pointer select-none w-fit">
                <input
                  type="checkbox"
                  checked={allRightFilteredSelected}
                  onChange={toggleSelectAllRight}
                  disabled={rightCorbans.length === 0}
                  className="h-4 w-4 rounded border-gray-300 text-[var(--color-primary)] focus:ring-[var(--color-primary)] disabled:opacity-40"
                />
                <span className={clsx('text-xs', rightCorbans.length === 0 && 'text-gray-400')}>
                  Selecionar todos os filtrados
                </span>
              </label>
            </div>
            <div className="max-h-[28rem] overflow-y-auto divide-y divide-gray-50">
              {rightCorbans.length === 0 ? (
                <p className="px-4 py-6 text-sm text-gray-400 text-center">Nenhum corban na equipe</p>
              ) : (
                rightCorbans.map((c) => {
                  const isSelected = selectedRight.has(c.id);
                  const mgrBadge = selectedManager ? shortManagerName(selectedManager) : 'Gerente';
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => toggleRight(c.id)}
                      className={clsx(
                        'w-full flex items-center gap-2 px-3 py-2.5 text-left text-sm transition-colors',
                        isSelected
                          ? 'bg-[var(--color-primary)]/10 border-l-2 border-[var(--color-primary)]'
                          : 'hover:bg-gray-50 border-l-2 border-transparent',
                      )}
                    >
                      <span className="inline-flex items-center gap-1 shrink-0 rounded-full bg-emerald-100 text-emerald-800 px-2 py-0.5 text-[10px] font-medium">
                        {mgrBadge}
                        {isSelected && (
                          <span
                            role="button"
                            tabIndex={0}
                            title="Desselecionar"
                            onClick={(e) => clearRightSelection(c.id, e)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' || e.key === ' ') {
                                e.preventDefault();
                                clearRightSelection(c.id, e as unknown as React.MouseEvent);
                              }
                            }}
                            className="ml-0.5 inline-flex items-center justify-center rounded-full hover:bg-emerald-200 p-0.5"
                          >
                            <X size={10} />
                          </span>
                        )}
                      </span>
                      <span className="flex-1 min-w-0 truncate font-medium text-gray-800">{c.name}</span>
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}

      {managerId && (
        <div className="mt-4 flex justify-end">
          <Button onClick={handleSave} loading={saving}>
            <Check size={16} />
            Salvar equipe
          </Button>
        </div>
      )}
    </div>
  );
}
