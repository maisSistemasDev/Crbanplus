export interface InternalUser {
  id: number;
  cpf: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'admin' | 'colaborador';
  is_active: boolean;
  permissions?: UserPermission[];
  permission_count: number;
  certificado?: string;
  matricula?: string;
  created_at: string;
  updated_at: string;
}

export interface UserPermission {
  id: number;
  user: number;
  codename: string;
  name: string;
  category: PermissionCategory;
  description?: string;
  created_at: string;
}

export type PermissionCategory = 
  | 'corbans'
  | 'users'
  | 'proposals'
  | 'payments'
  | 'reports'
  | 'settings';

export interface AvailablePermission {
  codename: string;
  name: string;
  category: PermissionCategory;
}

export interface PermissionGroup {
  category: PermissionCategory;
  label: string;
  permissions: AvailablePermission[];
}

export interface PermissionTemplate {
  id: number;
  name: string;
  description?: string;
  permissions: string[]; // Array de codenames
  is_active: boolean;
  permission_count: number;
  created_at: string;
}

export interface InternalUserFormData {
  cpf: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'admin' | 'colaborador';
  password?: string;
  certificado?: string;
  matricula?: string;
  is_active: boolean;
}
