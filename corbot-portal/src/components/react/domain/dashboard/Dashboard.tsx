import { useEffect, useMemo, useState } from 'react';
import { useStore } from '@nanostores/react';
import {
  BriefcaseBusiness,
  Calculator,
  CircleDollarSign,
  Clock3,
  Megaphone,
  PhoneCall,
  Shuffle,
} from 'lucide-react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { $currentUser } from '../../../../lib/stores/auth';
import { formatCurrency, formatDateTime } from '../../../../lib/utils/format';
import type { PortalContentFeed, PortalDashboard } from '../../../../lib/api/types';
import { SectionSpinner } from '../../ui/Spinner';

interface DashboardMetric {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
}

const EMPTY_DASHBOARD: PortalDashboard = {
  generated_at: '',
  month_proposals_count: 0,
  averbadas_value: 0,
  analysis_value: 0,
  predicted_commission: 0,
  received_commission: 0,
  advances_value: 0,
  physical_pending_count: 0,
  open_tickets_count: 0,
  received_by_month: [],
};

function formatAxisValue(value: number): string {
  if (value >= 1000) {
    return `${(value / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}k`;
  }
  return value.toLocaleString('pt-BR', { maximumFractionDigits: 0 });
}

export function Dashboard() {
  const user = useStore($currentUser);
  const [dashboard, setDashboard] = useState<PortalDashboard>(EMPTY_DASHBOARD);
  const [contentFeed, setContentFeed] = useState<PortalContentFeed>({ links: [], wall_messages: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      api.get<PortalDashboard>(ENDPOINTS.PORTAL_DASHBOARD),
      api.get<PortalContentFeed>(ENDPOINTS.PORTAL_CONTENT_FEED),
    ])
      .then(([dashboardRes, contentRes]) => {
        setDashboard(dashboardRes ?? EMPTY_DASHBOARD);
        setContentFeed(contentRes ?? { links: [], wall_messages: [] });
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  const metrics = useMemo<DashboardMetric[]>(
    () => [
      {
        label: 'Propostas Averbadas',
        value: formatCurrency(dashboard.averbadas_value),
        icon: CircleDollarSign,
      },
      {
        label: 'Propostas em Analise',
        value: formatCurrency(dashboard.analysis_value),
        icon: Clock3,
      },
      {
        label: 'Comissao Prevista',
        value: formatCurrency(dashboard.predicted_commission),
        icon: Calculator,
      },
      {
        label: 'Adiantamentos / Estornos',
        value: formatCurrency(dashboard.advances_value),
        icon: Shuffle,
      },
      {
        label: 'Pendencias de Fisico',
        value: `${dashboard.physical_pending_count} Propostas`,
        icon: BriefcaseBusiness,
      },
      {
        label: 'Pendencias de Fisico (Pago ao Corretor)',
        value: `${dashboard.physical_pending_count} Propostas`,
        icon: BriefcaseBusiness,
      },
      {
        label: 'Chamados Abertos',
        value: `${dashboard.open_tickets_count} Chamados`,
        icon: PhoneCall,
      },
    ],
    [dashboard],
  );

  const chartValues = dashboard.received_by_month;
  const chartMax = Math.max(...chartValues.map((item) => item.value), 0);
  const scaleMax = chartMax > 0 ? chartMax : 1;
  const receivedTotal =
    dashboard.received_commission ??
    chartValues.reduce((sum, item) => sum + (item.value || 0), 0);

  const firstName = `${user?.first_name ?? ''} ${user?.last_name ?? ''}`.trim() || 'Usuario';

  return (
    <div className="space-y-5">
      <div>
        <h1 className="page-title">Olá, {firstName}</h1>
        <p className="page-subtitle">Resumo da sua conta e atalhos do dia.</p>
      </div>

      {loading ? (
        <SectionSpinner />
      ) : error ? (
        <div className="card text-sm text-red-600">{error}</div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,470px)]">
            <div className="card">
              <p className="mb-2 text-center text-sm text-[var(--color-text-muted)]">
                Ultima Atualizacao:{' '}
                {dashboard.generated_at ? formatDateTime(dashboard.generated_at) : formatDateTime(new Date())}
              </p>
              <div className="h-[180px] w-full rounded-md border border-[var(--color-border)] bg-white p-3">
                <svg viewBox="0 0 520 170" className="h-full w-full">
                  <line x1="45" y1="20" x2="45" y2="130" stroke="#374151" strokeWidth="1" />
                  <line x1="45" y1="130" x2="500" y2="130" stroke="#374151" strokeWidth="1" />
                  <text x="8" y="25" fontSize="11" fill="#6b7280">
                    {formatAxisValue(scaleMax)}
                  </text>
                  <text x="8" y="79" fontSize="11" fill="#6b7280">
                    {formatAxisValue(scaleMax / 2)}
                  </text>
                  <text x="22" y="134" fontSize="11" fill="#6b7280">
                    0
                  </text>
                  {chartValues.map((item, index) => {
                    const x = 85 + index * 95;
                    const y = 130 - (item.value / scaleMax) * 100;
                    const next = chartValues[index + 1];
                    const nextX = x + 95;
                    const nextY = next !== undefined ? 130 - (next.value / scaleMax) * 100 : y;
                    return (
                      <g key={`${item.label}-${item.year}`}>
                        {next !== undefined && (
                          <line x1={x} y1={y} x2={nextX} y2={nextY} stroke="#3f6f29" strokeWidth="2" />
                        )}
                        <circle cx={x} cy={y} r="4" fill="#3f6f29" />
                        <text x={x - 12} y="156" fontSize="12" fill="#374151">
                          {item.label}
                        </text>
                      </g>
                    );
                  })}
                  <text x="258" y="168" fontSize="14" fontWeight="600" fill="#1f2937">
                    Comissao Recebida
                  </text>
                </svg>
              </div>
              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="rounded-md border border-[var(--color-border)] bg-white px-4 py-3">
                  <p className="break-words text-center text-2xl font-bold text-[#1f2937] md:text-3xl">
                    {formatCurrency(receivedTotal)}
                  </p>
                  <p className="mt-1 text-center text-sm text-[var(--color-text-muted)]">Comissões recebidas</p>
                </div>
                <div className="rounded-md border border-[var(--color-border)] bg-white px-4 py-3">
                  <p className="text-center text-2xl font-bold text-[#1f2937] md:text-3xl">
                    {dashboard.month_proposals_count}
                  </p>
                  <p className="mt-1 text-center text-sm text-[var(--color-text-muted)]">Total de Propostas do Mês</p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {metrics.map((metric) => {
                const Icon = metric.icon;
                return (
                  <div key={metric.label} className="card flex min-h-[96px] flex-col items-center justify-center px-2 py-3 text-center">
                    <Icon className="h-6 w-6 text-[#f59e0b] md:h-7 md:w-7" />
                    <p className="mt-1 text-[12px] text-[#4b5563] md:text-[13px]">{metric.label}</p>
                    <p className="mt-1 break-words text-xl font-semibold text-[#111827] sm:text-2xl md:text-3xl xl:text-4xl">{metric.value}</p>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div>
              <h2 className="mb-2 text-2xl font-semibold leading-none text-[#1f2937] md:text-[36px]">Comunicados</h2>
              <div className="card h-[250px] overflow-y-auto border-[#f0e2d6] bg-[#faeee5]">
                {contentFeed.wall_messages.length === 0 ? null : (
                  <div className="space-y-2">
                    {contentFeed.wall_messages.map((msg) => (
                      <div key={msg.id} className="rounded border border-[#efd8c5] bg-[#fff7ef] px-3 py-2">
                        <p className="text-sm font-semibold text-[#6b4b30]">{msg.title}</p>
                        <p className="text-xs text-[#7a5c43]">{msg.message}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div>
              <h2 className="mb-2 text-2xl font-semibold leading-none text-[#1f2937] md:text-[36px]">Mural de Mensagens</h2>
              <div className="card h-[250px] overflow-hidden p-6">
                {contentFeed.wall_messages.length === 0 ? (
                  <div className="flex h-full items-center justify-center rounded bg-[#f4f4f4] px-3 text-center text-base font-semibold text-[#d93b2f] md:text-xl">
                    Nao foram encontradas mensagens para voce.
                  </div>
                ) : (
                  <div className="h-full space-y-2 overflow-y-auto">
                    {contentFeed.wall_messages.map((msg) => (
                      <div key={`mural-${msg.id}`} className="rounded border border-gray-200 bg-gray-50 px-3 py-2">
                        <p className="text-sm font-semibold text-[#1f2937]">{msg.title}</p>
                        <p className="text-xs text-[var(--color-text-muted)]">{msg.message}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div>
            <h2 className="mb-2 text-2xl font-semibold leading-none text-[#1f2937] md:text-[36px]">Links Uteis</h2>
            <div className="card p-0">
              {contentFeed.links.length === 0 ? (
                <div className="px-4 py-8 text-sm text-[var(--color-text-muted)]">&nbsp;</div>
              ) : (
                contentFeed.links.map((link, index) => (
                  <a
                    key={link.id}
                    href={link.url}
                    target="_blank"
                    rel="noreferrer"
                    className={`flex items-center gap-3 px-4 py-3 transition-colors hover:bg-gray-50 ${
                      index < contentFeed.links.length - 1 ? 'border-b border-gray-100' : ''
                    }`}
                  >
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--color-primary-bg)]">
                      <Megaphone className="h-4 w-4 text-[var(--color-primary-dark)]" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-[#1f2937]">{link.title}</p>
                      <p className="text-xs text-[var(--color-text-muted)]">{link.url}</p>
                    </div>
                  </a>
                ))
              )}
            </div>
          </div>
        </>
      )}

    </div>
  );
}
