import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import toast from 'react-hot-toast';
import {
  Key, Plus, Trash2, Ban, Copy, CheckCircle, AlertTriangle,
  Clock, Shield, ChevronDown, ChevronUp, Eye, EyeOff,
} from 'lucide-react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { QueryProvider } from '../../providers/QueryProvider';
import { Button } from '../../ui/Button';
import { Modal } from '../../ui/Modal';
import { Badge } from '../../ui/Badge';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Scope {
  value: string;
  label: string;
}

interface APIKey {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  is_active: boolean;
  is_expired: boolean;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
  created_by_name: string;
  company_name: string | null;
}

interface CreateAPIKeyResponse extends APIKey {
  key: string;
  warning: string;
}

// ─── Scope groups ─────────────────────────────────────────────────────────────

const SCOPE_GROUPS: Record<string, string[]> = {
  'Usuários': ['users:read', 'users:write'],
  'Corbans': ['companies:read', 'companies:write'],
  'Bancos': ['banks:read', 'banks:write'],
  'Tabelas': ['tables:read', 'tables:write'],
  'Convênios': ['agreements:read', 'agreements:write'],
  'Propostas': ['proposals:read', 'proposals:write'],
  'Comissões': ['commissions:read', 'commissions:write'],
  'Pagamentos': ['payments:read', 'payments:write'],
  'Acessos Bancários': ['bank_access:read', 'bank_access:write'],
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(d: string | null) {
  if (!d) return '—';
  return format(new Date(d), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR });
}

function keyStatus(k: APIKey) {
  if (!k.is_active) return 'revogada';
  if (k.is_expired) return 'expirada';
  return 'ativa';
}

// ─── Create Modal ─────────────────────────────────────────────────────────────

function CreateKeyModal({ onClose, onCreated }: { onClose: () => void; onCreated: (resp: CreateAPIKeyResponse) => void }) {
  const [name, setName] = useState('');
  const [selectedScopes, setSelectedScopes] = useState<Set<string>>(new Set());
  const [expiresAt, setExpiresAt] = useState('');
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = { name, scopes: [...selectedScopes] };
      if (expiresAt) body.expires_at = new Date(expiresAt).toISOString();
      const res = await api.post<CreateAPIKeyResponse>(ENDPOINTS.API_KEYS, body);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      onCreated(data);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function toggleScope(scope: string) {
    setSelectedScopes((prev) => {
      const next = new Set(prev);
      next.has(scope) ? next.delete(scope) : next.add(scope);
      return next;
    });
  }

  function toggleGroup(scopes: string[]) {
    setSelectedScopes((prev) => {
      const next = new Set(prev);
      const allSelected = scopes.every((s) => next.has(s));
      scopes.forEach((s) => (allSelected ? next.delete(s) : next.add(s)));
      return next;
    });
  }

  return (
    <Modal isOpen onClose={onClose} title="Nova Chave de API" size="lg">
      <div className="space-y-5 p-1">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Nome da chave *</label>
          <input
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
            placeholder="Ex: Integração ERP, App Mobile..."
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Expiração (opcional)</label>
          <input
            type="datetime-local"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
            value={expiresAt}
            onChange={(e) => setExpiresAt(e.target.value)}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Escopos * — {selectedScopes.size} selecionado(s)
          </label>
          <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
            {Object.entries(SCOPE_GROUPS).map(([group, scopes]) => {
              const allSelected = scopes.every((s) => selectedScopes.has(s));
              const someSelected = scopes.some((s) => selectedScopes.has(s));
              return (
                <div key={group} className="border border-gray-200 rounded-lg p-3">
                  <label className="flex items-center gap-2 cursor-pointer mb-2">
                    <input
                      type="checkbox"
                      checked={allSelected}
                      ref={(el) => { if (el) el.indeterminate = someSelected && !allSelected; }}
                      onChange={() => toggleGroup(scopes)}
                      className="rounded"
                    />
                    <span className="text-sm font-semibold text-gray-700">{group}</span>
                  </label>
                  <div className="flex flex-wrap gap-2 ml-6">
                    {scopes.map((scope) => (
                      <label key={scope} className="flex items-center gap-1.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedScopes.has(scope)}
                          onChange={() => toggleScope(scope)}
                          className="rounded"
                        />
                        <span className="text-xs text-gray-600">
                          {scope.endsWith(':read') ? '👁 Leitura' : '✏️ Escrita'}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <Button variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button
            onClick={() => mutation.mutate()}
            loading={mutation.isPending}
            disabled={!name.trim() || selectedScopes.size === 0}
            icon={<Plus size={16} />}
          >
            Criar Chave
          </Button>
        </div>
      </div>
    </Modal>
  );
}

// ─── Show Key Modal ────────────────────────────────────────────────────────────

function ShowKeyModal({ keyData, onClose }: { keyData: CreateAPIKeyResponse; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  const [visible, setVisible] = useState(false);

  function copy() {
    navigator.clipboard.writeText(keyData.key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
    toast.success('Chave copiada!');
  }

  return (
    <Modal isOpen onClose={onClose} title="🔑 Chave criada com sucesso!" size="lg">
      <div className="space-y-4 p-1">
        <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 flex gap-3">
          <AlertTriangle size={20} className="text-amber-600 shrink-0 mt-0.5" />
          <p className="text-sm text-amber-800">
            <strong>Atenção:</strong> esta é a única vez que a chave completa será exibida. Copie e guarde agora em local seguro.
          </p>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Chave de API</label>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-gray-900 rounded-lg px-4 py-3 font-mono text-sm text-green-400 break-all select-all overflow-hidden">
              {visible ? keyData.key : '•'.repeat(40)}
            </div>
            <button
              onClick={() => setVisible(!visible)}
              className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100"
              title={visible ? 'Ocultar' : 'Mostrar'}
            >
              {visible ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
            <button
              onClick={copy}
              className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100"
              title="Copiar"
            >
              {copied ? <CheckCircle size={18} className="text-green-600" /> : <Copy size={18} />}
            </button>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-3 text-xs font-mono text-gray-600">
          <p className="text-gray-500 mb-1">Exemplo de uso:</p>
          <p>Authorization: Api-Key <span className="text-blue-600">{keyData.key.substring(0, 16)}...</span></p>
        </div>

        <div className="flex justify-end">
          <Button onClick={onClose}>Entendi, já salvei a chave</Button>
        </div>
      </div>
    </Modal>
  );
}

// ─── Key Card ─────────────────────────────────────────────────────────────────

function KeyCard({ apiKey, onRevoke }: { apiKey: APIKey; onRevoke: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false);
  const status = keyStatus(apiKey);

  const statusBadge = {
    ativa: <Badge variant="success">Ativa</Badge>,
    revogada: <Badge variant="error">Revogada</Badge>,
    expirada: <Badge variant="warning">Expirada</Badge>,
  }[status];

  return (
    <div className="bg-[var(--color-card-bg)] border border-[var(--color-border)] rounded-xl shadow-sm overflow-hidden">
      <div className="p-4 flex items-start gap-4">
        <div className="w-10 h-10 rounded-lg bg-[var(--color-primary)]/10 flex items-center justify-center shrink-0">
          <Key size={18} className="text-[var(--color-primary)]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-[var(--color-text-primary)]">{apiKey.name}</span>
            {statusBadge}
            {apiKey.company_name && (
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                {apiKey.company_name}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-0.5 font-mono">{apiKey.prefix}••••••••••••••</p>
          <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Shield size={12} /> {apiKey.scopes.length} escopo(s)
            </span>
            <span className="flex items-center gap-1">
              <Clock size={12} /> Criada em {fmtDate(apiKey.created_at)}
            </span>
            {apiKey.last_used_at && (
              <span className="flex items-center gap-1">
                <CheckCircle size={12} /> Último uso {fmtDate(apiKey.last_used_at)}
              </span>
            )}
            {apiKey.expires_at && (
              <span className="flex items-center gap-1">
                <AlertTriangle size={12} /> Expira {fmtDate(apiKey.expires_at)}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-gray-400 hover:text-gray-600 p-1 rounded"
            title="Ver escopos"
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          {status === 'ativa' && (
            <Button
              variant="danger"
              size="sm"
              icon={<Ban size={14} />}
              onClick={() => onRevoke(apiKey.id)}
            >
              Revogar
            </Button>
          )}
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 border-t border-[var(--color-border)] pt-3">
          <p className="text-xs font-medium text-gray-500 mb-2">Escopos autorizados:</p>
          <div className="flex flex-wrap gap-1.5">
            {apiKey.scopes.map((s) => (
              <span key={s} className="text-xs bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full font-mono">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function DeveloperPage() {
  const [showCreate, setShowCreate] = useState(false);
  const [newKey, setNewKey] = useState<CreateAPIKeyResponse | null>(null);
  const queryClient = useQueryClient();

  const { data: keys = [], isLoading } = useQuery<APIKey[]>({
    queryKey: ['api-keys'],
    queryFn: async () => {
      const res = await api.get<{ results?: APIKey[] } | APIKey[]>(ENDPOINTS.API_KEYS);
      return (res as { results?: APIKey[] }).results ?? (res as APIKey[]);
    },
  });

  const revokeMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.post(ENDPOINTS.API_KEY_REVOKE(id));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      toast.success('Chave revogada com sucesso.');
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function handleRevoke(id: string) {
    if (!confirm('Revogar esta chave? Essa ação não pode ser desfeita.')) return;
    revokeMutation.mutate(id);
  }

  const active = keys.filter((k) => k.is_active && !k.is_expired);
  const inactive = keys.filter((k) => !k.is_active || k.is_expired);

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] flex items-center gap-2">
            <Key size={26} className="text-[var(--color-primary)]" />
            Área do Desenvolvedor
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Gerencie as chaves de API para integrar sistemas externos.
            Cada chave possui escopos que limitam as operações permitidas.
          </p>
        </div>
        <Button icon={<Plus size={16} />} onClick={() => setShowCreate(true)}>
          Nova Chave
        </Button>
      </div>

      {/* Info cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: 'Total', value: keys.length, icon: <Key size={20} />, color: 'blue' },
          { label: 'Ativas', value: active.length, icon: <CheckCircle size={20} />, color: 'green' },
          { label: 'Revogadas / Expiradas', value: inactive.length, icon: <Ban size={20} />, color: 'red' },
        ].map((card) => (
          <div key={card.label} className="bg-[var(--color-card-bg)] border border-[var(--color-border)] rounded-xl p-4 flex items-center gap-4">
            <div className={`w-10 h-10 rounded-lg bg-${card.color}-100 flex items-center justify-center text-${card.color}-600`}>
              {card.icon}
            </div>
            <div>
              <p className="text-2xl font-bold text-[var(--color-text-primary)]">{card.value}</p>
              <p className="text-xs text-gray-500">{card.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Auth guide */}
      <div className="bg-gray-900 rounded-xl p-5 text-sm">
        <p className="text-gray-400 text-xs uppercase tracking-wider mb-3">Como usar</p>
        <div className="space-y-2 font-mono">
          <p className="text-gray-300">{'# Envie o header em todas as requisições:'}</p>
          <p><span className="text-yellow-400">Authorization</span><span className="text-gray-400">: </span><span className="text-green-400">Api-Key </span><span className="text-blue-300">crb_sua_chave_aqui</span></p>
          <p className="text-gray-300 mt-3">{'# Exemplo com curl:'}</p>
          <p className="text-gray-200 break-all">
            <span className="text-cyan-400">curl</span>
            <span className="text-gray-400"> -H </span>
            <span className="text-orange-300">"Authorization: Api-Key crb_sua_chave"</span>
            <span className="text-gray-400"> \</span>
          </p>
          <p className="text-gray-200 break-all pl-4">
            <span className="text-cyan-400">{'  '}</span>
            <span className="text-blue-300">https://api.seudominio.com.br/api/users/</span>
          </p>
        </div>
      </div>

      {/* Keys list */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin h-8 w-8 border-4 border-[var(--color-primary)] border-t-transparent rounded-full" />
        </div>
      ) : keys.length === 0 ? (
        <div className="text-center py-16 border-2 border-dashed border-gray-200 rounded-xl">
          <Key size={40} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500 font-medium">Nenhuma chave de API criada</p>
          <p className="text-gray-400 text-sm mt-1">Crie sua primeira chave para começar a integrar.</p>
          <Button className="mt-4" icon={<Plus size={16} />} onClick={() => setShowCreate(true)}>
            Criar primeira chave
          </Button>
        </div>
      ) : (
        <div className="space-y-6">
          {active.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
                Chaves Ativas ({active.length})
              </h2>
              {active.map((k) => (
                <KeyCard key={k.id} apiKey={k} onRevoke={handleRevoke} />
              ))}
            </div>
          )}
          {inactive.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">
                Revogadas / Expiradas ({inactive.length})
              </h2>
              {inactive.map((k) => (
                <KeyCard key={k.id} apiKey={k} onRevoke={handleRevoke} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      {showCreate && (
        <CreateKeyModal
          onClose={() => setShowCreate(false)}
          onCreated={(data) => {
            setShowCreate(false);
            setNewKey(data);
          }}
        />
      )}
      {newKey && (
        <ShowKeyModal keyData={newKey} onClose={() => setNewKey(null)} />
      )}
    </div>
  );
}

export function DeveloperPageShell() {
  return (
    <QueryProvider>
      <DeveloperPage />
    </QueryProvider>
  );
}
