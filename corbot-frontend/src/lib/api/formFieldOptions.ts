import { api } from './client';
import { ENDPOINTS } from './endpoints';
import type { FormFieldDef, PaginatedResponse } from './types';

export interface SelectOption {
  value: string | number;
  label: string;
}

const RELATION_ENDPOINTS: Record<string, string> = {
  Bank: ENDPOINTS.BANKS,
  User: `${ENDPOINTS.USERS}?page_size=500`,
  Company: `${ENDPOINTS.COMPANIES}?page_size=500`,
  BankAccess: `${ENDPOINTS.BANK_ACCESSES}?page_size=500`,
};

export function resolveOptionsUrl(field: FormFieldDef): string | undefined {
  if (field.options_url) return field.options_url;
  if (field.relation) return RELATION_ENDPOINTS[field.relation];
  return undefined;
}

export function itemToSelectOption(item: Record<string, unknown>): SelectOption {
  const name =
    (item.name as string) ||
    `${item.first_name || ''} ${item.last_name || ''}`.trim() ||
    (item.trading_name as string) ||
    (item.username as string) ||
    (item.label as string);

  let label = name || String(item.id ?? '');
  if (item.cpf && name) {
    label = `${name} (${item.cpf})`;
  }

  return {
    value: item.id as string | number,
    label,
  };
}

export async function fetchSelectOptions(url: string): Promise<SelectOption[]> {
  const data = await api.get<Record<string, unknown>[] | PaginatedResponse<Record<string, unknown>>>(url);
  const items = Array.isArray(data) ? data : (data.results ?? []);
  return items.map((item) => itemToSelectOption(item));
}
