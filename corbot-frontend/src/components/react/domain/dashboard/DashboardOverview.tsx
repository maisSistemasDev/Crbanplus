import { useStore } from '@nanostores/react';
import { $currentUser } from '../../../../lib/stores/auth';
import { ROLE_LABELS } from '../../../../lib/utils/roles';
import type { Role } from '../../../../lib/utils/roles';
import { FileSpreadsheet, Coins, CreditCard, Users } from 'lucide-react';

function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
      <div className="flex items-center gap-4">
        <div
          className="h-12 w-12 rounded-lg flex items-center justify-center shrink-0"
          style={{ backgroundColor: `${color}15`, color }}
        >
          {icon}
        </div>
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
}

export function DashboardOverview() {
  const user = useStore($currentUser);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          Bem-vindo, {user?.first_name}! ({ROLE_LABELS[(user?.role || 'vendedor') as Role]})
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={<FileSpreadsheet size={24} />}
          label="Propostas"
          value="--"
          color="var(--color-primary)"
        />
        <StatCard
          icon={<Coins size={24} />}
          label="Comissoes Pendentes"
          value="--"
          color="var(--color-warning)"
        />
        <StatCard
          icon={<CreditCard size={24} />}
          label="Pagamentos"
          value="--"
          color="var(--color-success)"
        />
        <StatCard
          icon={<Users size={24} />}
          label="Vendedores Ativos"
          value="--"
          color="var(--color-accent)"
        />
      </div>

      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Atividade Recente</h2>
        <p className="text-sm text-gray-500">Nenhuma atividade recente.</p>
      </div>
    </div>
  );
}
