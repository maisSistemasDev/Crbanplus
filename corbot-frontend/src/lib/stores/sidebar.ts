import { atom } from 'nanostores';

function loadCollapsed(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return localStorage.getItem('sidebar_collapsed') === 'true';
  } catch {
    return false;
  }
}

export const $sidebarCollapsed = atom<boolean>(loadCollapsed());
export const $sidebarMobileOpen = atom<boolean>(false);

export function toggleSidebar() {
  const next = !$sidebarCollapsed.get();
  $sidebarCollapsed.set(next);
  localStorage.setItem('sidebar_collapsed', String(next));
}

export function setSidebarCollapsed(collapsed: boolean) {
  $sidebarCollapsed.set(collapsed);
  localStorage.setItem('sidebar_collapsed', String(collapsed));
}

export function openMobileSidebar() {
  $sidebarMobileOpen.set(true);
}

export function closeMobileSidebar() {
  $sidebarMobileOpen.set(false);
}
