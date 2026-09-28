export interface CommercialManager {
  id: number;
  cpf: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  inactivated_at?: string | null;
  inactivation_reason?: string | null;
  team_size: number;
}

export interface TeamMember {
  id: number;
  manager: number;
  manager_name: string;
  company: string;
  company_name: string;
  added_by_name: string | null;
  created_at: string;
}

export interface ProductionByCompany {
  company_id: string;
  company_name: string;
  total_amount: string;
  total_count: number;
}

export interface ProductionByBank {
  bank_id: string;
  bank_name: string;
  total_amount: string;
  total_count: number;
}

export interface ProductionByPeriod {
  period: string | null;
  amount: string;
  count: number;
}

export interface ProductivityBlock {
  amount: string;
  count: number;
  label?: string;
}

export interface DashboardData {
  manager: { id: number; name: string; team_size: number };
  date_from: string;
  date_to: string;
  productivity_month: ProductivityBlock;
  productivity_week: ProductivityBlock;
  productivity_period: ProductivityBlock;
  top_10: ProductionByCompany[];
  top_bank: ProductionByBank | null;
  production_by_bank: ProductionByBank[];
  total_production: string;
  total_proposals: number;
  production_by_period: ProductionByPeriod[];
  production_by_company: ProductionByCompany[];
  ranking_overall: ProductionByCompany[];
  ranking_by_period: ProductionByCompany[] | null;
  period: string | null;
}

export function formatCurrency(value: string) {
  const n = Number(value);
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export function managerLabel(m: Pick<CommercialManager, 'first_name' | 'last_name' | 'cpf'>) {
  const name = `${m.first_name || ''} ${m.last_name || ''}`.trim();
  return name || m.cpf;
}

/** Primeiro nome + sobrenome abreviado (ex.: "Maria S."). */
export function shortManagerName(m: Pick<CommercialManager, 'first_name' | 'last_name' | 'cpf'>) {
  const first = (m.first_name || '').trim();
  const last = (m.last_name || '').trim();
  if (first && last) {
    return `${first} ${last.charAt(0).toUpperCase()}.`;
  }
  if (first) return first;
  if (last) return last;
  return m.cpf || 'Sem nome';
}
