import { atom, computed } from 'nanostores';
import type { User, TokenResponse } from '../api/types';

function loadTokens(): TokenResponse | null {
  if (typeof window === 'undefined') return null;
  try {
    const stored = localStorage.getItem('tokens');
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

function loadUser(): User | null {
  if (typeof window === 'undefined') return null;
  try {
    const stored = localStorage.getItem('user');
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

export const $tokens = atom<TokenResponse | null>(loadTokens());
export const $currentUser = atom<User | null>(loadUser());

export const $isAuthenticated = computed($tokens, (tokens) => !!tokens?.access);
export const $userRole = computed($currentUser, (user) => user?.role ?? null);

export function setAuth(tokens: TokenResponse, user: User) {
  $tokens.set(tokens);
  $currentUser.set(user);
  localStorage.setItem('tokens', JSON.stringify(tokens));
  localStorage.setItem('user', JSON.stringify(user));
}

export function updateCurrentUser(user: User) {
  $currentUser.set(user);
  localStorage.setItem('user', JSON.stringify(user));
}

export function clearAuth() {
  $tokens.set(null);
  $currentUser.set(null);
  localStorage.removeItem('tokens');
  localStorage.removeItem('user');
  localStorage.removeItem('theme');
}
