export interface EtlFlowNodeData {
  label?: string;
  nodeType?: string;
  schedule_mode?: 'daily' | 'weekdays' | 'weekly' | 'custom';
  schedule_time?: string;
  schedule_weekdays?: number[];
  cron?: string;
  timezone?: string;
  use_shared_auth?: boolean;
  auth_type?: string;
  auth_config?: Record<string, string>;
  method?: string;
  url?: string;
  headers?: Record<string, string>;
  query_params?: Record<string, string>;
  body?: Record<string, unknown>;
  items_path?: string;
  mappings?: EtlFieldMapping[];
  layout_id?: string;
  layout_name?: string;
  bank_id?: string;
  [key: string]: unknown;
}

export interface EtlVariableExtraction {
  name: string;
  path: string;
}

export interface EtlMappingWhen {
  path: string;
  op: 'eq' | 'ne' | 'empty' | 'not_empty' | 'contains';
  value?: string;
}

export interface EtlFieldMapping {
  source_path: string;
  layout_field: string;
  header_name?: string;
  transform?: string;
  /** Se preenchido, usa este path quando o valor principal vier vazio */
  fallback_source_path?: string;
  /** Condição sobre outro campo do JSON */
  when?: EtlMappingWhen;
  /** Path alternativo quando a condição não bate */
  else_source_path?: string;
  /** Não incluir o campo na linha se a condição não bater */
  skip_if_unmatched?: boolean;
}

export interface EtlFlowDefinition {
  nodes: EtlFlowNodeDef[];
  edges: EtlFlowEdgeDef[];
  viewport?: { x: number; y: number; zoom: number };
}

export interface EtlFlowNodeDef {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: EtlFlowNodeData;
}

export interface EtlFlowEdgeDef {
  id: string;
  source: string;
  target: string;
}

export interface EtlBankProfileSettings {
  paginate_http?: EtlFlowNodeData;
  extract_items?: EtlFlowNodeData;
  detail_steps?: EtlFlowNodeData[];
  notes?: string;
}

export interface ProposalEtlBankProfile {
  id: string;
  bank: string;
  bank_name?: string;
  settings: EtlBankProfileSettings;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface ProposalEtlFlow {
  id: string;
  name: string;
  bank: string | null;
  bank_name?: string;
  is_active: boolean;
  shared_auth_enabled?: boolean;
  shared_auth_type?: string;
  shared_auth_config?: Record<string, string>;
  flow_definition: EtlFlowDefinition;
  created_at: string;
  updated_at: string;
  last_run_status?: string | null;
  last_batch_id?: string | null;
}

export interface EtlExecutionLogEntry {
  timestamp: string;
  level: 'info' | 'success' | 'error' | 'warn';
  node_id: string;
  node_type: string;
  node_label: string;
  message: string;
  params: Record<string, unknown>;
  result: Record<string, unknown>;
}

export interface ProposalEtlRun {
  id: string;
  flow: string;
  flow_name?: string;
  proposal_batch: string | null;
  status: 'running' | 'success' | 'failed';
  started_at: string;
  finished_at: string | null;
  fetched_count: number;
  rows_written: number;
  node_outputs: Record<string, unknown>;
  execution_log?: EtlExecutionLogEntry[];
  trigger_source?: string;
  celery_task_id?: string | null;
  error_message: string | null;
  error_node_id: string | null;
}

export interface EtlMetaAuthType {
  id: string;
  label: string;
  fields: { name: string; type: string; label: string; default?: string; required?: boolean; placeholder?: string }[];
}

export interface EtlMetaNodeType {
  id: string;
  label: string;
  category: string;
}

export interface EtlLayoutField {
  name: string;
  label: string;
  data_type: string;
}

export interface EtlMappingApplyResult {
  mappings: EtlFieldMapping[];
  layoutId: string;
  layoutName: string;
  bankId: string;
  itemsPath: string;
}
