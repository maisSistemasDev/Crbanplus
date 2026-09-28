import { api } from './client';
import type { PaginatedResponse } from './types';

/** Busca todas as páginas de um endpoint paginado (DRF). */
export async function fetchAllPaginated<T>(
  endpoint: string,
  extraParams?: Record<string, string>,
  pageSize = 500,
): Promise<T[]> {
  const items: T[] = [];
  let page = 1;
  let total = Infinity;

  while (items.length < total) {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (extraParams) {
      Object.entries(extraParams).forEach(([k, v]) => {
        if (v) params.set(k, v);
      });
    }

    const res = await api.get<PaginatedResponse<T> | T[]>(`${endpoint}?${params}`);
    if (Array.isArray(res)) {
      return res;
    }

    items.push(...res.results);
    total = res.count;
    if (res.results.length === 0) break;
    page += 1;
  }

  return items;
}
