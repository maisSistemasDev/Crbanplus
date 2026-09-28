export type DateRangePreset = '' | 'today' | 'last7' | 'last30' | 'thisMonth' | 'custom';

export const DATE_PRESET_OPTIONS = [
  { value: 'today', label: 'Hoje' },
  { value: 'last7', label: 'Ultimos 7 dias' },
  { value: 'last30', label: 'Ultimos 30 dias' },
  { value: 'thisMonth', label: 'Este mes' },
  { value: 'custom', label: 'Selecionar periodo' },
];

export function formatDateInput(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function resolveDateRange(preset: DateRangePreset, customBegin: string, customEnd: string) {
  const today = new Date();

  if (preset === 'custom') {
    return { begin: customBegin, end: customEnd };
  }

  if (preset === 'today') {
    const value = formatDateInput(today);
    return { begin: value, end: value };
  }

  if (preset === 'last7') {
    const begin = new Date(today);
    begin.setDate(today.getDate() - 6);
    return { begin: formatDateInput(begin), end: formatDateInput(today) };
  }

  if (preset === 'last30') {
    const begin = new Date(today);
    begin.setDate(today.getDate() - 29);
    return { begin: formatDateInput(begin), end: formatDateInput(today) };
  }

  if (preset === 'thisMonth') {
    const begin = new Date(today.getFullYear(), today.getMonth(), 1);
    return { begin: formatDateInput(begin), end: formatDateInput(today) };
  }

  return { begin: '', end: '' };
}
