import { useState, useEffect, useCallback, useMemo } from 'react';
import { useStore } from '@nanostores/react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { $currentUser } from '../../../../lib/stores/auth';
import { isPromotoraAdmin } from '../../../../lib/utils/roles';
import type { Role } from '../../../../lib/utils/roles';
import type { PaginatedResponse } from '../../../../lib/api/types';
import { PageHeader } from '../../ui/PageHeader';
import { Select } from '../../ui/Select';
import { Button } from '../../ui/Button';
import { PageSpinner } from '../../ui/Spinner';
import { CalendarDays, Landmark, Trophy, TrendingUp, Users } from 'lucide-react';
import toast from 'react-hot-toast';
import type { CommercialManager, DashboardData } from './types';
import { formatCurrency, managerLabel } from './types';

function formatDateInput(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function startOfMonth(date = new Date()) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function startOfWeek(date = new Date()) {
  const copy = new Date(date);
  const day = copy.getDay();
  const diff = day === 0 ? 6 : day - 1;
  copy.setDate(copy.getDate() - diff);
  return copy;
}

function readQuery(name: string): string {
  if (typeof window === 'undefined') return '';
  return new URLSearchParams(window.location.search).get(name) || '';
}

export function CommercialProductionPage() {
  const user = useStore($currentUser);
  const isAdmin = isPromotoraAdmin((user?.role as Role) ?? null, user?.company ?? null);
  const isGerenteComercial = user?.role === 'gerente_comercial';

  const [managers, setManagers] = useState<CommercialManager[]>([]);
  const [managerId, setManagerId] = useState(readQuery('manager'));
  const [dateFrom, setDateFrom] = useState(readQuery('date_from') || formatDateInput(startOfMonth()));
  const [dateTo, setDateTo] = useState(readQuery('date_to') || formatDateInput(new Date()));
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loadingManagers, setLoadingManagers] = useState(true);
  const [loadingDash, setLoadingDash] = useState(false);

  const managerOptions = useMemo(
    () =>
      managers.map((m) => ({
        value: String(m.id),
        label: `${managerLabel(m)} (${m.cpf})`,
      })),
    [managers],
  );

  useEffect(() => {
    (async () => {
      setLoadingManagers(true);
      try {
        if (isGerenteComercial && user) {
          setManagers([
            {
              id: user.id,
              cpf: user.cpf,
              email: user.email,
              first_name: user.first_name,
              last_name: user.last_name,
              is_active: user.is_active,
              team_size: 0,
            },
          ]);
          setManagerId(String(user.id));
        } else if (isAdmin) {
          const res = await api.get<PaginatedResponse<CommercialManager> | CommercialManager[]>(
            `${ENDPOINTS.COMMERCIAL_MANAGERS}?page_size=200`,
          );
          const list = Array.isArray(res) ? res : res.results;
          setManagers(list);
          if (!managerId && list.length > 0) {
            setManagerId(String(list[0].id));
          }
        } else {
          setManagers([]);
        }
      } catch (error) {
        toast.error(extractErrorMessage(error));
      } finally {
        setLoadingManagers(false);
      }
    })();
  }, [isAdmin, isGerenteComercial, user?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadDashboard = useCallback(async () => {
    if (!managerId && !isGerenteComercial) {
      setDashboard(null);
      return;
    }
    setLoadingDash(true);
    try {
      const qs = new URLSearchParams();
      if (managerId) qs.set('manager', managerId);
      if (dateFrom) qs.set('date_from', dateFrom);
      if (dateTo) qs.set('date_to', dateTo);
      const dashRes = await api.get<DashboardData>(`${ENDPOINTS.COMMERCIAL_DASHBOARD}?${qs.toString()}`);
      setDashboard(dashRes);
    } catch (error) {
      toast.error(extractErrorMessage(error));
      setDashboard(null);
    } finally {
      setLoadingDash(false);
    }
  }, [managerId, dateFrom, dateTo, isGerenteComercial]);

  useEffect(() => {
    loadDashboard();
    if (typeof window === 'undefined') return;
    const url = new URL(window.location.href);
    if (managerId) url.searchParams.set('manager', managerId);
    else url.searchParams.delete('manager');
    if (dateFrom) url.searchParams.set('date_from', dateFrom);
    else url.searchParams.delete('date_from');
    if (dateTo) url.searchParams.set('date_to', dateTo);
    else url.searchParams.delete('date_to');
    url.searchParams.delete('period');
    window.history.replaceState({}, '', url.toString());
  }, [loadDashboard, managerId, dateFrom, dateTo]);

  function applyPreset(kind: 'week' | 'month' | '30') {
    const today = new Date();
    if (kind === 'week') setDateFrom(formatDateInput(startOfWeek(today)));
    if (kind === 'month') setDateFrom(formatDateInput(startOfMonth(today)));
    if (kind === '30') {
      const begin = new Date(today);
      begin.setDate(today.getDate() - 29);
      setDateFrom(formatDateInput(begin));
    }
    setDateTo(formatDateInput(today));
  }

  if (!isAdmin && !isGerenteComercial) {
    return (
      <div>
        <PageHeader title="Dashboard comercial" subtitle="Acesso restrito" />
        <p className="text-sm text-gray-500">Você não tem permissão para ver a produção comercial.</p>
      </div>
    );
  }

  if (loadingManagers) return <PageSpinner />;

  const periodLabel =
    dashboard?.date_from && dashboard?.date_to
      ? `${dashboard.date_from.split('-').reverse().join('/')} – ${dashboard.date_to.split('-').reverse().join('/')}`
      : `${dateFrom} – ${dateTo}`;

  return (
    <div>
      <PageHeader
        title={isGerenteComercial ? 'Dashboard da operação' : 'Dashboard comercial'}
        subtitle={
          isAdmin
            ? 'Produção da carteira por gerente, com filtro de período por dia'
            : 'Visão geral da produção da sua equipe'
        }
      />

      <div className="card mb-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 items-end">
          {(isAdmin || isGerenteComercial) && (
            <Select
              label="Gerente"
              value={managerId}
              onChange={(e) => setManagerId(e.target.value)}
              options={managerOptions}
              placeholder="Selecione um gerente"
              disabled={isGerenteComercial}
            />
          )}
          <label className="block">
            <span className="block text-sm font-medium text-gray-700 mb-1">De</span>
            <input
              type="date"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="block text-sm font-medium text-gray-700 mb-1">Até</span>
            <input
              type="date"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" onClick={() => applyPreset('week')}>
              Esta semana
            </Button>
            <Button size="sm" variant="secondary" onClick={() => applyPreset('month')}>
              Este mês
            </Button>
            <Button size="sm" variant="secondary" onClick={() => applyPreset('30')}>
              30 dias
            </Button>
          </div>
        </div>
      </div>

      {!managerId ? (
        <p className="text-sm text-gray-400">Selecione um gerente para ver a produção.</p>
      ) : loadingDash && !dashboard ? (
        <PageSpinner />
      ) : !dashboard ? (
        <p className="text-sm text-gray-400">Sem dados de produção.</p>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 mb-4">
            <div className="card">
              <p className="text-xs text-gray-500 flex items-center gap-1">
                <CalendarDays size={14} /> Produtividade do mês
                {dashboard.productivity_month.label ? ` (${dashboard.productivity_month.label})` : ''}
              </p>
              <p className="text-lg font-semibold text-gray-900 mt-1">
                {formatCurrency(dashboard.productivity_month.amount)}
              </p>
              <p className="text-xs text-gray-500">{dashboard.productivity_month.count} proposta(s)</p>
            </div>
            <div className="card">
              <p className="text-xs text-gray-500 flex items-center gap-1">
                <TrendingUp size={14} /> Produtividade da semana
                {dashboard.productivity_week.label ? ` (${dashboard.productivity_week.label})` : ''}
              </p>
              <p className="text-lg font-semibold text-gray-900 mt-1">
                {formatCurrency(dashboard.productivity_week.amount)}
              </p>
              <p className="text-xs text-gray-500">{dashboard.productivity_week.count} proposta(s)</p>
            </div>
            <div className="card">
              <p className="text-xs text-gray-500 flex items-center gap-1">
                <Users size={14} /> Período selecionado
              </p>
              <p className="text-[11px] text-gray-400">{periodLabel}</p>
              <p className="text-lg font-semibold text-gray-900 mt-1">
                {formatCurrency(dashboard.productivity_period.amount)}
              </p>
              <p className="text-xs text-gray-500">{dashboard.productivity_period.count} proposta(s)</p>
            </div>
            <div className="card">
              <p className="text-xs text-gray-500 flex items-center gap-1">
                <Landmark size={14} /> Banco que mais produziu
              </p>
              {dashboard.top_bank ? (
                <>
                  <p className="text-lg font-semibold text-gray-900 mt-1">{dashboard.top_bank.bank_name}</p>
                  <p className="text-xs text-gray-500">
                    {formatCurrency(dashboard.top_bank.total_amount)} · {dashboard.top_bank.total_count} proposta(s)
                  </p>
                </>
              ) : (
                <p className="text-sm text-gray-400 mt-2">Sem produção no período.</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
            <div className="card">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1">
                <Trophy size={14} /> Top 10 de produção
              </h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-500 border-b">
                    <th className="text-left py-1">#</th>
                    <th className="text-left py-1">Corban</th>
                    <th className="text-left py-1">Propostas</th>
                    <th className="text-left py-1">Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {(dashboard.top_10 || []).map((c, idx) => (
                    <tr key={c.company_id} className="border-b border-gray-50">
                      <td className="py-1">{idx + 1}</td>
                      <td className="py-1">{c.company_name}</td>
                      <td className="py-1">{c.total_count}</td>
                      <td className="py-1">{formatCurrency(c.total_amount)}</td>
                    </tr>
                  ))}
                  {(dashboard.top_10 || []).length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-2 text-xs text-gray-400">
                        Sem produção no período.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="card">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Produção por banco</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-500 border-b">
                    <th className="text-left py-1">Banco</th>
                    <th className="text-left py-1">Propostas</th>
                    <th className="text-left py-1">Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {(dashboard.production_by_bank || []).map((b) => (
                    <tr key={b.bank_id} className="border-b border-gray-50">
                      <td className="py-1">{b.bank_name}</td>
                      <td className="py-1">{b.total_count}</td>
                      <td className="py-1">{formatCurrency(b.total_amount)}</td>
                    </tr>
                  ))}
                  {(dashboard.production_by_bank || []).length === 0 && (
                    <tr>
                      <td colSpan={3} className="py-2 text-xs text-gray-400">
                        Sem produção por banco no período.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Evolução no período</h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-500 border-b">
                  <th className="text-left py-1">Data</th>
                  <th className="text-left py-1">Propostas</th>
                  <th className="text-left py-1">Valor</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.production_by_period.map((p) => (
                  <tr key={p.period || 'null'} className="border-b border-gray-50">
                    <td className="py-1">{p.period || '—'}</td>
                    <td className="py-1">{p.count}</td>
                    <td className="py-1">{formatCurrency(p.amount)}</td>
                  </tr>
                ))}
                {dashboard.production_by_period.length === 0 && (
                  <tr>
                    <td colSpan={3} className="py-2 text-xs text-gray-400">
                      Sem produção no intervalo.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
