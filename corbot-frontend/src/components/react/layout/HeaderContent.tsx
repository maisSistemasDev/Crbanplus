import { useState, useEffect } from 'react';
import { useStore } from '@nanostores/react';
import { $currentUser } from '../../../lib/stores/auth';
import { $sidebarCollapsed, toggleSidebar } from '../../../lib/stores/sidebar';
import { ROLE_LABELS, ROLE_COLORS } from '../../../lib/utils/roles';
import type { Role } from '../../../lib/utils/roles';
import { api } from '../../../lib/api/client';
import { ENDPOINTS } from '../../../lib/api/endpoints';
import { Menu, PanelLeftClose, Wallet } from 'lucide-react';

function formatCurrency(value: number): string {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export function HeaderContent() {
  const user = useStore($currentUser);
  const collapsed = useStore($sidebarCollapsed);
  const [balance, setBalance] = useState<{ available: number; pending: number } | null>(null);

  useEffect(() => {
    if (!user) return;
    api.get<{ available: number; pending: number }>(ENDPOINTS.COMMISSION_BALANCE)
      .then(setBalance)
      .catch(() => {});
  }, [user]);

  return (
    <header
      className="bg-white border-b border-[var(--color-header-border)] flex items-center justify-between px-3 shrink-0"
      style={{ height: 'var(--header-height)' }}
    >
      <div className="flex items-center gap-3">
        <button
          onClick={toggleSidebar}
          className="hidden md:flex p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-500"
          title={collapsed ? 'Expandir menu' : 'Recolher menu'}
          aria-label={collapsed ? 'Expandir menu' : 'Recolher menu'}
        >
          {collapsed ? <Menu size={20} /> : <PanelLeftClose size={20} />}
        </button>
      </div>

      <div className="flex items-center gap-4">
        {balance !== null && (
          <div className="flex items-center gap-2 bg-green-50 text-green-700 px-3 py-1.5 rounded-lg" title="Comissao disponivel para saque">
            <Wallet size={16} />
            <span className="text-sm font-semibold">{formatCurrency(balance.available)}</span>
          </div>
        )}
        {user && (
          <>
            <span
              className={`text-xs font-medium px-2 py-1 rounded-full ${ROLE_COLORS[user.role as Role] || 'bg-gray-100 text-gray-800'}`}
            >
              {ROLE_LABELS[user.role as Role] || user.role}
            </span>
            <span className="text-sm text-gray-700 font-medium">
              {user.first_name} {user.last_name}
            </span>
          </>
        )}
      </div>
    </header>
  );
}
