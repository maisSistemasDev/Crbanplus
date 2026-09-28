import type { EtlFlowNodeData } from '../api/types/etl';

export type ScheduleMode = 'daily' | 'weekdays' | 'weekly' | 'custom';

export const WEEKDAY_OPTIONS = [
  { value: 1, label: 'Seg' },
  { value: 2, label: 'Ter' },
  { value: 3, label: 'Qua' },
  { value: 4, label: 'Qui' },
  { value: 5, label: 'Sex' },
  { value: 6, label: 'Sáb' },
  { value: 0, label: 'Dom' },
];

function parseTime(time: string): { hour: number; minute: number } {
  const [h, m] = (time || '08:00').split(':');
  return { hour: Math.min(23, Math.max(0, Number(h) || 8)), minute: Math.min(59, Math.max(0, Number(m) || 0)) };
}

export function buildCronFromSchedule(data: EtlFlowNodeData): string {
  const mode = (data.schedule_mode as ScheduleMode) || 'weekdays';
  const { hour, minute } = parseTime(String(data.schedule_time || '08:00'));

  if (mode === 'custom') {
    return String(data.cron || '0 8 * * 1-5').trim();
  }
  if (mode === 'daily') {
    return `${minute} ${hour} * * *`;
  }
  if (mode === 'weekdays') {
    return `${minute} ${hour} * * 1-5`;
  }
  const days = Array.isArray(data.schedule_weekdays)
    ? [...new Set(data.schedule_weekdays.map(Number))].sort((a, b) => a - b)
  : [1, 2, 3, 4, 5];
  return `${minute} ${hour} * * ${days.join(',')}`;
}

export function buildScheduleSummary(data: EtlFlowNodeData): string {
  const mode = (data.schedule_mode as ScheduleMode) || 'weekdays';
  const time = String(data.schedule_time || '08:00');
  const tz = String(data.timezone || 'America/Sao_Paulo');

  if (mode === 'daily') return `Todos os dias às ${time} (${tz})`;
  if (mode === 'weekdays') return `Segunda a sexta às ${time} (${tz})`;
  if (mode === 'weekly') {
    const days = Array.isArray(data.schedule_weekdays) ? data.schedule_weekdays : [1, 2, 3, 4, 5];
    const labels = days
      .map((d) => WEEKDAY_OPTIONS.find((o) => o.value === Number(d))?.label || String(d))
      .join(', ');
    return `${labels} às ${time} (${tz})`;
  }
  return `Cron: ${data.cron || buildCronFromSchedule(data)} (${tz})`;
}

export function patchScheduleFields(partial: Partial<EtlFlowNodeData>): Partial<EtlFlowNodeData> {
  const merged = { ...partial };
  if (
    merged.schedule_mode !== undefined
    || merged.schedule_time !== undefined
    || merged.schedule_weekdays !== undefined
  ) {
    merged.cron = buildCronFromSchedule(merged as EtlFlowNodeData);
  }
  return merged;
}

export function normalizeScheduleData(data: EtlFlowNodeData): EtlFlowNodeData {
  const mode = (data.schedule_mode as ScheduleMode) || (data.cron ? 'custom' : 'weekdays');
  return {
    schedule_mode: mode,
    schedule_time: data.schedule_time || '08:00',
    schedule_weekdays: data.schedule_weekdays || [1, 2, 3, 4, 5],
    timezone: data.timezone || 'America/Sao_Paulo',
    cron: data.cron || buildCronFromSchedule({ ...data, schedule_mode: mode }),
    ...data,
  };
}
