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
  role: 'admin' | 'empresa_admin' | 'gerente' | 'gerente_comercial' | 'lider' | 'vendedor' | 'colaborador';
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
  code_in_bank: string | null;
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
  error_summary?: { error_message: string; count: number }[];
  saved_count?: number;
  created_at: string;
  updated_at: string;
}

export interface Proposal {
  id: string;
  seller: number | null;
  seller_details?: { first_name: string; last_name: string; display_name?: string };
  digitador: string | null;
  bank_access: number | null;
  bank_access_details?: { id: number; username: string; display_name?: string };
  contract_number: string;
  company: string;
  company_details?: { name: string };
  bank: string;
  bank_details?: { name: string };
  agreement: string;
  agreement_details?: { name: string };
  table: string;
  table_details?: { name_in_bank: string };
  status: string;
  payment_status?: string;
  payment_status_display?: string;
  disbursement_date: string;
  amount: string;
  commission_value?: string | number | null;
  client_document: string;
  client_name: string;
  original_data: Record<string, unknown>;
  batch: string | null;
  release_date: string | null;
  hash: string | null;
  commissions?: CommissionSummary;
  claim_details?: ProposalClaimSummary | null;
}

export interface ProposalClaimSummary {
  id: number;
  claim_type: 'fraude' | 'pago_corban_errado';
  claim_type_display: string;
  amount: string;
  created_at: string;
  charged_company_name: string | null;
  correct_company_name: string | null;
  total: number;
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

export interface CommissionRecipient {
  type: 'user' | 'company';
  id: string | number;
  name: string;
  document?: string | null;
}

/** Linha compacta de comissão usada nos modais de detalhe e no consolidado. */
export interface CommissionRow {
  id: number;
  proposal_id: string | null;
  contract_number: string | null;
  client_name: string | null;
  client_document: string | null;
  proposal_amount: string;
  bank_name: string | null;
  table_name: string | null;
  matricula: string | null;
  role: string;
  role_display: string;
  percentage: string;
  total_value: string;
  debit_value: string;
  net_value: string;
  is_zeroed: boolean;
  release_status: string;
  created_at: string;
}

export interface ConsolidatedCommissionGroup {
  key: string;
  recipient: CommissionRecipient;
  /** O consolidado agrupa por recebedor e status; status distintos não se somam. */
  release_status: string;
  release_status_display: string;
  total_value: string;
  debit_value: string;
  net_value: string;
  is_zeroed: boolean;
  commissions_count: number;
  commission_ids: number[];
  items: CommissionRow[];
  roles: string[];
  companies: string[];
}

export interface CommissionTotals {
  total_value: string;
  debit_value: string;
  net_value: string;
  commissions_count: number;
  zeroed_count: number;
}

export interface ConsolidatedCommissionResponse {
  consolidated: true;
  results: ConsolidatedCommissionGroup[];
  totals: CommissionTotals;
}

export interface DebitDetailEntry {
  debit_id: number;
  reason: string;
  origin: string;
  owner_name: string;
  debit_amount: string;
  remaining_amount: string;
  created_at: string;
  projected: boolean;
  amount: string;
  commissions: Array<{
    commission_id: number;
    amount: string;
    contract_number: string | null;
    client_name: string | null;
  }>;
}

export interface DebitDetailResponse {
  results: DebitDetailEntry[];
  total: string;
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
  gross_value?: string | null;
  debit_discount?: string;
  debit_discounts?: { debit_id: number; amount: string; reason: string; origin?: string }[];
  /** Valor cheio da comissão, antes de qualquer débito. */
  total_value?: string;
  /** Débito já abatido ou projetado para a próxima liberação. */
  debit_value?: string;
  /** Valor que será efetivamente pago. */
  net_value?: string;
  is_zeroed?: boolean;
  company_name?: string | null;
  recipient?: CommissionRecipient | null;
  row?: CommissionRow;
  payment: number | null;
  commission_config: number | null;
  created_at: string;
  updated_at: string;
  released: boolean;
  released_at: string | null;
  released_by: number | null;
  paid_at: string | null;
  paid_by: number | null;
  release_status?: 'not_released' | 'withdraw_available' | 'pending_manual_payment' | 'paid';
  proposal_details?: {
    contract_number?: string;
    client_name?: string;
    disbursement_date?: string;
  } | null;
}

export interface UserDebit {
  id: number;
  user: number | null;
  user_details: User | null;
  company: string | null;
  company_details: Company | null;
  owner_name: string | null;
  owner_type: 'user' | 'company';
  amount: string;
  remaining_amount: string;
  reason: string;
  origin: 'manual' | 'sinistro';
  is_active: boolean;
  created_by: number | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
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
