export const ENDPOINTS = {
  // Auth
  TOKEN: '/token/',
  TOKEN_REFRESH: '/token/refresh/',
  CURRENT_USER: '/users/me/',
  PROFILE_SETTINGS: '/users/me/',
  CORBANPAY_CONFIG: '/config/corbanpay/',
  AI_SETTINGS: '/config/ai/',

  // Setup
  SETUP_STATUS: '/setup/status/',
  SETUP: '/setup/',

  // Users
  USERS: '/users/',
  USER_DETAIL: (id: number) => `/users/${id}/`,
  SELLERS: '/users/sellers/',
  SELLER_DETAIL: (id: number) => `/users/sellers/${id}/`,
  LEADERS: '/users/leaders/',
  CHANGE_LEADER: (id: number) => `/users/${id}/change_leader/`,
  BATCH_CHANGE_LEADER: '/users/batch_change_leader/',
  CREATE_MANAGER: '/users/managers/',
  IMPORT_SELLERS: '/users/import/sellers/',
  IMPORT_SELLERS_TEMPLATE: '/users/import/sellers/template/',

  // Internal Users (Promotora)
  INTERNAL_USERS: '/internal-users/',
  INTERNAL_USER_DETAIL: (id: number) => `/internal-users/${id}/`,
  INTERNAL_USER_PERMISSIONS: (id: number) => `/internal-users/${id}/permissions/`,
  AVAILABLE_PERMISSIONS: '/internal-users/available-permissions/',
  INTERNAL_USER_FORM_FIELDS: '/internal-users/form-fields/',
  
  // Permission Templates
  PERMISSION_TEMPLATES: '/permission-templates/',
  PERMISSION_TEMPLATE_DETAIL: (id: number) => `/permission-templates/${id}/`,
  APPLY_TEMPLATE: (id: number) => `/permission-templates/${id}/apply-to-user/`,

  // Companies
  COMPANIES: '/companies/',
  COMPANY_DETAIL: (id: string) => `/companies/${id}/`,

  // Banks
  BANKS: '/banks/',
  BANK_DETAIL: (id: string) => `/banks/${id}/`,
  AGREEMENTS: '/agreements/',
  AGREEMENT_DETAIL: (id: string) => `/agreements/${id}/`,
  TABLES: '/tables/',
  TABLE_DETAIL: (id: string) => `/tables/${id}/`,
  TABLES_BULK_DELETE: '/tables/bulk-delete/',
  TABLES_CREATE_BATCH: '/tables/create-batch/',
  TABLES_EXPORT_CSV: '/tables/export-csv/',
  TABLES_EXPORT_CSV_BANK: (bankId: string) => `/tables/export-csv/${bankId}/`,
  TABLES_BY_BANK: (bankId: string) => `/tables/by-bank/${bankId}/`,
  TABLE_HISTORY: (tableId: string) => `/tables/${tableId}/history/`,

  // Bank Access
  BANK_ACCESSES: '/bank-accesses/',
  BANK_ACCESS_DETAIL: (id: string) => `/bank-accesses/${id}/`,
  ACCESS_LOGS: '/access-logs/',

  // Proposals
  PROPOSALS: '/proposals/',
  PREVIEW_ROWS: '/proposals/preview-rows/',
  PROPOSAL_FIELDS: '/proposals/fields/',
  LAYOUTS: '/proposals/layouts/',
  LAYOUT_DETAIL: (id: string) => `/proposals/layouts/${id}/`,
  BATCHES: '/proposals/batch/',
  BATCH_DETAIL: (id: string) => `/proposals/batch/${id}/`,
  BATCH_PROPOSALS: (id: string) => `/proposals/batch/${id}/proposals/`,
  PROPOSAL_PREVIEW: (id: string) => `/proposals/preview/${id}/`,
  AGREEMENT_NAMES: '/proposals/agreement-names/',
  TABLE_NAMES: '/proposals/table-names/',
  USER_NAMES: '/proposals/user-names/',
  STATUS_PAYMENT: '/proposals/status-payment/',

  // Commissions
  COMMISSIONS: '/commissions/',
  COMMISSION_DETAIL: (id: number) => `/commissions/${id}/`,
  COMMISSION_MIRROR: '/commissions/mirror/',
  COMMISSION_BALANCE: '/commissions/balance/',
  COMMISSION_RELEASE: '/commissions/release/',
  COMMISSION_EXPORT: '/commissions/export/',
  COMMISSION_UPDATE_STATUS: '/commissions/update-status/',

  // Commission Groups
  COMMISSION_GROUPS: '/commission-groups/',
  COMMISSION_GROUP_DETAIL: (id: number) => `/commission-groups/${id}/`,
  COMMISSION_GROUP_MEMBERS: (id: number) => `/commission-groups/${id}/members/`,
  COMMISSION_GROUPS_BY_COMPANY: '/commission-groups/by-company/',
  COMMISSION_GROUP_BY_COMPANY_DETAIL: (id: number) => `/commission-groups/by-company/${id}/`,
  COMMISSION_GROUP_BY_COMPANY_COMPANIES: (id: number) => `/commission-groups/by-company/${id}/companies/`,
  COMMISSION_GROUP_MAX_RATES: '/commission-groups/max-rates/',
  COMMISSION_GROUP_BY_COMPANY_MAX_RATES: '/commission-groups/by-company/max-rates/',
  COMMISSION_GROUP_EXPORT_CSV: '/commission-groups/export-csv-template/',
  COMMISSION_GROUP_IMPORT_CSV: (groupId: number) => `/commission-groups/${groupId}/import-csv/`,

  // Payments
  PAYMENTS: '/payments/',
  WITHDRAWALS: '/withdrawals/',
  WITHDRAWALS_CORBANPAY: '/withdrawals/corbanpay/',
  GENERATE_COMMISSIONS: '/payments/generate-comissions/',

  // Push Notifications
  PUSH_SUBSCRIBE: '/push/subscribe/',

  // Importação em lote
  IMPORT_CREATE: '/import/',
  IMPORT_STATUS: (jobId: string) => `/import/${jobId}/`,
  IMPORT_TEMPLATE: (entityType: string) => `/import/template/${entityType}/`,

  // Form Fields
  FORM_FIELDS_USERS: '/form-fields/users/',
  FORM_FIELDS_USERS_CREATE: '/form-fields/users/create/',
  FORM_FIELDS_COMPANIES: '/form-fields/companies/',
  FORM_FIELDS_EXTRA_DATA: '/form-fields/extra-data/',
  FORM_FIELDS_MANAGERS: '/form-fields/managers/',
  FORM_FIELDS_BANKS: '/banks/form-fields/',
  FORM_FIELDS_AGREEMENTS: '/agreements/form-fields/',
  FORM_FIELDS_TABLES: '/tables/form-fields/',
  FORM_FIELDS_BANK_ACCESS: '/form-fields/bank-accesses/',
  FORM_FIELDS_ACCESS_LOGS: '/form-fields/access-logs/',
  FORM_FIELDS_LAYOUTS: '/proposals/layouts/form-fields/',
  FORM_FIELDS_COMMISSION_GROUPS: '/commission-groups/form-fields/',
  FORM_FIELDS_PAYMENTS: '/payments/form-fields/',

  // API Keys (Developer Area)
  API_KEYS: '/api-keys/',
  API_KEY_DETAIL: (id: string) => `/api-keys/${id}/`,
  API_KEY_REVOKE: (id: string) => `/api-keys/${id}/revoke/`,
  API_KEY_AVAILABLE_SCOPES: '/api-keys/available-scopes/',

  // AI Agent
  AI_SUGGESTIONS: '/ai/suggestions/',
  AI_SUGGESTION_ACCEPT: (id: number) => `/ai/suggestions/${id}/accept/`,
  AI_SUGGESTION_REJECT: (id: number) => `/ai/suggestions/${id}/reject/`,
  AI_CONVERSATIONS: '/ai/conversations/',
  AI_CONVERSATION_DETAIL: (id: number) => `/ai/conversations/${id}/`,
} as const;
