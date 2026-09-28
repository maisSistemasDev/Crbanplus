import {
  LayoutDashboard,
  FileText,
  Wallet,
  Settings,
  Percent,
  type LucideIcon,
} from 'lucide-react';
import type { Role } from '../../../lib/utils/roles';

export interface NavChild {
  label: string;
  href: string;
  roles?: Role[];
}

export interface NavItem {
  label: string;
  icon: LucideIcon;
  href?: string;
  roles?: Role[];
  children?: NavChild[];
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' },
  { label: 'Propostas', icon: FileText, href: '/proposals' },
  { label: 'Comissões', icon: Percent, href: '/commission-tables' },
  {
    label: 'Financeiro',
    icon: Wallet,
    children: [
      { label: 'Pagamentos', href: '/payments', roles: ['empresa_admin', 'gerente'] },
      { label: 'Débitos', href: '/debits' },
    ],
  },
  {
    label: 'Configurações',
    icon: Settings,
    href: '/settings',
  },
];

export function filterNavForRole(items: NavItem[], role: Role | null): NavItem[] {
  if (role === 'empresa_admin') {
    return [
      { label: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' },
      { label: 'Propostas', icon: FileText, href: '/proposals' },
      { label: 'Comissões', icon: Percent, href: '/commission-tables' },
      {
        label: 'Financeiro',
        icon: Wallet,
        children: [
          { label: '2ª Via de Pagamento', href: '/payments' },
          { label: 'Débitos', href: '/debits' },
        ],
      },
      {
        label: 'Configurações',
        icon: Settings,
        href: '/settings',
      },
    ];
  }

  return items
    .filter((item) => !item.roles || (role && item.roles.includes(role)))
    .map((item) => ({
      ...item,
      children: item.children?.filter((child) => !child.roles || (role && child.roles.includes(role))),
    }))
    .filter((item) => !item.children || item.children.length > 0);
}
