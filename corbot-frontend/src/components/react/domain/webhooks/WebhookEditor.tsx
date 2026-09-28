import { useCallback, useEffect, useMemo, useState } from 'react';
import { Copy, KeyRound, Play, Save, Webhook } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import type { ModelField } from '../../../../lib/api/types';
import type { EtlFieldMapping, EtlMappingApplyResult } from '../../../../lib/api/types/etl';
import type {
  WebhookDelivery,
  WebhookEndpoint,
  WebhookEndpointCreateResponse,
  WebhookTestResult,
} from '../../../../lib/api/types/webhooks';
import { resolveJsonPath } from '../../../../lib/etl/jsonPath';
import { EtlFieldMappingModal } from '../proposal-etl/EtlFieldMappingModal';
import { EtlMappingRuleFields } from '../proposal-etl/EtlMappingRuleFields';
import { Button } from '../../ui/Button';
import { Input } from '../../ui/Input';
import { PageHeader } from '../../ui/PageHeader';
import { Badge } from '../../ui/Badge';
import { Select } from '../../ui/Select';

interface BankOption {
  id: string;
  name: string;
}

function extractSampleItem(payload: unknown, itemsPath: string): Record<string, unknown> {
  const resolved = itemsPath ? resolveJsonPath(payload, itemsPath) : payload;
  const data = resolved ?? payload;
  if (Array.isArray(data) && data[0] && typeof data[0] === 'object') {
    return data[0] as Record<string, unknown>;
  }
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    return data as Record<string, unknown>;
  }
  return {};
}

interface WebhookEditorProps {
  webhookId?: string;
}

export function WebhookEditor({ webhookId }: WebhookEditorProps) {
  const isEdit = Boolean(webhookId);
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [banks, setBanks] = useState<BankOption[]>([]);
  const [modelFields, setModelFields] = useState<ModelField[]>([]);
  const [fieldTransforms, setFieldTransforms] = useState<{ id: string; label: string }[]>([]);
  const [conditionOperators, setConditionOperators] = useState<{ id: string; label: string }[]>([]);
  const [deliveries, setDeliveries] = useState<WebhookDelivery[]>([]);
  const [mappingOpen, setMappingOpen] = useState(false);
  const [secretToken, setSecretToken] = useState<string | null>(null);
  const [inboundUrl, setInboundUrl] = useState('');
  const [testResult, setTestResult] = useState<WebhookTestResult | null>(null);

  const [name, setName] = useState('');
  const [bankId, setBankId] = useState('');
  const [layoutId, setLayoutId] = useState('');
  const [layoutName, setLayoutName] = useState('');
  const [itemsPath, setItemsPath] = useState('');
  const [mappings, setMappings] = useState<EtlFieldMapping[]>([]);
  const [isActive, setIsActive] = useState(true);
  const [autoProcess, setAutoProcess] = useState(true);
  const [payloadText, setPayloadText] = useState('{\n  "data": []\n}');

  const sampleItem = useMemo(() => {
    try {
      const payload = JSON.parse(payloadText);
      return extractSampleItem(payload, itemsPath);
    } catch {
      return {};
    }
  }, [payloadText, itemsPath]);

  const loadMeta = useCallback(async () => {
    const [banksRes, fieldsRes, metaRes] = await Promise.all([
      api.get<BankOption[] | { results: BankOption[] }>(`${ENDPOINTS.BANKS}?page_size=500`),
      api.get<ModelField[]>(ENDPOINTS.FORM_FIELDS_LAYOUTS),
      api.get<{ field_transforms: { id: string; label: string }[]; condition_operators: { id: string; label: string }[] }>(
        ENDPOINTS.PROPOSAL_ETL_META,
      ),
    ]);
    setBanks(Array.isArray(banksRes) ? banksRes : (banksRes.results ?? []));
    setModelFields(Array.isArray(fieldsRes) ? fieldsRes : []);
    setFieldTransforms(metaRes.field_transforms ?? []);
    setConditionOperators(metaRes.condition_operators ?? []);
  }, []);

  const loadWebhook = useCallback(async () => {
    if (!webhookId) return;
    setLoading(true);
    try {
      const [endpoint, deliveryList] = await Promise.all([
        api.get<WebhookEndpoint>(ENDPOINTS.WEBHOOK_DETAIL(webhookId)),
        api.get<WebhookDelivery[]>(ENDPOINTS.WEBHOOK_DELIVERIES(webhookId)),
      ]);
      setName(endpoint.name);
      setBankId(endpoint.bank);
      setLayoutId(endpoint.layout || '');
      setLayoutName(endpoint.layout_name || '');
      setItemsPath(endpoint.items_path || '');
      setMappings(endpoint.mappings || []);
      setIsActive(endpoint.is_active);
      setAutoProcess(endpoint.auto_process);
      setInboundUrl(endpoint.inbound_url);
      setDeliveries(deliveryList);
      const storedSecret = sessionStorage.getItem(`webhook-secret-${webhookId}`);
      if (storedSecret) {
        setSecretToken(storedSecret);
        sessionStorage.removeItem(`webhook-secret-${webhookId}`);
      }
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [webhookId]);

  useEffect(() => {
    loadMeta();
    loadWebhook();
  }, [loadMeta, loadWebhook]);

  async function handleSave() {
    if (!name.trim() || !bankId) {
      toast.error('Preencha nome e banco.');
      return;
    }
    setSaving(true);
    try {
      const body = {
        name: name.trim(),
        bank: bankId,
        layout: layoutId || null,
        items_path: itemsPath,
        mappings,
        is_active: isActive,
        auto_process: autoProcess,
      };
      if (isEdit && webhookId) {
        await api.patch(ENDPOINTS.WEBHOOK_DETAIL(webhookId), body);
        toast.success('Webhook atualizado.');
        loadWebhook();
      } else {
        const created = await api.post<WebhookEndpointCreateResponse>(ENDPOINTS.WEBHOOKS, body);
        sessionStorage.setItem(`webhook-secret-${created.id}`, created.secret_token);
        toast.success('Webhook criado. Copie o token secreto na próxima tela.');
        window.location.href = `/proposals/webhooks/${created.id}`;
      }
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    if (!webhookId) {
      toast.error('Salve o webhook antes de testar.');
      return;
    }
    let payload: unknown;
    try {
      payload = JSON.parse(payloadText);
    } catch {
      toast.error('JSON de exemplo inválido.');
      return;
    }
    setTesting(true);
    try {
      const result = await api.post<WebhookTestResult>(ENDPOINTS.WEBHOOK_TEST(webhookId), { payload });
      setTestResult(result);
      toast.success(`${result.rows_count} linha(s) mapeada(s) de ${result.items_count} item(ns).`);
    } catch (err) {
      toast.error(extractErrorMessage(err));
      setTestResult(null);
    } finally {
      setTesting(false);
    }
  }

  async function handleRegenerateSecret() {
    if (!webhookId) return;
    try {
      const res = await api.post<{ secret_token: string; inbound_url: string }>(
        ENDPOINTS.WEBHOOK_REGENERATE_SECRET(webhookId),
      );
      setSecretToken(res.secret_token);
      setInboundUrl(res.inbound_url);
      toast.success('Novo token gerado. Atualize o sistema que envia o webhook.');
    } catch (err) {
      toast.error(extractErrorMessage(err));
    }
  }

  function copyText(text: string, label: string) {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copiado.`);
  }

  function applyMappingResult(result: EtlMappingApplyResult) {
    setMappings(result.mappings);
    setLayoutId(result.layoutId);
    setLayoutName(result.layoutName);
    setBankId(result.bankId);
    if (result.itemsPath) setItemsPath(result.itemsPath);
    setMappingOpen(false);
    toast.success('Mapeamento aplicado. Salve o webhook.');
  }

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="animate-spin h-8 w-8 border-2 border-[var(--color-primary)] border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={isEdit ? name || 'Editar webhook' : 'Novo webhook'}
        subtitle="Um lote por banco por dia. Propostas do mesmo dia entram no lote aberto; se já foi processado, abre um novo lote."
        actions={
          <Button onClick={handleSave} loading={saving}>
            <Save size={16} />
            Salvar
          </Button>
        }
      />

      {isEdit && inboundUrl && (
        <div className="card space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-800">
            <Webhook size={16} />
            Endpoint de recebimento
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <code className="flex-1 min-w-0 text-xs bg-gray-50 border rounded-lg px-3 py-2 break-all">
              POST {inboundUrl}
            </code>
            <Button size="sm" variant="secondary" onClick={() => copyText(inboundUrl, 'URL')}>
              <Copy size={14} />
              URL
            </Button>
          </div>
          <p className="text-xs text-gray-500">
            Envie o header <code className="bg-gray-100 px-1 rounded">X-Webhook-Secret</code> com o token secreto.
          </p>
          {secretToken && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
              <strong>Token (copie agora):</strong>{' '}
              <code className="break-all">{secretToken}</code>
              <button
                type="button"
                className="ml-2 underline"
                onClick={() => copyText(secretToken, 'Token')}
              >
                Copiar
              </button>
            </div>
          )}
          {isEdit && (
            <Button size="sm" variant="secondary" onClick={handleRegenerateSecret}>
              <KeyRound size={14} />
              Gerar novo token
            </Button>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card space-y-3">
          <h3 className="text-sm font-semibold text-gray-800">Configuração</h3>
          <Input label="Nome" value={name} onChange={(e) => setName(e.target.value)} />
          <Select
            label="Banco"
            value={bankId}
            onChange={(e) => setBankId(e.target.value)}
            options={[{ value: '', label: 'Selecione...' }, ...banks.map((b) => ({ value: b.id, label: b.name }))]}
          />
          <Input
            label="JSON path dos itens (opcional)"
            value={itemsPath}
            onChange={(e) => setItemsPath(e.target.value)}
            placeholder="$.data ou $.items"
          />
          <Input
            label="Layout vinculado"
            value={layoutName || layoutId || '—'}
            readOnly
            placeholder="Configure pelo mapeamento"
          />
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            Webhook ativo
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={autoProcess} onChange={(e) => setAutoProcess(e.target.checked)} />
            Processar automaticamente ao criar novo lote do dia
          </label>
          <p className="text-xs text-gray-500">
            Propostas recebidas no mesmo dia são acrescentadas ao lote aberto do banco.
            Se esse lote já foi processado, um novo lote é criado para o restante do dia.
          </p>
        </div>

        <div className="card space-y-3">
          <h3 className="text-sm font-semibold text-gray-800">Payload de exemplo</h3>
          <textarea
            className="w-full h-48 text-xs font-mono border border-gray-200 rounded-lg p-3"
            value={payloadText}
            onChange={(e) => setPayloadText(e.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" onClick={() => setMappingOpen(true)}>
              Mapear campos
            </Button>
            {isEdit && (
              <Button size="sm" variant="secondary" onClick={handleTest} loading={testing}>
                <Play size={14} />
                Testar mapeamento
              </Button>
            )}
          </div>
          {testResult && (
            <div className="text-xs bg-green-50 border border-green-100 rounded-lg p-2 space-y-1">
              <p>{testResult.items_count} item(ns) → {testResult.rows_count} linha(s)</p>
              {testResult.sample_row && (
                <pre className="overflow-auto max-h-24">{JSON.stringify(testResult.sample_row, null, 2)}</pre>
              )}
            </div>
          )}
        </div>
      </div>

      {mappings.length > 0 && (
        <div className="card space-y-3">
          <h3 className="text-sm font-semibold text-gray-800">Mapeamentos ({mappings.length})</h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {mappings.map((mapping, idx) => (
              <div key={idx} className="border border-gray-100 rounded-lg p-2 space-y-2">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <Input
                    label="Campo origem (JSON path)"
                    value={mapping.source_path}
                    onChange={(e) => {
                      const next = [...mappings];
                      next[idx] = { ...next[idx], source_path: e.target.value };
                      setMappings(next);
                    }}
                  />
                  <Input
                    label="Campo do layout"
                    value={mapping.layout_field}
                    onChange={(e) => {
                      const next = [...mappings];
                      next[idx] = { ...next[idx], layout_field: e.target.value };
                      setMappings(next);
                    }}
                  />
                </div>
                <EtlMappingRuleFields
                  mapping={mapping}
                  fieldTransforms={fieldTransforms}
                  conditionOperators={conditionOperators}
                  onChange={(patch) => {
                    const next = [...mappings];
                    next[idx] = { ...next[idx], ...patch };
                    setMappings(next);
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {isEdit && deliveries.length > 0 && (
        <div className="card space-y-3">
          <h3 className="text-sm font-semibold text-gray-800">Últimas entregas</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="py-2 pr-3">Data</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Itens</th>
                  <th className="py-2 pr-3">Lote</th>
                  <th className="py-2 pr-3">Ação</th>
                  <th className="py-2">Erro</th>
                </tr>
              </thead>
              <tbody>
                {deliveries.map((d) => (
                  <tr key={d.id} className="border-b border-gray-50">
                    <td className="py-2 pr-3 whitespace-nowrap">{new Date(d.created_at).toLocaleString('pt-BR')}</td>
                    <td className="py-2 pr-3">
                      <Badge variant={d.status === 'failed' ? 'error' : d.status === 'batch_created' ? 'success' : 'default'}>
                        {d.status}
                      </Badge>
                    </td>
                    <td className="py-2 pr-3">{d.items_count}</td>
                    <td className="py-2 pr-3">
                      {d.batch_id ? (
                        <a href={`/proposals/batches/${d.batch_id}`} className="text-[var(--color-primary)] underline">
                          {d.batch_total_rows ?? '?'} linhas
                        </a>
                      ) : '—'}
                    </td>
                    <td className="py-2 pr-3 text-gray-600">
                      {d.batch_created ? 'Novo lote' : d.status === 'appended' ? 'Acrescentou' : '—'}
                    </td>
                    <td className="py-2 text-red-600">{d.error_message || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <EtlFieldMappingModal
        open={mappingOpen}
        onClose={() => setMappingOpen(false)}
        sampleItem={sampleItem}
        itemsPath={itemsPath}
        modelFields={modelFields}
        initialMappings={mappings}
        defaultBankId={bankId}
        defaultLayoutName={layoutName || `${name || 'Webhook'} layout`}
        onApply={applyMappingResult}
      />
    </div>
  );
}
