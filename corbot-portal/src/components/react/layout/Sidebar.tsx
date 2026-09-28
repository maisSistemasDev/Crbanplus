import { useEffect, useState } from 'react';
import { useStore } from '@nanostores/react';
import clsx from 'clsx';
import { ChevronDown, ChevronsLeft, ChevronsRight, X } from 'lucide-react';
import { $currentUser } from '../../../lib/stores/auth';
import { $sidebarCollapsed, $sidebarMobileOpen, toggleSidebar, closeMobileSidebar } from '../../../lib/stores/sidebar';
import { $whitelabel } from '../../../lib/stores/whitelabel';
import { NAV_ITEMS, filterNavForRole } from './nav';
import type { Role } from '../../../lib/utils/roles';

function isActive(href: string, pathname: string): boolean {
  if (href === '/dashboard') return pathname === '/dashboard' || pathname === '/';
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar({ isMobile = false }: { isMobile?: boolean }) {
  const user = useStore($currentUser);
  const collapsed = useStore($sidebarCollapsed);
  const mobileOpen = useStore($sidebarMobileOpen);
  const whitelabel = useStore($whitelabel);
  const [pathname, setPathname] = useState('');
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set());

  useEffect(() => {
    setPathname(window.location.pathname);
  }, []);

  useEffect(() => {
    const items = filterNavForRole(NAV_ITEMS, (user?.role as Role) ?? null);
    const initiallyOpen = new Set<string>();
    items.forEach((item) => {
      if (item.children?.some((c) => isActive(c.href, pathname))) {
        initiallyOpen.add(item.label);
      }
    });
    setOpenGroups(initiallyOpen);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, user?.role]);

  const items = filterNavForRole(NAV_ITEMS, (user?.role as Role) ?? null);

  function toggleGroup(label: string) {
    setOpenGroups((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  }

  const compact = collapsed && !isMobile;

  return (
    <aside
      className={clsx(
        'fixed top-0 z-50 flex h-screen flex-col bg-[var(--color-sidebar-bg)] transition-transform duration-200',
        isMobile ? 'left-0' : 'left-0',
        isMobile && !mobileOpen && '-translate-x-full',
      )}
      style={{ width: compact ? 'var(--sidebar-collapsed-width)' : 'var(--sidebar-width)' }}
    >
      <div
        className="flex items-center border-b border-[var(--color-sidebar-border)] px-4"
        style={{ height: 'var(--header-height)' }}
      >
        {!compact && (
          <span className="truncate text-sm font-semibold text-white">
            {whitelabel.systemName || 'Portal Corban'}
          </span>
        )}
        {isMobile && (
          <button
            type="button"
            onClick={closeMobileSidebar}
            className="ml-auto rounded-md p-1 text-[var(--color-sidebar-text-muted)] hover:text-white"
            aria-label="Fechar menu"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto py-3">
        <ul className="space-y-0.5 px-2">
          {items.map((item) => {
            const Icon = item.icon;
            if (!item.children) {
              const active = isActive(item.href!, pathname);
              return (
                <li key={item.label}>
                  <a
                    href={item.href}
                    onClick={closeMobileSidebar}
                    className={clsx(
                      'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                      active
                        ? 'bg-[var(--color-sidebar-bg-active)] text-white font-medium'
                        : 'text-[var(--color-sidebar-text)] hover:bg-[var(--color-sidebar-bg-active)] hover:text-white',
                    )}
                    title={compact ? item.label : undefined}
                  >
                    <Icon className="h-4.5 w-4.5 shrink-0" />
                    {!compact && <span className="truncate">{item.label}</span>}
                  </a>
                </li>
              );
            }

            const open = openGroups.has(item.label) && !compact;
            const groupActive = item.children.some((c) => isActive(c.href, pathname));

            return (
              <li key={item.label}>
                <button
                  type="button"
                  onClick={() => toggleGroup(item.label)}
                  className={clsx(
                    'flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                    groupActive
                      ? 'text-white font-medium'
                      : 'text-[var(--color-sidebar-text)] hover:bg-[var(--color-sidebar-bg-active)] hover:text-white',
                  )}
                  title={compact ? item.label : undefined}
                >
                  <Icon className="h-4.5 w-4.5 shrink-0" />
                  {!compact && (
                    <>
                      <span className="flex-1 truncate text-left">{item.label}</span>
                      <ChevronDown className={clsx('h-3.5 w-3.5 transition-transform', open && 'rotate-180')} />
                    </>
                  )}
                </button>
                {open && (
                  <ul className="mt-0.5 space-y-0.5 border-l border-[var(--color-sidebar-border)] pl-4 ml-4">
                    {item.children.map((child) => {
                      const active = isActive(child.href, pathname);
                      return (
                        <li key={child.href}>
                          <a
                            href={child.href}
                            onClick={closeMobileSidebar}
                            className={clsx(
                              'block rounded-md px-3 py-1.5 text-[13px] transition-colors',
                              active
                                ? 'text-white font-medium'
                                : 'text-[var(--color-sidebar-text-muted)] hover:text-white',
                            )}
                          >
                            {child.label}
                          </a>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      </nav>

      {!isMobile && (
        <button
          type="button"
          onClick={toggleSidebar}
          className="flex items-center justify-center gap-2 border-t border-[var(--color-sidebar-border)] px-3 py-3 text-[var(--color-sidebar-text-muted)] hover:text-white transition-colors"
        >
          {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
          {!collapsed && <span className="text-xs">Recolher menu</span>}
        </button>
      )}
    </aside>
  );
}
