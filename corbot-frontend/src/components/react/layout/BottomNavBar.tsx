import { useStore } from '@nanostores/react';
import { $currentUser } from '../../../lib/stores/auth';
import { LayoutDashboard, Coins, Wallet, Settings } from 'lucide-react';
import clsx from 'clsx';

interface NavItem {
  icon: React.ReactNode;
  label: string;
  href: string;
}

const BASE_NAV: NavItem[] = [
  { icon: <LayoutDashboard size={22} />, label: 'Início',    href: '/dashboard' },
  { icon: <Coins size={22} />,           label: 'Comissões', href: '/commissions' },
  { icon: <Wallet size={22} />,          label: 'Saques',    href: '/withdrawals/corbanpay' },
  { icon: <Settings size={22} />,        label: 'Config',    href: '/settings' },
];

export function BottomNavBar() {
  const currentPath = typeof window !== 'undefined' ? window.location.pathname : '/';

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-[var(--color-card-bg)] border-t border-[var(--color-border)] safe-area-bottom md:hidden">
      <div className="flex items-stretch h-16">
        {BASE_NAV.map((item) => {
          const isActive = currentPath === item.href || currentPath.startsWith(item.href + '/');
          return (
            <a
              key={item.href}
              href={item.href}
              className={clsx(
                'flex-1 flex flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors',
                isActive
                  ? 'text-[var(--color-primary)]'
                  : 'text-[var(--color-text-muted)]',
              )}
            >
              {item.icon}
              <span>{item.label}</span>
            </a>
          );
        })}
      </div>
    </nav>
  );
}
