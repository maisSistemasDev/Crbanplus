import { useState } from 'react';
import { useStore } from '@nanostores/react';
import { $currentUser, clearAuth } from '../../../lib/stores/auth';
import { $sidebarCollapsed, toggleSidebar } from '../../../lib/stores/sidebar';
import { $theme } from '../../../lib/stores/theme';
import { $whitelabel } from '../../../lib/stores/whitelabel';
import { ROLE_LABELS } from '../../../lib/utils/roles';
import type { Role } from '../../../lib/utils/roles';
import {
  LayoutDashboard, Building2, Users, Landmark, FileSpreadsheet,
  Coins, UsersRound, KeyRound, ChevronDown, ChevronRight,
  CreditCard, LogOut, Wallet, Code2, BookOpen, Settings,
} from 'lucide-react';
import clsx from 'clsx';

interface MenuItem {
  icon: React.ReactNode;
  label: string;
  href: string;
  tourId?: string;
  children?: { label: string; href: string; tourId?: string }[];
}

function getMenuItems(role: Role): MenuItem[] {
  const iconSize = 20;

  const admin: MenuItem[] = [
    { icon: <LayoutDashboard size={iconSize} />, label: 'Dashboard', href: '/dashboard' },
    { icon: <Building2 size={iconSize} />, label: 'Corbans', href: '/companies' },
    {
      icon: <Users size={iconSize} />,
      label: 'Usuarios',
      href: '/users',
      tourId: 'sidebar-users',
      children: [
        { label: 'Todos', href: '/users' },
        { label: 'Vendedores', href: '/users/sellers' },
        { label: 'Lideres', href: '/users/leaders' },
        { label: 'Gerentes', href: '/users/managers' },
        { label: 'Corbans', href: '/users/corbans' },
        { label: 'Criar', href: '/users/create', tourId: 'create-user-link' },
        { label: 'Importar CSV', href: '/users/import', tourId: 'import-csv-link' },
      ],
    },
    {
      icon: <Landmark size={iconSize} />,
      label: 'Bancos',
      href: '/banks',
      tourId: 'sidebar-banks',
      children: [
        { label: 'Bancos', href: '/banks' },
        { label: 'Convenios', href: '/agreements' },
        { label: 'Tabelas', href: '/tables', tourId: 'tables-link' },
      ],
    },
    {
      icon: <FileSpreadsheet size={iconSize} />,
      label: 'Propostas',
      href: '/proposals',
      children: [
        { label: 'Listagem', href: '/proposals' },
        { label: 'Lotes', href: '/proposals/batches' },
        { label: 'Upload', href: '/proposals/batches/upload' },
        { label: 'Layouts', href: '/proposals/layouts' },
      ],
    },
    {
      icon: <Coins size={iconSize} />,
      label: 'Comissoes',
      href: '/commissions',
      children: [
        { label: 'Listagem', href: '/commissions' },
        { label: 'Espelho', href: '/commissions/mirror' },
        { label: 'Gerar', href: '/commissions/generate' },
      ],
    },
    {
      icon: <UsersRound size={iconSize} />,
      label: 'Equipes',
      href: '/commission-groups',
      tourId: 'sidebar-commission-groups',
      children: [
        { label: 'Grupos', href: '/commission-groups' },
        { label: 'Por Empresa', href: '/commission-groups/by-company' },
      ],
    },
    { icon: <CreditCard size={iconSize} />, label: 'Pagamentos', href: '/payments' },
    { icon: <KeyRound size={iconSize} />, label: 'Acessos', href: '/bank-access' },
    { icon: <Settings size={iconSize} />, label: 'Configuracoes', href: '/settings' },
    { icon: <Code2 size={iconSize} />, label: 'Desenvolvedor', href: '/developer' },
    { icon: <BookOpen size={iconSize} />, label: 'Documentacao', href: '/docs' },
  ];

  const empresa_admin: MenuItem[] = [
    { icon: <LayoutDashboard size={iconSize} />, label: 'Dashboard', href: '/dashboard' },
    { icon: <Building2 size={iconSize} />, label: 'Minha Empresa', href: '/companies' },
    {
      icon: <Users size={iconSize} />,
      label: 'Usuarios',
      href: '/users',
      children: [
        { label: 'Todos', href: '/users' },
        { label: 'Vendedores', href: '/users/sellers' },
        { label: 'Lideres', href: '/users/leaders' },
        { label: 'Gerentes', href: '/users/managers' },
        { label: 'Corbans', href: '/users/corbans' },
        { label: 'Criar', href: '/users/create' },
        { label: 'Importar CSV', href: '/users/import' },
      ],
    },
    { icon: <Coins size={iconSize} />, label: 'Comissoes', href: '/commissions' },
    {
      icon: <Wallet size={iconSize} />,
      label: 'Saques',
      href: '/withdrawals/corbanpay',
      children: [
        { label: 'Saque CorbanPay', href: '/withdrawals/corbanpay' },
      ],
    },
    { icon: <UsersRound size={iconSize} />, label: 'Equipes', href: '/commission-groups', tourId: 'sidebar-commission-groups' },
    { icon: <CreditCard size={iconSize} />, label: 'Pagamentos', href: '/payments' },
    { icon: <Settings size={iconSize} />, label: 'Configuracoes', href: '/settings' },
  ];

  const gerente: MenuItem[] = [
    { icon: <LayoutDashboard size={iconSize} />, label: 'Dashboard', href: '/dashboard' },
    {
      icon: <Users size={iconSize} />,
      label: 'Usuarios',
      href: '/users',
      tourId: 'sidebar-users',
      children: [
        { label: 'Vendedores', href: '/users/sellers' },
        { label: 'Lideres', href: '/users/leaders' },
        { label: 'Importar CSV', href: '/users/import', tourId: 'import-csv-link' },
      ],
    },
    { icon: <Coins size={iconSize} />, label: 'Comissoes', href: '/commissions' },
    {
      icon: <Wallet size={iconSize} />,
      label: 'Saques',
      href: '/withdrawals/corbanpay',
      children: [
        { label: 'Saque CorbanPay', href: '/withdrawals/corbanpay' },
      ],
    },
    { icon: <UsersRound size={iconSize} />, label: 'Equipes', href: '/commission-groups' },
    { icon: <CreditCard size={iconSize} />, label: 'Pagamentos', href: '/payments' },
    { icon: <Settings size={iconSize} />, label: 'Configuracoes', href: '/settings' },
  ];

  const lider: MenuItem[] = [
    { icon: <LayoutDashboard size={iconSize} />, label: 'Dashboard', href: '/dashboard' },
    { icon: <Users size={iconSize} />, label: 'Minha Equipe', href: '/users/sellers' },
    { icon: <Coins size={iconSize} />, label: 'Comissoes', href: '/commissions' },
    {
      icon: <Wallet size={iconSize} />,
      label: 'Saques',
      href: '/withdrawals/corbanpay',
      children: [
        { label: 'Saque CorbanPay', href: '/withdrawals/corbanpay' },
      ],
    },
    { icon: <UsersRound size={iconSize} />, label: 'Equipes', href: '/commission-groups' },
    { icon: <Settings size={iconSize} />, label: 'Configuracoes', href: '/settings' },
  ];

  const vendedor: MenuItem[] = [
    { icon: <LayoutDashboard size={iconSize} />, label: 'Dashboard', href: '/dashboard' },
    { icon: <Coins size={iconSize} />, label: 'Minhas Comissoes', href: '/commissions' },
    {
      icon: <Wallet size={iconSize} />,
      label: 'Saques',
      href: '/withdrawals/corbanpay',
      children: [
        { label: 'Saque CorbanPay', href: '/withdrawals/corbanpay' },
      ],
    },
    { icon: <Settings size={iconSize} />, label: 'Configuracoes', href: '/settings' },
  ];

  const menus: Record<Role, MenuItem[]> = { admin, empresa_admin, gerente, lider, vendedor };
  return menus[role] || vendedor;
}

function SidebarItem({
  item,
  collapsed,
  currentPath,
}: {
  item: MenuItem;
  collapsed: boolean;
  currentPath: string;
}) {
  const isActive = currentPath === item.href || item.children?.some((c) => currentPath === c.href);
  const [open, setOpen] = useState(isActive);

  if (item.children && !collapsed) {
    return (
      <div>
        <button
          onClick={() => setOpen(!open)}
          data-tour={item.tourId}
          className={clsx(
            'w-full flex items-center gap-3 px-4 py-2.5 text-sm rounded-lg transition-colors',
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
                  'block px-3 py-2 text-sm rounded-lg transition-colors',
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
      className={clsx(
        'flex items-center gap-3 px-4 py-2.5 text-sm rounded-lg transition-colors',
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
  const menuItems = getMenuItems((user?.role || 'vendedor') as Role);

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
        'flex items-center h-14 px-4 border-b border-white/10',
        collapsed ? 'justify-center' : 'gap-3',
      )}>
        {(config.logoUrl || theme.logoUrl) ? (
          <img src={config.logoUrl || theme.logoUrl} alt="Logo" className="h-8 w-8 rounded object-contain" />
        ) : (
          <div className="h-8 w-8 rounded bg-[var(--color-primary)] flex items-center justify-center text-white font-bold text-sm">
            {config.systemName.charAt(0).toUpperCase()}
          </div>
        )}
        {!collapsed && <span className="text-white font-semibold text-lg">{config.systemName}</span>}
      </div>

      {/* Menu */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {menuItems.map((item) => (
          <SidebarItem
            key={item.href}
            item={item}
            collapsed={collapsed}
            currentPath={currentPath}
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
            'flex items-center gap-3 px-4 py-2.5 text-sm rounded-lg transition-colors w-full',
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
