import { useStore } from '@nanostores/react';
import clsx from 'clsx';
import { FileText, LayoutDashboard, Percent, Settings, Wallet } from 'lucide-react';
import { $currentUser } from '../../../lib/stores/auth';
import type { Role } from '../../../lib/utils/roles';

const NAV = [
  { href: '/dashboard', label: 'Início', icon: LayoutDashboard },
  { href: '/proposals', label: 'Propostas', icon: FileText },
  { href: '/commission-tables', label: 'Comissões', icon: Percent },
  { href: '/payments', label: 'Financeiro', icon: Wallet, roles: ['empresa_admin', 'gerente'] as Role[] },
  { href: '/settings', label: 'Perfil', icon: Settings },
];

export function BottomNavBar() {
  const user = useStore($currentUser);
  const role = (user?.role as Role | undefined) ?? null;
  const currentPath = typeof window !== 'undefined' ? window.location.pathname : '/';
  const items = NAV.filter((item) => !item.roles || (role && item.roles.includes(role)));

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-[var(--color-border)] bg-[var(--color-card-bg)] md:hidden">
      <div
        className="flex items-stretch"
        style={{ height: 'var(--bottom-nav-height)', paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      >
        {items.map((item) => {
          const Icon = item.icon;
          const active =
            item.href === '/dashboard'
              ? currentPath === '/dashboard' || currentPath === '/'
              : currentPath === item.href || currentPath.startsWith(`${item.href}/`);
          return (
            <a
              key={item.href}
              href={item.href}
              className={clsx(
                'flex flex-1 flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors',
                active ? 'text-[var(--color-primary)]' : 'text-[var(--color-text-muted)]',
              )}
            >
              <Icon className="h-5 w-5" />
              <span>{item.label}</span>
            </a>
          );
        })}
      </div>
    </nav>
  );
}
