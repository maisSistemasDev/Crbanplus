import type { EtlFlowNodeData } from '../../../../lib/api/types/etl';
import {
  WEEKDAY_OPTIONS,
  buildCronFromSchedule,
  buildScheduleSummary,
  type ScheduleMode,
} from '../../../../lib/etl/scheduleUtils';
import { Input } from '../../ui/Input';
import { SearchSelect } from '../../ui/SearchSelect';
import { strField } from './etlFormHelpers';

const SCHEDULE_MODE_OPTIONS = [
  { value: 'daily', label: 'Todos os dias' },
  { value: 'weekdays', label: 'Segunda a sexta' },
  { value: 'weekly', label: 'Dias específicos da semana' },
  { value: 'custom', label: 'Avançado (cron)' },
];

interface EtlScheduleConfigProps {
  data: EtlFlowNodeData;
  onChange: (partial: Partial<EtlFlowNodeData>) => void;
}

export function EtlScheduleConfig({ data, onChange }: EtlScheduleConfigProps) {
  const mode = (data.schedule_mode as ScheduleMode) || 'weekdays';
  const weekdays = Array.isArray(data.schedule_weekdays)
    ? data.schedule_weekdays.map(Number)
    : [1, 2, 3, 4, 5];

  function patch(partial: Partial<EtlFlowNodeData>) {
    const next = { ...data, ...partial };
    onChange({
      ...partial,
      cron: buildCronFromSchedule(next),
    });
  }

  return (
    <div className="space-y-3">
      <label className="block text-xs font-medium text-gray-600">Frequência</label>
      <SearchSelect
        value={mode}
        options={SCHEDULE_MODE_OPTIONS}
        onChange={(e) => patch({ schedule_mode: e.target.value as ScheduleMode })}
      />

      {mode !== 'custom' && (
        <Input
          label="Horário"
          type="time"
          value={String(data.schedule_time || '08:00')}
          onChange={(e) => patch({ schedule_time: e.target.value })}
        />
      )}

      {mode === 'weekly' && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-gray-600">Dias da semana</p>
          <div className="flex flex-wrap gap-1.5">
            {WEEKDAY_OPTIONS.map((day) => {
              const active = weekdays.includes(day.value);
              return (
                <button
                  key={day.value}
                  type="button"
                  onClick={() => {
                    const next = active
                      ? weekdays.filter((d) => d !== day.value)
                      : [...weekdays, day.value].sort((a, b) => a - b);
                    patch({ schedule_weekdays: next.length ? next : [day.value] });
                  }}
                  className={
                    active
                      ? 'px-2 py-1 text-xs rounded-md bg-violet-600 text-white'
                      : 'px-2 py-1 text-xs rounded-md border border-gray-200 text-gray-600 hover:bg-gray-50'
                  }
                >
                  {day.label}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {mode === 'custom' && (
        <Input
          label="Expressão cron"
          value={data.cron || ''}
          onChange={(e) => onChange({ cron: e.target.value })}
          placeholder="0 8 * * 1-5"
        />
      )}

      <Input
        label="Fuso horário"
        value={strField(data.timezone)}
        onChange={(e) => patch({ timezone: e.target.value })}
        placeholder="America/Sao_Paulo"
      />

      <div className="text-xs bg-violet-50 text-violet-900 rounded-lg p-2 space-y-1">
        <p className="font-medium">Resumo do agendamento</p>
        <p>{buildScheduleSummary(data)}</p>
        <p className="font-mono text-[10px] text-violet-700/80">cron: {data.cron || buildCronFromSchedule(data)}</p>
        <p className="text-violet-700/70">
          Marque &quot;Fluxo ativo&quot; na barra lateral e rode o Celery Beat para execução automática.
        </p>
      </div>
    </div>
  );
}
