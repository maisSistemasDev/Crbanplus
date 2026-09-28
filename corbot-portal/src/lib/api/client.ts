import { $tokens, clearAuth } from '../stores/auth';

// PUBLIC_API_URL é embutido em build-time pelo Vite/Astro.
// Em dev (.env): http://localhost:8000
// Em prod (Dockerfile): "" → usa caminhos relativos (/api/...) que passam pelo proxy
// Em produção o Dockerfile passa PUBLIC_API_URL="" (string vazia) para que o
// cliente use caminhos relativos (/api/...) e passe pelo proxy reverso.
// Usamos ?? em vez de || para não substituir string vazia pelo fallback.
export const API_BASE_URL =
  (import.meta.env.PUBLIC_API_URL as string | undefined)?.replace(/\/+$/, '') ?? '';

/** Resolve URL de mídia/arquivo retornada pela API (ex.: /media/bank_logos/x.png). */
export function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (/^(https?:|blob:|data:)/.test(url)) return url;
  const path = url.startsWith('/') ? url : `/${url}`;
  if (API_BASE_URL) return `${API_BASE_URL}${path}`;
  return path;
}

export const API_URL = `${API_BASE_URL}/api`;

const API_BASE = API_URL;

export class ApiError extends Error {
  constructor(
    public status: number,
    public data: Record<string, unknown>,
  ) {
    // Tentar extrair mensagem mais específica
    let message = `API Error ${status}`;
    
    if (data && typeof data === 'object') {
      // Tentar diferentes campos de mensagem
      const errorMsg = 
        (data.error as string) || 
        (data.detail as string) || 
        (data.message as string);
      
      if (errorMsg) {
        message = errorMsg;
      }
    }
    
    super(message);
    this.name = 'ApiError';
    
    // Log detalhado em desenvolvimento
    if (import.meta.env.DEV) {
      console.error('API Error:', {
        status,
        message,
        data,
      });
    }
  }
}

let isRefreshing = false;
let refreshQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

function processRefreshQueue(token: string | null, error: unknown) {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (token) resolve(token);
    else reject(error);
  });
  refreshQueue = [];
}

export async function refreshAccessToken(): Promise<string | null> {
  const tokens = $tokens.get();
  if (!tokens?.refresh) return null;

  if (isRefreshing) {
    return new Promise<string>((resolve, reject) => {
      refreshQueue.push({ resolve, reject });
    });
  }

  isRefreshing = true;

  try {
    const response = await fetch(`${API_BASE}/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: tokens.refresh }),
    });

    if (!response.ok) {
      clearAuth();
      processRefreshQueue(null, new Error('Refresh failed'));
      return null;
    }

    const data = await response.json();
    const newTokens = { access: data.access, refresh: tokens.refresh };
    $tokens.set(newTokens);
    localStorage.setItem('tokens', JSON.stringify(newTokens));

    processRefreshQueue(data.access, null);
    return data.access;
  } catch (err) {
    clearAuth();
    processRefreshQueue(null, err);
    return null;
  } finally {
    isRefreshing = false;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const tokens = $tokens.get();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  if (tokens?.access) {
    headers['Authorization'] = `Bearer ${tokens.access}`;
  }

  let response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && tokens?.refresh) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers['Authorization'] = `Bearer ${newToken}`;
      response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
      });
    } else {
      window.location.href = `${window.location.origin}/login`;
      throw new ApiError(401, { detail: 'Session expired' });
    }
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(response.status, error);
  }

  if (response.status === 204) return undefined as T;

  return response.json();
}

export const api = {
  get: <T>(url: string) => request<T>(url),
  post: <T>(url: string, data?: unknown) =>
    request<T>(url, {
      method: 'POST',
      body: data instanceof FormData ? data : JSON.stringify(data),
    }),
  put: <T>(url: string, data?: unknown) =>
    request<T>(url, {
      method: 'PUT',
      body: data instanceof FormData ? data : JSON.stringify(data),
    }),
  patch: <T>(url: string, data?: unknown) =>
    request<T>(url, {
      method: 'PATCH',
      body: data instanceof FormData ? data : JSON.stringify(data),
    }),
  delete: <T>(url: string, data?: unknown) =>
    request<T>(url, {
      method: 'DELETE',
      body: data ? JSON.stringify(data) : undefined,
    }),
  upload: <T>(url: string, formData: FormData, method: string = 'POST') =>
    request<T>(url, { method, body: formData }),
  /** Faz GET autenticado e retorna o corpo como Blob (para downloads). */
  getBlob: async (url: string): Promise<{ blob: Blob; filename: string }> => {
    const tokens = $tokens.get();
    const headers: Record<string, string> = {};
    if (tokens?.access) headers['Authorization'] = `Bearer ${tokens.access}`;
    const response = await fetch(`${API_BASE}${url}`, { headers });
    if (!response.ok) throw new ApiError(response.status, await response.json().catch(() => ({})));
    const disposition = response.headers.get('Content-Disposition') ?? '';
    const match = disposition.match(/filename[^;=\n]*=(['"]?)([^'"\n;]+)\1/);
    const filename = match?.[2] ?? 'download';
    return { blob: await response.blob(), filename };
  },
};
