// API response types matching Django REST Framework serializers

// ===== Auth =====
export interface TokenResponse {
  access: string;
  refresh: string;
}

// ===== Core =====
export interface User {
  id: number;
  cpf: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'admin' | 'empresa_admin' | 'gerente' | 'lider' | 'vendedor';
  leader: number | null;
  company: string | null;
  company_name: string | null;
  is_active: boolean;
  is_gerente: boolean;
  is_lider: boolean;
  is_vendedor: boolean;
  is_empresa_admin: boolean;
  certificado?: string | null;
  matricula?: string | null;
  extra_data: ExtraData | null;
  leader_name?: string;
}

export interface ExtraData {
  user: number;
  rg: string | null;
  rg_emission_date: string | null;
  rg_emission_organ: string | null;
  birth_date: string | null;
  phone: string | null;
  pix_key: string | null;
  pix_type: 'CHAVE_ALEATORIA' | 'EMAIL' | 'CELULAR' | 'CPF' | 'CNPJ' | null;
}

export interface Company {
  id: string;
  name: string;
  trading_name: string | null;
  cnpj: string;
  logo: string | null;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  settings: Record<string, unknown>;
  email: string | null;
  phone: string | null;
  website: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  zip_code: string | null;
  is_active: boolean;
}

// ===== Banks =====
export interface Bank {
  id: string;
  name: string;
  logo: string | null;
  website: string | null;
  is_active: boolean;
}

export interface Agreement {
  id: string;
  name: string;
  code: string;
  description: string;
  is_active: boolean;
  alias?: string[];
}

export interface Table {
  id: string;
  bank: string;
  bank_name: string;
  agreement: string;
  agreement_name: string;
  name_in_bank: string;
  description: string;
  min_value: string;
  max_value: string;
  commission_rate: string;
  vigency_date: string;
  alias: string[];
  is_active: boolean;
}

// ===== Proposals =====
export interface FileColumn {
  column_name: string;
  column_index: number;
  detected_type: string;
  sample_data: string | null;
}

export interface ModelField {
  name: string;
  verbose_name: string;
  type: string;
  required: boolean;
}

export interface PreviewRowsResponse {
  columns_order: FileColumn[];
  model_fields: ModelField[];
}

export interface ColumnMapping {
  [dbFieldName: string]: {
    index: number;
    name: string;
    data_type: string;
  };
}

export interface LayoutField {
  id: string;
  name: string;
  index: number;
  header_name: string;
}

export interface Layout {
  id: string;
  name: string;
  bank: string;
  bank_name: string;
  map_fields: LayoutField[];
  created_at: string;
  updated_at: string;
}

export interface ProposalBatch {
  id: string;
  file: string;
  layout: string;
  status: string;
  processed_at: string | null;
  error_message: string | null;
  processed_rows: number;
  errored_rows: number;
  total_rows: number;
  task_id: string | null;
  log_url: string | null;
  original_file_url: string | null;
  bank_name: string;
  bank_id: string | null;
  layout_name: string;
  name: string;
  commissions_to_generate?: number;
  created_at: string;
  updated_at: string;
}

export interface Proposal {
  id: string;
  seller: number;
  contract_number: string;
  company: string;
  bank: string;
  agreement: string;
  table: string;
  status: string;
  disbursement_date: string;
  amount: string;
  client_document: string;
  client_name: string;
  original_data: Record<string, unknown>;
  batch: string | null;
  release_date: string | null;
  hash: string | null;
  commissions?: CommissionSummary;
}

export interface CommissionSummary {
  id: number;
  user: number;
  company: string;
  role: string;
  percentage: string;
  value: string;
  table: string;
  payment: number | null;
}

// ===== Commissions =====
export interface CommissionRules {
  id: number;
  bank: string | null;
  table: string | null;
  commission_rate: string;
}

export interface CommissionRulesByUser {
  id: number;
  bank: string | null;
  table: string | null;
  leader_commission_rate: string;
  seller_commission_rate: string;
}

export interface CommissionGroup {
  id: number;
  name: string;
  description: string | null;
  company: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  sellers: number[];
  leaders: number[];
  color: string;
  commission_rules: CommissionRulesByUser[];
  promotora_rules: CommissionRules[];
  by_leader: boolean;
  leader: number | null;
}

export interface CommissionGroupByCompany {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  color: string;
  commission_rules: CommissionRules[];
  is_active: boolean;
  companies: Company[];
}

export interface Commission {
  id: number;
  proposal: string;
  user: number | null;
  user_details: User | null;
  company: string | null;
  role: 'vendedor' | 'lider' | 'empresa';
  role_display: string;
  percentage: string;
  value: string;
  payment: number | null;
  commission_config: number | null;
  created_at: string;
  updated_at: string;
  released: boolean;
  released_at: string | null;
  released_by: number | null;
  paid_at: string | null;
  paid_by: number | null;
}

// ===== Payments =====
export interface Payment {
  id: number;
  user: number;
  user_details: User;
  total_amount: string;
  status: 'pending' | 'approved' | 'paid' | 'rejected';
  status_display: string;
  approved_by: number | null;
  approved_at: string | null;
  paid_at: string | null;
  payment_method: string;
  payment_details: Record<string, unknown>;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface Withdraw {
  id: number;
  user: number;
  amount: string;
  created_at: string;
  payment: number | null;
}

export interface CorbanPayTransaction {
  id: number;
  status: 'pending' | 'active' | 'withdrawn' | 'failed';
  receiver_id: string;
  pre_payment_id: string;
  withdrawal_link: string;
  amount: string;
  error_message: string | null;
  created_at: string;
}

// ===== Bank Access =====
export interface BankAccess {
  id: string;
  company: string;
  company_name: string;
  bank: string;
  bank_name: string;
  username: string;
  description: string;
  is_active: boolean;
  user: number;
  user_name: string;
  last_access: string | null;
  last_access_status: string | null;
  created_by: number | null;
  created_by_name: string | null;
}

// ===== Form Fields =====
export interface FormFieldDef {
  name: string;
  type: 'text' | 'number' | 'select' | 'password' | 'checkbox' | 'color' |
    'date' | 'file' | 'textarea' | 'json' | 'array' | 'email' | 'url' | 'separator';
  label: string;
  required: boolean;
  mask?: string;
  options?: Array<{ value: string | number; label: string }>;
  options_url?: string;
  relation?: string;
  accept?: string;
  min?: number;
  max?: number;
  step?: string;
  default?: unknown;
  value?: unknown;
}

// ===== WebSocket =====
export interface BatchStatusMessage {
  type: string;
  batch_id: string;
  status: string;
  total_proposals: number;
  processed_proposals: number;
  success_proposals: number;
  error_proposals: number;
  progress: number;
  message: string;
  task_id: string | null;
}

// ===== Paginated Response =====
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
