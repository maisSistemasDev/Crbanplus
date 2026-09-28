export function strField(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

export function numField(value: unknown): string {
  return typeof value === 'number' && !Number.isNaN(value) ? String(value) : '';
}

export function parseNumField(raw: string): number | undefined {
  if (raw.trim() === '') return undefined;
  const n = Number(raw);
  return Number.isNaN(n) ? undefined : n;
}
