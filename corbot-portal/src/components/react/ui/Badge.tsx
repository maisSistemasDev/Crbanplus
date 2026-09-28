import clsx from 'clsx';

const STATUS_STYLES: Record<string, string> = {
  pago: 'bg-emerald-100 text-emerald-700',
  paga: 'bg-emerald-100 text-emerald-700',
  paid: 'bg-emerald-100 text-emerald-700',
  pago_parcial: 'bg-emerald-50 text-emerald-700',
  liberado: 'bg-emerald-100 text-emerald-700',
  saque_liberado: 'bg-emerald-100 text-emerald-700',
  withdraw_available: 'bg-emerald-100 text-emerald-700',
  ativo: 'bg-emerald-100 text-emerald-700',
  ativa: 'bg-emerald-100 text-emerald-700',
  aprovado: 'bg-emerald-100 text-emerald-700',
  concluido: 'bg-emerald-100 text-emerald-700',
  aguardando: 'bg-amber-100 text-amber-700',
  aguardando_pagamento: 'bg-amber-100 text-amber-700',
  pending_manual_payment: 'bg-amber-100 text-amber-700',
  pendente: 'bg-amber-100 text-amber-700',
  pending: 'bg-amber-100 text-amber-700',
  not_released: 'bg-amber-100 text-amber-700',
  nao_liberado: 'bg-amber-100 text-amber-700',
  processando: 'bg-amber-100 text-amber-700',
  processed: 'bg-emerald-100 text-emerald-700',
  processada: 'bg-emerald-100 text-emerald-700',
  em_analise: 'bg-amber-100 text-amber-700',
  sinistro: 'bg-red-100 text-red-700',
  cancelado: 'bg-red-100 text-red-700',
  cancelada: 'bg-red-100 text-red-700',
  recusado: 'bg-red-100 text-red-700',
  reprovado: 'bg-red-100 text-red-700',
  falhou: 'bg-red-100 text-red-700',
  parcial: 'bg-amber-100 text-amber-700',
  inativo: 'bg-gray-100 text-gray-600',
  inativa: 'bg-gray-100 text-gray-600',
  expirado: 'bg-gray-100 text-gray-600',
  revogado: 'bg-gray-100 text-gray-600',
};

const ROLE_STYLES: Record<string, string> = {
  admin: 'bg-purple-100 text-purple-700',
  empresa_admin: 'bg-indigo-100 text-indigo-700',
  gerente: 'bg-blue-100 text-blue-700',
  lider: 'bg-teal-100 text-teal-700',
  vendedor: 'bg-gray-100 text-gray-700',
};

function normalize(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, '_');
}

interface StatusBadgeProps {
  status: string;
  label?: string;
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pendente',
  not_released: 'Pendente',
  nao_liberado: 'Pendente',
  processed: 'Processada',
  processada: 'Processada',
  paid: 'Pago',
  pago: 'Pago',
  withdraw_available: 'Saque liberado',
  saque_liberado: 'Saque liberado',
  pending_manual_payment: 'Aguardando pagamento',
  aguardando_pagamento: 'Aguardando pagamento',
  sinistro: 'Sinistro',
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const key = normalize(status);
  const style = STATUS_STYLES[key] ?? 'bg-gray-100 text-gray-600';
  return <span className={clsx('status-pill', style)}>{label ?? STATUS_LABELS[key] ?? status}</span>;
}

interface RoleBadgeProps {
  role: string;
  label: string;
}

export function RoleBadge({ role, label }: RoleBadgeProps) {
  const style = ROLE_STYLES[role] ?? 'bg-gray-100 text-gray-600';
  return <span className={clsx('status-pill', style)}>{label}</span>;
}

export function Badge({ children, tone = 'gray' }: { children: React.ReactNode; tone?: 'gray' | 'primary' | 'success' | 'warning' | 'error' }) {
  const tones: Record<string, string> = {
    gray: 'bg-gray-100 text-gray-600',
    primary: 'bg-[var(--color-primary-bg)] text-[var(--color-primary-dark)]',
    success: 'bg-emerald-100 text-emerald-700',
    warning: 'bg-amber-100 text-amber-700',
    error: 'bg-red-100 text-red-700',
  };
  return <span className={clsx('status-pill', tones[tone])}>{children}</span>;
}
