import type { EtlFieldMapping } from './etl';

export interface WebhookEndpoint {
  id: string;
  name: string;
  bank: string;
  bank_name?: string;
  layout: string | null;
  layout_name?: string | null;
  items_path: string;
  mappings: EtlFieldMapping[];
  is_active: boolean;
  auto_process: boolean;
  inbound_url: string;
  delivery_count?: number;
  last_delivery_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WebhookEndpointCreateResponse extends WebhookEndpoint {
  secret_token: string;
}

export interface WebhookDelivery {
  id: string;
  status: 'received' | 'mapped' | 'batch_created' | 'appended' | 'failed';
  items_count: number;
  error_message?: string;
  source_ip?: string | null;
  batch_id?: string | null;
  batch_total_rows?: number | null;
  batch_created?: boolean;
  created_at: string;
}

export interface WebhookTestResult {
  items_count: number;
  rows_count: number;
  sample_item: Record<string, unknown> | null;
  sample_row: Record<string, unknown> | null;
  rows_preview: Record<string, unknown>[];
}
