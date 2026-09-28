import { useStore } from '@nanostores/react';
import { $currentUser } from '../../../lib/stores/auth';
import { $whitelabel } from '../../../lib/stores/whitelabel';
import type { Role } from '../../../lib/utils/roles';
import {
  Users, Landmark, FileSpreadsheet, Coins, UsersRound, KeyRound, CreditCard, Receipt,
} from 'lucide-react';
import clsx from 'clsx';

interface AppItem {
  icon: React.ReactNode;
  label: string;
  href: string;
  color: string;
}

function getAppItems(role: Role): AppItem[] {
  const all: Record<string, AppItem> = {
    colaboradores:{ icon: <Users size={28} />,           label: 'Colaboradores', href: '/colaboradores',      color: '#1f6feb' },
    bancos:       { icon: <Landmark size={28} />,        label: 'Bancos',        href: '/banks',              color: '#0f766e' },
    convenios:    { icon: <Landmark size={28} />,        label: 'Convenios',     href: '/agreements',         color: '#0ea5e9' },
    tabelas:      { icon: <FileSpreadsheet size={28} />, label: 'Tabelas',       href: '/tables',             color: '#4f46e5' },
    equipes:      { icon: <UsersRound size={28} />,      label: 'Equipes',       href: '/commission-groups',  color: '#0891b2' },
    propostas:    { icon: <FileSpreadsheet size={28} />, label: 'Propostas',     href: '/proposals',          color: '#16a34a' },
    corbans:      { icon: <Users size={28} />,           label: 'Corbans',       href: '/users',              color: '#2563eb' },
    acessos:      { icon: <KeyRound size={28} />,        label: 'Acessos',       href: '/bank-access',        color: '#334155' },
    comissoes:    { icon: <Coins size={28} />,           label: 'Comissoes',     href: '/commissions',        color: '#f59e0b' },
    pagamentos:   { icon: <CreditCard size={28} />,      label: 'Pagamentos',    href: '/payments',           color: '#dc2626' },
    debitos:      { icon: <Receipt size={28} />,         label: 'Debitos',       href: '/debitos',            color: '#7c3aed' },
  };

  const simplifiedItems: AppItem[] = [
    all.colaboradores,
    all.bancos,
    all.convenios,
    all.tabelas,
    all.equipes,
    all.propostas,
    all.corbans,
    all.acessos,
    all.comissoes,
    all.pagamentos,
    all.debitos,
  ];

  const byRole: Record<Role, AppItem[]> = {
    admin: simplifiedItems,
    empresa_admin: simplifiedItems,
    gerente: simplifiedItems,
    gerente_comercial: [all.propostas, all.corbans, all.comissoes, all.pagamentos],
    lider: simplifiedItems,
    vendedor: simplifiedItems,
    colaborador: simplifiedItems,
  };

  return byRole[role] || byRole.vendedor;
}

export function MobileHome() {
  const user = useStore($currentUser);
  const config = useStore($whitelabel);
  const role = (user?.role || 'vendedor') as Role;
  const apps = getAppItems(role);
  const currentPath = typeof window !== 'undefined' ? window.location.pathname : '/';

  return (
    <div className="flex flex-col min-h-screen bg-[var(--color-body-bg)] pb-20">
      {/* Header */}
      <header className="bg-[var(--color-secondary)] text-white px-4 pt-10 pb-6 safe-area-top">
        <div className="flex items-center gap-3 mb-1">
          {(config.logoUrl) ? (
            <img src={config.logoUrl} alt="Logo" className="h-9 w-9 rounded-xl object-contain" />
          ) : (
            <div className="h-9 w-9 rounded-xl bg-[var(--color-primary)] flex items-center justify-center font-bold text-base">
              {config.systemName.charAt(0).toUpperCase()}
            </div>
          )}
          <div>
            <p className="text-xs text-white/60">Bem-vindo,</p>
            <p className="font-semibold text-sm leading-tight">{user?.first_name || 'Usuário'}</p>
          </div>
        </div>
        <p className="text-lg font-bold mt-2">{config.systemName}</p>
      </header>

      {/* App Grid */}
      <main className="flex-1 px-4 py-5">
        <div className="grid grid-cols-4 gap-3">
          {apps.map((app) => {
            const isActive = currentPath === app.href;
            return (
              <a
                key={app.href}
                href={app.href}
                className={clsx(
                  'flex flex-col items-center gap-1.5 group',
                )}
              >
                <div
                  className={clsx(
                    'w-full aspect-square rounded-2xl flex items-center justify-center shadow-sm transition-transform active:scale-95',
                    isActive && 'ring-2 ring-offset-2 ring-[var(--color-primary)]',
                  )}
                  style={{ backgroundColor: app.color }}
                >
                  <span className="text-white">{app.icon}</span>
                </div>
                <span className="text-[10px] text-center leading-tight text-[var(--color-text)] font-medium line-clamp-2">
                  {app.label}
                </span>
              </a>
            );
          })}
        </div>
      </main>
    </div>
  );
}
