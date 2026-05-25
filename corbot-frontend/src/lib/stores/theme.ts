import { atom } from 'nanostores';

export interface ThemeConfig {
  primaryColor: string;
  secondaryColor: string;
  accentColor: string;
  logoUrl: string | null;
}

const DEFAULT_THEME: ThemeConfig = {
  primaryColor: '#3498db',
  secondaryColor: '#2c3e50',
  accentColor: '#e74c3c',
  logoUrl: null,
};

function loadTheme(): ThemeConfig {
  if (typeof window === 'undefined') return DEFAULT_THEME;
  try {
    const stored = localStorage.getItem('theme');
    return stored ? JSON.parse(stored) : DEFAULT_THEME;
  } catch {
    return DEFAULT_THEME;
  }
}

export const $theme = atom<ThemeConfig>(loadTheme());

export function applyTheme(config: ThemeConfig) {
  $theme.set(config);
  localStorage.setItem('theme', JSON.stringify(config));

  if (typeof document === 'undefined') return;

  const root = document.documentElement;
  root.style.setProperty('--color-primary', config.primaryColor);
  root.style.setProperty('--color-secondary', config.secondaryColor);
  root.style.setProperty('--color-accent', config.accentColor);
}

export function initTheme() {
  const config = loadTheme();
  applyTheme(config);
}
