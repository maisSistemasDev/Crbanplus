import { useStore } from '@nanostores/react';
import { $currentUser } from '../../../../lib/stores/auth';
import { ROLE_LABELS } from '../../../../lib/utils/roles';
import type { Role } from '../../../../lib/utils/roles';
import {
  FileSpreadsheet, Coins, UsersRound, Upload, Settings, Landmark, Users,
} from 'lucide-react';
import { CommercialProductionPage } from '../commercial/CommercialProductionPage';
import { PageHeader } from '../../ui/PageHeader';

const SHORTCUTS = [
  { href: '/proposals/batches/upload', label: 'Upload de lote', icon: Upload, roles: ['admin', 'empresa_admin', 'gerente', 'lider'] as Role[] },
  { href: '/commissions', label: 'Comissões', icon: Coins, roles: ['admin', 'empresa_admin', 'gerente', 'lider', 'vendedor'] as Role[] },
  { href: '/commission-groups', label: 'Equipes', icon: UsersRound, roles: ['admin', 'empresa_admin', 'gerente'] as Role[] },
  { href: '/users/import', label: 'Importar CSV', icon: Users, roles: ['admin', 'empresa_admin'] as Role[] },
  { href: '/tables', label: 'Tabelas bancárias', icon: Landmark, roles: ['admin', 'empresa_admin', 'gerente'] as Role[] },
  { href: '/proposals', label: 'Propostas', icon: FileSpreadsheet, roles: ['admin', 'empresa_admin', 'gerente', 'lider', 'vendedor'] as Role[] },
  { href: '/settings', label: 'Configurações', icon: Settings, roles: ['admin', 'empresa_admin'] as Role[] },
];

function ShortcutCard({
  href,
  label,
  icon: Icon,
}: {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}) {
  return (
    <a
      href={href}
      className="card flex items-center gap-3 hover:border-[var(--color-primary)]/40 hover:shadow-md transition-all group"
    >
      <div
        className="h-9 w-9 rounded-lg flex items-center justify-center shrink-0"
        style={{ backgroundColor: 'color-mix(in srgb, var(--color-primary) 12%, white)', color: 'var(--color-primary)' }}
      >
        <Icon size={18} />
      </div>
      <span className="text-sm font-medium text-gray-800 group-hover:text-[var(--color-primary)]">
        {label}
      </span>
    </a>
  );
}

export function DashboardOverview() {
  const user = useStore($currentUser);
  const role = (user?.role || 'vendedor') as Role;

  if (role === 'gerente_comercial') {
    return <CommercialProductionPage />;
  }

  const shortcuts = SHORTCUTS.filter((s) => s.roles.includes(role));

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle={`Bem-vindo, ${user?.first_name}! (${ROLE_LABELS[role]})`}
      />

      <div className="mb-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">Acesso rápido</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {shortcuts.map((s) => (
            <ShortcutCard key={s.href} href={s.href} label={s.label} icon={s.icon} />
          ))}
        </div>
      </div>

      <div className="card">
        <h2 className="text-sm font-semibold text-gray-900 mb-1">Indicadores</h2>
        <p className="text-xs text-gray-500">
          Resumo numérico em breve. Use os atalhos acima para as tarefas do dia a dia.
        </p>
      </div>
    </div>
  );
}
