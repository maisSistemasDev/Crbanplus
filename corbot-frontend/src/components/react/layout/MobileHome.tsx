import { useStore } from '@nanostores/react';
import { $currentUser } from '../../../lib/stores/auth';
import { $whitelabel } from '../../../lib/stores/whitelabel';
import type { Role } from '../../../lib/utils/roles';
import {
  LayoutDashboard, Building2, Users, Landmark, FileSpreadsheet,
  Coins, UsersRound, KeyRound, CreditCard, Wallet, Code2,
  BookOpen, Settings,
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
    dashboard:    { icon: <LayoutDashboard size={28} />, label: 'Dashboard',         href: '/dashboard',                 color: '#3498db' },
    corbans:      { icon: <Building2 size={28} />,       label: 'Corbans',           href: '/companies',                 color: '#8e44ad' },
    empresa:      { icon: <Building2 size={28} />,       label: 'Minha Empresa',     href: '/companies',                 color: '#8e44ad' },
    usuarios:     { icon: <Users size={28} />,           label: 'Usuários',          href: '/users',                     color: '#2980b9' },
    equipe:       { icon: <Users size={28} />,           label: 'Minha Equipe',      href: '/users/sellers',             color: '#2980b9' },
    bancos:       { icon: <Landmark size={28} />,        label: 'Bancos',            href: '/banks',                     color: '#16a085' },
    propostas:    { icon: <FileSpreadsheet size={28} />, label: 'Propostas',         href: '/proposals',                 color: '#27ae60' },
    lotes:        { icon: <FileSpreadsheet size={28} />, label: 'Lotes',             href: '/proposals/batches',         color: '#2ecc71' },
    comissoes:    { icon: <Coins size={28} />,           label: 'Comissões',         href: '/commissions',               color: '#f39c12' },
    espelho:      { icon: <Coins size={28} />,           label: 'Espelho',           href: '/commissions/mirror',        color: '#e67e22' },
    gerarComis:   { icon: <Coins size={28} />,           label: 'Gerar Comissões',   href: '/commissions/generate',      color: '#d35400' },
    equipesGrupo: { icon: <UsersRound size={28} />,      label: 'Equipes',           href: '/commission-groups',         color: '#1abc9c' },
    pagamentos:   { icon: <CreditCard size={28} />,      label: 'Pagamentos',        href: '/payments',                  color: '#c0392b' },
    saques:       { icon: <Wallet size={28} />,          label: 'Saques',            href: '/withdrawals/corbanpay',     color: '#2471a3' },
    acessos:      { icon: <KeyRound size={28} />,        label: 'Acessos',           href: '/bank-access',               color: '#7f8c8d' },
    configuracoes:{ icon: <Settings size={28} />,        label: 'Configurações',     href: '/settings',                  color: '#95a5a6' },
    dev:          { icon: <Code2 size={28} />,           label: 'Desenvolvedor',     href: '/developer',                 color: '#34495e' },
    docs:         { icon: <BookOpen size={28} />,        label: 'Documentação',      href: '/docs',                      color: '#5d6d7e' },
  };

  const byRole: Record<Role, AppItem[]> = {
    admin: [
      all.dashboard, all.corbans, all.usuarios, all.bancos, all.propostas,
      all.lotes, all.comissoes, all.espelho, all.gerarComis, all.equipesGrupo,
      all.pagamentos, all.acessos, all.configuracoes, all.dev, all.docs,
    ],
    empresa_admin: [
      all.dashboard, all.empresa, all.usuarios, all.comissoes, all.saques,
      all.equipesGrupo, all.pagamentos, all.configuracoes,
    ],
    gerente: [
      all.dashboard, all.usuarios, all.comissoes, all.saques,
      all.equipesGrupo, all.pagamentos, all.configuracoes,
    ],
    lider: [
      all.dashboard, all.equipe, all.comissoes, all.saques,
      all.equipesGrupo, all.configuracoes,
    ],
    vendedor: [
      all.dashboard, all.comissoes, all.saques, all.configuracoes,
    ],
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
