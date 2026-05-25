import { atom } from 'nanostores';
import { API_URL } from '../api/client';

export interface WhitelabelConfig {
  systemName: string;
  logoUrl: string;
  loading: boolean;
}

const DEFAULT_CONFIG: WhitelabelConfig = {
  systemName: 'CorbanPlus',
  logoUrl: '',
  loading: true,
};

export const $whitelabel = atom<WhitelabelConfig>(DEFAULT_CONFIG);

let fetchPromise: Promise<void> | null = null;

export function fetchWhitelabel(): Promise<void> {
  if (typeof window === 'undefined') return Promise.resolve();
  if (fetchPromise) return fetchPromise;

  fetchPromise = (async () => {
    try {
      const response = await fetch(`${API_URL}/config/whitelabel/`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      if (response.ok) {
        const data = await response.json();
        $whitelabel.set({
          systemName: data.system_name ?? DEFAULT_CONFIG.systemName,
          logoUrl: data.logo_url ?? '',
          loading: false,
        });
        return;
      }
    } catch (error) {
      console.error('Erro ao carregar configurações de whitelabel:', error);
    }

    $whitelabel.set({ ...$whitelabel.get(), loading: false });
  })();

  return fetchPromise;
}

if (typeof window !== 'undefined') {
  fetchWhitelabel();
}
