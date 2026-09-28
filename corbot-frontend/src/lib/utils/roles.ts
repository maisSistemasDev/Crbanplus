export type Role =
  | 'admin'
  | 'empresa_admin'
  | 'gerente'
  | 'gerente_comercial'
  | 'lider'
  | 'vendedor'
  | 'colaborador';

export const ROLE_LABELS: Record<Role, string> = {
  admin: 'Administrador',
  empresa_admin: 'Admin. Empresa',
  gerente: 'Gerente',
  gerente_comercial: 'Gerente Comercial',
  lider: 'Líder',
  vendedor: 'Vendedor',
  colaborador: 'Colaborador',
};

export const ROLE_COLORS: Record<Role, string> = {
  admin: 'bg-purple-100 text-purple-800',
  empresa_admin: 'bg-indigo-100 text-indigo-800',
  gerente: 'bg-blue-100 text-blue-800',
  gerente_comercial: 'bg-sky-100 text-sky-800',
  lider: 'bg-green-100 text-green-800',
  vendedor: 'bg-gray-100 text-gray-800',
  colaborador: 'bg-amber-100 text-amber-800',
};

export function canAccess(userRole: Role | null, requiredRoles: Role[]): boolean {
  if (!userRole) return false;
  return requiredRoles.includes(userRole);
}

export function isAdmin(role: Role | null): boolean {
  return role === 'admin';
}

export function isPromotoraAdmin(role: Role | null, company: string | null): boolean {
  return role === 'admin' && company === null;
}

export function isEmpresaAdmin(role: Role | null): boolean {
  return role === 'empresa_admin';
}

export function isGerenteComercial(role: Role | null): boolean {
  return role === 'gerente_comercial';
}

export function isLider(role: Role | null): boolean {
  return role === 'lider';
}

export function isVendedor(role: Role | null): boolean {
  return role === 'vendedor';
}
