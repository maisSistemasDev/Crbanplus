// API response types matching Django REST Framework serializers

// ===== Auth =====
export interface TokenResponse {
  access: string;
  refresh: string;
}

export interface LoginProfile {
  user_id: number;
  profile_type: 'vendedor' | 'corban' | 'promotora';
  role: string;
  role_label: string;
  company_name: string | null;
  label: string;
}

export type LoginResponse =
  | TokenResponse
  | { requires_profile_selection: true; profiles: LoginProfile[] };

export function isProfileSelectionResponse(
  data: LoginResponse,
): data is { requires_profile_selection: true; profiles: LoginProfile[] } {
  return 'requires_profile_selection' in data && data.requires_profile_selection === true;
}

// ===== Core =====
export interface User {
  id: number;
  cpf: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'admin' | 'empresa_admin' | 'gerente' | 'lider' | 'vendedor' | 'colaborador';
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
  document: string;
  /** @deprecated use document */
  cnpj?: string;
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

export interface PortalUsefulLink {
  id: number;
  title: string;
  url: string;
  is_active: boolean;
  display_order: number;
  created_by: number | null;
  created_by_name?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PortalWallMessage {
  id: number;
  title: string;
  message: string;
  company: string | null;
  company_name?: string;
  starts_at: string | null;
  ends_at: string | null;
  is_active: boolean;
  display_order: number;
  created_by: number | null;
  created_by_name?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PortalDashboard {
  generated_at: string;
  month_proposals_count: number;
  averbadas_value: number;
  analysis_value: number;
  predicted_commission: number;
  received_commission: number;
  advances_value: number;
  physical_pending_count: number;
  open_tickets_count: number;
  received_by_month: Array<{
    year: number;
    month: number;
    label: string;
    value: number;
  }>;
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
  code_in_bank?: string | null;
  description: string;
  min_value: string;
  max_value: string;
  commission_rate: string;
  vigency_date: string;
  alias: string[];
  is_active: boolean;
}

export interface CommissionTableRow {
  table_id: string;
  range_id: string | null;
  bank_id: string;
  bank_name: string;
  agreement_id: string;
  agreement_name: string;
  product: string;
  min_value: string;
  max_value: string;
  commission_rate: string;
  fixed_value: string | null;
  vigency_date: string | null;
  format: string;
  product_type: string;
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
  commission_value?: string | number | null;
  client_document: string;
  client_name: string;
  original_data: Record<string, unknown>;
  batch: string | null;
  release_date: string | null;
  hash: string | null;
  uploaded_at?: string;
  created_at?: string;
  updated_at?: string;
  commissions?: CommissionSummary;
  seller_details?: { first_name: string; last_name: string } | null;
  company_details?: { name: string } | null;
  bank_details?: { name: string } | null;
  agreement_details?: { name: string } | null;
  table_details?: { name_in_bank: string } | null;
  payment_status?: 'not_released' | 'withdraw_available' | 'pending_manual_payment' | 'paid';
  payment_status_display?: string;
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
  release_status?: 'not_released' | 'withdraw_available' | 'pending_manual_payment' | 'paid';
  paid_at?: string | null;
}

// ===== Commissions =====
export interface CommissionRules {
  id: number;
  bank: string | null;
  table: string | null;
  commission_range: string | null;
  commission_rate: string;
}

export interface CommissionRulesByUser {
  id: number;
  bank: string | null;
  table: string | null;
  commission_range: string | null;
  leader_commission_rate: string;
  seller_commission_rate: string;
}

export interface CommissionGroup {
  id: number;
  name: string;
  description: string | null;
  company: string | null;
  company_name?: string | null;
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
  proposal_details?: Proposal;
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
  release_status: 'not_released' | 'withdraw_available' | 'pending_manual_payment' | 'paid';
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
  bank: string;
  bank_name: string;
  bank_access_login_type?: 'cpf' | 'email';
  username: string;
  password?: string;
  is_active: boolean;
  is_master: boolean;
  notes: string | null;
  link: string | null;
  alias?: string[];
  user: number;
  user_name: string;
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

// ===== Débitos =====
export interface PortalDebit {
  id: number;
  owner_name: string | null;
  owner_type: 'user' | 'company';
  amount: string;
  remaining_amount: string;
  reason: string;
  origin: 'manual' | 'sinistro';
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PortalDebitDetail extends PortalDebit {
  origin_claims: Array<{
    claim_id: number;
    claim_type: string;
    claim_type_display: string;
    amount: string;
    description: string;
    proposal_id: string;
    contract_number: string | null;
    client_name: string | null;
    client_document: string | null;
    created_at: string;
  }>;
  applications: Array<{
    commission_id: number;
    amount: string;
    proposal_id: string;
    contract_number: string | null;
    client_name: string | null;
    role_display: string;
    created_at: string;
  }>;
}

// ===== Paginated Response =====
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ===== AI Agent =====
export interface TableUpdateSuggestion {
  id: number;
  commission_group: number;
  commission_group_name: string;
  table: string;
  table_name: string;
  bank_name: string;
  old_config: Record<string, unknown>[];
  suggested_config: Record<string, unknown>[];
  ai_reasoning: string;
  status: 'pending' | 'accepted' | 'rejected';
  created_at: string;
  applied_at: string | null;
  applied_by: number | null;
}

export interface AiMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  tool_calls: unknown | null;
  created_at: string;
  tour_name?: string | null;
  file_url?: string | null;
  file_name?: string | null;
}

export interface AiConversation {
  id: number;
  created_at: string;
  updated_at: string;
  messages: AiMessage[];
}
