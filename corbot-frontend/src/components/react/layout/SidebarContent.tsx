import { useState, useEffect } from 'react';
import { useStore } from '@nanostores/react';
import { getPendingTourTargetIds } from '../../../lib/tour/driver';
import { $currentUser, clearAuth } from '../../../lib/stores/auth';
import { $sidebarCollapsed, toggleSidebar } from '../../../lib/stores/sidebar';
import { $theme } from '../../../lib/stores/theme';
import { $whitelabel } from '../../../lib/stores/whitelabel';
import { ROLE_LABELS, isPromotoraAdmin } from '../../../lib/utils/roles';
import type { Role } from '../../../lib/utils/roles';
import {
  Building2, Users, ChevronDown, ChevronRight, LogOut, Wallet, FileSpreadsheet, Settings, Briefcase, LayoutDashboard,
} from 'lucide-react';
import clsx from 'clsx';
import type { User } from '../../../lib/api/types';

interface MenuItem {
  icon: React.ReactNode;
  label: string;
  href: string;
  tourId?: string;
  children?: { label: string; href: string; tourId?: string }[];
}

function getMenuItems(user: User | null): MenuItem[] {
  const iconSize = 18;
  const role = (user?.role || 'vendedor') as Role;
  const promotoraAdmin = isPromotoraAdmin(role, user?.company ?? null);
  const isGerenteComercial = role === 'gerente_comercial';

  if (isGerenteComercial) {
    return [
      { icon: <LayoutDashboard size={iconSize} />, label: 'Dashboard', href: '/dashboard' },
      {
        icon: <FileSpreadsheet size={iconSize} />,
        label: 'Propostas',
        href: '/proposals',
        children: [{ label: 'Minhas Propostas', href: '/proposals' }],
      },
      {
        icon: <Users size={iconSize} />,
        label: 'Cadastro',
        href: '/cadastro',
        children: [{ label: 'Corbans', href: '/users' }],
      },
      {
        icon: <Wallet size={iconSize} />,
        label: 'Financeiro',
        href: '/financeiro',
        children: [
          { label: 'Comissões', href: '/commissions' },
          { label: 'Pagamentos', href: '/payments' },
        ],
      },
    ];
  }

  const items: MenuItem[] = [
    {
      icon: <Building2 size={iconSize} />,
      label: 'Administracao',
      href: '/administracao',
      children: [
        { label: 'Colaboradores', href: '/colaboradores' },
        { label: 'Bancos', href: '/banks' },
        { label: 'Convenios', href: '/agreements' },
        { label: 'Tabelas', href: '/tables' },
        { label: 'Equipes', href: '/commission-groups' },
      ],
    },
    {
      icon: <FileSpreadsheet size={iconSize} />,
      label: 'Propostas',
      href: '/proposals',
      children: [
        { label: 'Minhas Propostas', href: '/proposals' },
        { label: 'Lotes de Importacao', href: '/proposals/batches' },
        { label: 'Upload de Lote', href: '/proposals/batches/upload' },
        { label: 'Layouts CSV', href: '/proposals/layouts' },
        { label: 'Webhooks', href: '/proposals/webhooks' },
      ],
    },
    {
      icon: <Users size={iconSize} />,
      label: 'Cadastro',
      href: '/cadastro',
      children: [
        { label: 'Corbans', href: '/users' },
        { label: 'Acessos', href: '/bank-access' },
      ],
    },
    {
      icon: <Wallet size={iconSize} />,
      label: 'Financeiro',
      href: '/financeiro',
      children: [
        { label: 'Comissoes', href: '/commissions' },
        { label: 'Pagamentos', href: '/payments' },
        { label: 'Debitos', href: '/debitos' },
      ],
    },
  ];

  if (promotoraAdmin) {
    items.push({
      icon: <Briefcase size={iconSize} />,
      label: 'Comercial',
      href: '/commercial',
      children: [
        { label: 'Gerentes', href: '/commercial/managers' },
        { label: 'Equipes', href: '/commercial/teams' },
        { label: 'Produção', href: '/commercial/production' },
      ],
    });
  }

  items.push({
    icon: <Settings size={iconSize} />,
    label: 'Configurações',
    href: '/settings',
    children: [
      { label: 'Integrador', href: '/settings' },
      { label: 'Documentação', href: '/docs' },
    ],
  });

  return items;
}

function SidebarItem({
  item,
  collapsed,
  currentPath,
  tourTargetIds,
}: {
  item: MenuItem;
  collapsed: boolean;
  currentPath: string;
  tourTargetIds: Set<string>;
}) {
  const isActive =
    currentPath === item.href ||
    (item.children && item.href !== '/' && currentPath.startsWith(`${item.href}/`)) ||
    item.children?.some((c) => currentPath === c.href || currentPath.startsWith(`${c.href}/`));
  const childInTour = item.children?.some((c) => c.tourId && tourTargetIds.has(c.tourId)) ?? false;
  const [open, setOpen] = useState(isActive || childInTour);

  if (item.children && !collapsed) {
    return (
      <div>
        <button
          onClick={() => setOpen(!open)}
          data-tour={item.tourId}
          className={clsx(
            'w-full flex items-center gap-2.5 px-3 py-2 text-sm rounded-lg transition-colors',
            isActive
              ? 'bg-[var(--color-sidebar-active)] text-white'
              : 'text-[var(--color-sidebar-text)] hover:bg-[var(--color-sidebar-hover)]',
          )}
        >
          {item.icon}
          <span className="flex-1 text-left">{item.label}</span>
          {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </button>
        {open && (
          <div className="ml-8 mt-1 space-y-0.5">
            {item.children.map((child) => (
              <a
                key={child.href}
                href={child.href}
                data-tour={child.tourId}
                className={clsx(
                  'block px-2.5 py-1.5 text-xs rounded-lg transition-colors',
                  currentPath === child.href
                    ? 'bg-[var(--color-sidebar-active)] text-white'
                    : 'text-[var(--color-sidebar-text)] opacity-80 hover:opacity-100 hover:bg-[var(--color-sidebar-hover)]',
                )}
              >
                {child.label}
              </a>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <a
      href={item.href}
      title={collapsed ? item.label : undefined}
      data-tour={item.tourId}
      className={clsx(
        'flex items-center gap-2.5 px-3 py-2 text-sm rounded-lg transition-colors',
        collapsed && 'justify-center',
        isActive
          ? 'bg-[var(--color-sidebar-active)] text-white'
          : 'text-[var(--color-sidebar-text)] hover:bg-[var(--color-sidebar-hover)]',
      )}
    >
      {item.icon}
      {!collapsed && <span>{item.label}</span>}
    </a>
  );
}

export function SidebarContent() {
  const user = useStore($currentUser);
  const collapsed = useStore($sidebarCollapsed);
  const theme = useStore($theme);
  const config = useStore($whitelabel);
  const currentPath = typeof window !== 'undefined' ? window.location.pathname : '/';
  const menuItems = getMenuItems(user);
  const [tourTargetIds, setTourTargetIds] = useState(() => getPendingTourTargetIds());

  useEffect(() => {
    const refresh = () => setTourTargetIds(getPendingTourTargetIds());
    refresh();
    window.addEventListener('corbot-tour-updated', refresh);
    return () => window.removeEventListener('corbot-tour-updated', refresh);
  }, []);

  function handleLogout() {
    clearAuth();
    window.location.href = `${window.location.origin}/login`;
  }

  return (
    <aside
      className={clsx(
        'fixed top-0 left-0 h-full bg-[var(--color-sidebar-bg)] flex flex-col transition-all duration-250 z-40',
        collapsed ? 'w-[var(--sidebar-collapsed-width)]' : 'w-[var(--sidebar-width)]',
      )}
    >
      {/* Logo */}
      <div className={clsx(
        'flex items-center px-3 border-b border-white/10',
        'h-[var(--header-height)]',
        collapsed ? 'justify-center' : 'gap-3',
      )}>
        {(config.logoUrl || theme.logoUrl) ? (
          <img src={config.logoUrl || theme.logoUrl} alt="Logo" className="h-8 w-8 rounded object-contain" />
        ) : (
          <div className="h-8 w-8 rounded bg-[var(--color-primary)] flex items-center justify-center text-white font-bold text-sm">
            {config.systemName.charAt(0).toUpperCase()}
          </div>
        )}
        {!collapsed && <span className="text-white font-semibold text-sm">{config.systemName}</span>}
      </div>

      {/* Menu */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {menuItems.map((item) => (
          <SidebarItem
            key={item.href}
            item={item}
            collapsed={collapsed}
            currentPath={currentPath}
            tourTargetIds={tourTargetIds}
          />
        ))}
      </nav>

      {/* User / Logout */}
      <div className="p-3 border-t border-white/10">
        {!collapsed && user && (
          <div className="px-3 py-2 mb-2">
            <p className="text-white text-sm font-medium truncate">
              {user.first_name} {user.last_name}
            </p>
            <p className="text-white/60 text-xs">
              {ROLE_LABELS[user.role as Role]}
            </p>
          </div>
        )}
        <button
          onClick={handleLogout}
          title="Sair"
          className={clsx(
            'flex items-center gap-2.5 px-3 py-2 text-sm rounded-lg transition-colors w-full',
            'text-[var(--color-sidebar-text)] hover:bg-red-500/20 hover:text-red-300',
            collapsed && 'justify-center',
          )}
        >
          <LogOut size={20} />
          {!collapsed && <span>Sair</span>}
        </button>
      </div>
    </aside>
  );
}
