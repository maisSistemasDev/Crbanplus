import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  type Connection,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import clsx from 'clsx';
import { Play, Save, FlaskConical, ArrowLeft, Trash2, Terminal } from 'lucide-react';
import { api, ApiError } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import type {
  EtlExecutionLogEntry,
  EtlFlowDefinition,
  EtlFlowNodeData,
  EtlMappingApplyResult,
  EtlMetaAuthType,
  EtlMetaNodeType,
  ProposalEtlFlow,
  ProposalEtlRun,
} from '../../../../lib/api/types/etl';
import type { ModelField } from '../../../../lib/api/types';
import { Button } from '../../ui/Button';
import { Input } from '../../ui/Input';
import { PageHeader } from '../../ui/PageHeader';
import { SearchSelect } from '../../ui/SearchSelect';
import { EtlFieldMappingModal } from './EtlFieldMappingModal';
import { EtlBankProfilePanel } from './EtlBankProfilePanel';
import { EtlSharedAuthPanel } from './EtlSharedAuthPanel';
import { EtlMappingRuleFields } from './EtlMappingRuleFields';
import { EtlScheduleConfig } from './EtlScheduleConfig';
import { EtlExecutionConsole } from './EtlExecutionConsole';
import { EtlVariableExtractionsSection } from './EtlVariableExtractionsSection';
import { extractSampleFromTestOutputs } from '../../../../lib/etl/jsonPath';
import { numField, parseNumField, strField } from './etlFormHelpers';

const NODE_COLORS: Record<string, string> = {
  schedule_trigger: 'border-violet-400 bg-violet-50',
  http_request: 'border-blue-400 bg-blue-50',
  paginate_http: 'border-indigo-400 bg-indigo-50',
  extract_items: 'border-amber-400 bg-amber-50',
  fetch_item_details: 'border-cyan-400 bg-cyan-50',
  map_fields: 'border-emerald-400 bg-emerald-50',
  create_batch: 'border-rose-400 bg-rose-50',
};

function EtlFlowNode({ data, selected }: { data: EtlFlowNodeData; selected?: boolean }) {
  const nodeType = data.nodeType || 'unknown';
  return (
    <div
      className={clsx(
        'min-w-[160px] rounded-lg border-2 px-3 py-2 shadow-sm',
        NODE_COLORS[nodeType] || 'border-gray-300 bg-white',
        selected && 'ring-2 ring-[var(--color-primary)]',
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-gray-400" />
      <p className="text-xs font-semibold text-gray-800">{data.label || nodeType}</p>
      <p className="text-[10px] text-gray-500 uppercase tracking-wide">{nodeType.replace(/_/g, ' ')}</p>
      <Handle type="source" position={Position.Right} className="!bg-gray-400" />
    </div>
  );
}

const nodeTypes = { etlNode: EtlFlowNode };

const DATE_FORMAT_OPTIONS = [
  { value: '%Y-%m-%d', label: '2026-06-08 (ISO)' },
  { value: '%d/%m/%Y', label: '08/06/2026 (BR)' },
  { value: '%Y-%m-%dT00:00:00', label: 'ISO com hora 00:00:00' },
];

const MERGE_MODE_OPTIONS = [
  { value: 'merge', label: 'Mesclar campos no item (nível raiz)' },
  { value: 'nest', label: 'Guardar em sub-objeto (ex: partner)' },
  { value: 'prefix', label: 'Mesclar com prefixo (ex: partner_)' },
  { value: 'extract', label: 'Somente extrair variáveis (sem mesclar tudo)' },
];

const HTTP_METHOD_OPTIONS = [
  { value: 'GET', label: 'GET' },
  { value: 'POST', label: 'POST' },
];

const PARAM_LOCATION_OPTIONS = [
  { value: 'query', label: 'Query string (?page=1)' },
  { value: 'body', label: 'Corpo JSON (POST)' },
];

function toReactFlowNodes(definition: EtlFlowDefinition): Node[] {
  return (definition.nodes || []).map((n) => ({
    id: n.id,
    type: 'etlNode',
    position: n.position,
    data: { ...n.data, nodeType: n.type, label: n.data?.label || n.type },
  }));
}

function toReactFlowEdges(definition: EtlFlowDefinition): Edge[] {
  return (definition.edges || []).map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
  }));
}

function fromReactFlow(nodes: Node[], edges: Edge[]): EtlFlowDefinition {
  return {
    nodes: nodes.map((n) => {
      const raw = { ...(n.data as EtlFlowNodeData) };
      const nodeType = raw.nodeType || 'unknown';
      delete raw.nodeType;
      return {
        id: n.id,
        type: nodeType,
        position: n.position,
        data: raw,
      };
    }),
    edges: edges.map((e) => ({ id: e.id, source: e.source, target: e.target })),
  };
}

function newNodeId(type: string) {
  return `${type}-${Date.now().toString(36)}`;
}

function authDefaultsForType(authTypeId: string, authTypes: EtlMetaAuthType[]): Record<string, string> {
  const authType = authTypes.find((a) => a.id === authTypeId);
  if (!authType) return {};
  return Object.fromEntries(
    authType.fields
      .filter((f) => f.default)
      .map((f) => [f.name, f.default as string]),
  );
}

function resolveAuthConfig(
  authType: string | undefined,
  authConfig: Record<string, string> | undefined,
  authTypes: EtlMetaAuthType[],
): Record<string, string> {
  const defaults = authDefaultsForType(authType || 'none', authTypes);
  const cfg = { ...(authConfig || {}) };
  for (const [key, value] of Object.entries(defaults)) {
    if (cfg[key] === undefined) {
      cfg[key] = value;
    }
  }
  return cfg;
}

function normalizeFlowNodes(nodes: Node[], authTypes: EtlMetaAuthType[]): Node[] {
  return nodes.map((n) => {
    const data = n.data as EtlFlowNodeData;
    const isHttp =
      data.nodeType === 'http_request'
      || data.nodeType === 'paginate_http'
      || data.nodeType === 'fetch_item_details';
    if (!isHttp || !data.auth_type || data.auth_type === 'none') {
      return n;
    }
    return {
      ...n,
      data: {
        ...data,
        auth_config: resolveAuthConfig(data.auth_type, data.auth_config as Record<string, string>, authTypes),
      },
    };
  });
}

function newParamRow(name = '', value = ''): { id: string; name: string; value: string } {
  return { id: `param-${Math.random().toString(36).slice(2, 9)}`, name, value };
}

function paramsToRows(params: Record<string, string>) {
  return Object.entries(params).map(([name, value]) => newParamRow(name, value));
}

function rowsToParams(rows: { name: string; value: string }[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const row of rows) {
    if (row.name.trim()) out[row.name] = row.value;
  }
  return out;
}

function RequestParamsSection({
  data,
  patch,
  nodeId,
}: {
  data: EtlFlowNodeData;
  patch: (partial: Partial<EtlFlowNodeData>) => void;
  nodeId: string;
}) {
  const queryParams = (data.query_params as Record<string, string> | undefined) || {};
  const [rows, setRows] = useState(() => paramsToRows(queryParams));

  useEffect(() => {
    setRows(paramsToRows(queryParams));
  }, [nodeId]);

  const commitRows = useCallback(
    (nextRows: { id: string; name: string; value: string }[]) => {
      setRows(nextRows);
      patch({ query_params: rowsToParams(nextRows) });
    },
    [patch],
  );

  function applyParamsObject(obj: Record<string, string>) {
    commitRows(paramsToRows(obj));
  }

  return (
    <div className="space-y-2 border-t border-gray-100 pt-3 mt-2">
      <p className="text-xs font-medium text-gray-700">Parâmetros e datas dinâmicas</p>
      <p className="text-xs text-gray-500">
        Use <code className="bg-gray-100 px-1 rounded">d</code> (hoje),{' '}
        <code className="bg-gray-100 px-1 rounded">d-7</code> (7 dias atrás),{' '}
        <code className="bg-gray-100 px-1 rounded">d-1</code> (ontem). Na URL:{' '}
        <code className="bg-gray-100 px-1 rounded">{'?start={d-7}&end={d-1}'}</code>
      </p>
      <label className="block text-xs font-medium text-gray-600 mb-1">Formato da data</label>
      <SearchSelect
        value={(data.date_format as string) || '%Y-%m-%d'}
        options={DATE_FORMAT_OPTIONS}
        onChange={(e) => patch({ date_format: e.target.value })}
      />
      <Input
        label="Fuso horário"
        value={strField(data.date_timezone)}
        onChange={(e) => patch({ date_timezone: e.target.value })}
        placeholder="America/Sao_Paulo"
      />
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="secondary"
          type="button"
          onClick={() =>
            applyParamsObject({
              ...rowsToParams(rows),
              start_date: 'd-7',
              end_date: 'd-1',
            })
          }
        >
          Preset: últimos 7 dias
        </Button>
        <Button
          size="sm"
          variant="secondary"
          type="button"
          onClick={() =>
            applyParamsObject({
              ...rowsToParams(rows),
              start_date: 'd-1',
              end_date: 'd-1',
            })
          }
        >
          Preset: ontem
        </Button>
      </div>
      {rows.map((row) => (
        <div key={row.id} className="flex gap-2 items-end">
          <div className="flex-1">
            <Input
              label="Parâmetro"
              value={row.name}
              onChange={(e) => {
                commitRows(
                  rows.map((r) => (r.id === row.id ? { ...r, name: e.target.value } : r)),
                );
              }}
            />
          </div>
          <div className="flex-1">
            <Input
              label="Valor"
              value={row.value}
              onChange={(e) => {
                commitRows(
                  rows.map((r) => (r.id === row.id ? { ...r, value: e.target.value } : r)),
                );
              }}
              placeholder="d-7"
            />
          </div>
          <button
            type="button"
            className="text-xs text-red-600 hover:underline pb-2"
            onClick={() => commitRows(rows.filter((r) => r.id !== row.id))}
          >
            Remover
          </button>
        </div>
      ))}
      <Button
        size="sm"
        variant="secondary"
        type="button"
        onClick={() => commitRows([...rows, newParamRow(`param_${rows.length + 1}`, '')])}
      >
        Adicionar parâmetro
      </Button>
    </div>
  );
}

interface NodeConfigPanelProps {
  node: Node | null;
  authTypes: EtlMetaAuthType[];
  paginationModes: { id: string; label: string }[];
  fieldTransforms: { id: string; label: string }[];
  conditionOperators: { id: string; label: string }[];
  modelFields: ModelField[];
  sharedAuthEnabled: boolean;
  onChange: (nodeId: string, data: EtlFlowNodeData) => void;
  onDelete: (nodeId: string) => void;
}

function NodeConfigPanel({
  node,
  authTypes,
  paginationModes,
  fieldTransforms,
  conditionOperators,
  modelFields,
  sharedAuthEnabled,
  onChange,
  onDelete,
}: NodeConfigPanelProps) {
  if (!node) {
    return (
      <div className="p-4 text-sm text-gray-500">
        Selecione um nó no canvas para configurar.
      </div>
    );
  }

  const data = node.data as EtlFlowNodeData;
  const nodeType = data.nodeType || '';

  function patch(partial: Partial<EtlFlowNodeData>) {
    onChange(node.id, { ...data, ...partial });
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">{data.label || nodeType}</h3>
          <p className="text-xs text-gray-500">{nodeType.replace(/_/g, ' ')}</p>
        </div>
        <Button
          size="sm"
          variant="danger"
          icon={<Trash2 size={14} />}
          onClick={() => onDelete(node.id)}
          title="Excluir nó (Delete)"
        >
          Excluir
        </Button>
      </div>

      <Input
        label="Rótulo"
        value={data.label || ''}
        onChange={(e) => patch({ label: e.target.value })}
      />

      {nodeType === 'schedule_trigger' && (
        <EtlScheduleConfig data={data} onChange={(partial) => patch(partial)} />
      )}

      {(nodeType === 'http_request' || nodeType === 'paginate_http' || nodeType === 'fetch_item_details') && (
        <>
          {nodeType === 'fetch_item_details' ? (
            <>
              <Input
                label="URL template"
                value={(data.url_template as string) || ''}
                onChange={(e) => patch({ url_template: e.target.value })}
                placeholder="https://api.../propostas/{id}"
              />
              <Input
                label="Campo ID no item"
                value={strField(data.id_field)}
                onChange={(e) => patch({ id_field: e.target.value })}
                placeholder="id"
              />
              <p className="text-xs text-gray-500">
                Use {'{nome_do_campo}'} na URL. Ex: {'{proposal_id}'} se o item tiver proposal_id.
              </p>
              <Input
                label="JSON Path do detalhe (opcional)"
                value={(data.detail_path as string) || ''}
                onChange={(e) => patch({ detail_path: e.target.value })}
                placeholder="$.data"
              />
              <label className="block text-xs font-medium text-gray-600 mb-1">Mesclar resposta</label>
              <SearchSelect
                value={(data.merge_mode as string) || 'merge'}
                options={MERGE_MODE_OPTIONS}
                onChange={(e) => patch({ merge_mode: e.target.value })}
              />
              <EtlVariableExtractionsSection
                nodeId={node.id}
                extractions={data.variable_extractions as { name: string; path: string }[] | undefined}
                onChange={(variable_extractions) => patch({ variable_extractions })}
              />
              {(data.merge_mode as string) === 'nest' && (
                <Input
                  label="Chave do sub-objeto"
                  value={strField(data.merge_key)}
                  onChange={(e) => patch({ merge_key: e.target.value })}
                  placeholder="partner"
                />
              )}
              {(data.merge_mode as string) === 'prefix' && (
                <Input
                  label="Prefixo dos campos"
                  value={(data.merge_prefix as string) || ''}
                  onChange={(e) => patch({ merge_prefix: e.target.value })}
                  placeholder="partner"
                />
              )}
              <div className="text-xs text-gray-500 bg-blue-50 rounded-lg p-2 space-y-1">
                <p className="font-medium text-blue-800">Fluxo com detalhe + partner</p>
                <p>1. Lista → 2. Detalhar proposta ({'{proposal_uuid}'}, path $.data, mesclar) →</p>
                <p>3. Detalhar partner ({'{partner_uuid}'}, path $.data, nest em &quot;partner&quot;) →</p>
                <p>4. Ou use &quot;Somente extrair variáveis&quot;: user_uuid → user_uuid, partner → partners[0]</p>
                <p>5. Testar o último nó e mapear (customer.cpf, loan.requested_amount, partner.name…)</p>
              </div>
              <Input
                label="Delay entre chamadas (ms)"
                type="number"
                value={numField(data.delay_ms)}
                onChange={(e) => patch({ delay_ms: parseNumField(e.target.value) })}
                placeholder="0"
              />
            </>
          ) : (
            <Input
              label="URL"
              value={data.url || ''}
              onChange={(e) => patch({ url: e.target.value })}
              placeholder="https://api.banco.com/propostas"
            />
          )}
          <label className="block text-xs font-medium text-gray-600 mb-1">Método</label>
          <SearchSelect
            value={data.method || 'GET'}
            options={HTTP_METHOD_OPTIONS}
            onChange={(e) => patch({ method: e.target.value })}
          />
          {sharedAuthEnabled && (
            <label className="flex items-center gap-2 text-xs text-gray-700 rounded-lg border border-indigo-100 bg-indigo-50 px-3 py-2 mb-2">
              <input
                type="checkbox"
                checked={data.use_shared_auth !== false}
                onChange={(e) => patch({ use_shared_auth: e.target.checked })}
              />
              Usar autenticação compartilhada do fluxo
            </label>
          )}
          {(!sharedAuthEnabled || data.use_shared_auth === false) && (
            <>
              <label className="block text-xs font-medium text-gray-600 mb-1">Autenticação do nó</label>
              <SearchSelect
                value={data.auth_type || 'none'}
                options={authTypes.map((a) => ({ value: a.id, label: a.label }))}
                onChange={(e) => {
                  const authType = e.target.value;
                  patch({
                    auth_type: authType,
                    auth_config: authDefaultsForType(authType, authTypes),
                  });
                }}
              />
              {authTypes
                .find((a) => a.id === (data.auth_type || 'none'))
                ?.fields.map((field) => {
                  const rawCfg = (data.auth_config as Record<string, string>) || {};
                  return (
                  <Input
                    key={field.name}
                    label={field.label}
                    type={field.type === 'password' ? 'password' : 'text'}
                    value={rawCfg[field.name] ?? ''}
                    placeholder={field.default ? String(field.default) : undefined}
                    onChange={(e) =>
                      patch({
                        auth_config: { ...rawCfg, [field.name]: e.target.value },
                      })
                    }
                  />
                  );
                })}
            </>
          )}
          <RequestParamsSection data={data} patch={patch} nodeId={node.id} />
        </>
      )}

      {nodeType === 'paginate_http' && (
        <>
          <p className="text-xs text-gray-500">
            Busca todas as páginas automaticamente e agrega os itens. Pode ir direto para Mapear campos.
          </p>
          <label className="block text-xs font-medium text-gray-600 mb-1">Modo de paginação</label>
          <SearchSelect
            value={(data.pagination_mode as string) || 'page'}
            options={paginationModes.map((m) => ({ value: m.id, label: m.label }))}
            onChange={(e) => patch({ pagination_mode: e.target.value })}
          />
          <label className="block text-xs font-medium text-gray-600 mb-1">Onde enviar parâmetros</label>
          <SearchSelect
            value={(data.param_location as string) || 'query'}
            options={PARAM_LOCATION_OPTIONS}
            onChange={(e) => patch({ param_location: e.target.value })}
          />
          <Input
            label="JSON Path dos itens (por página)"
            value={strField(data.items_path)}
            onChange={(e) => patch({ items_path: e.target.value })}
            placeholder="$.content"
          />
          <Input
            label="Máximo de páginas"
            type="number"
            value={numField(data.max_pages)}
            onChange={(e) => patch({ max_pages: parseNumField(e.target.value) })}
            placeholder="100"
          />
          <Input
            label="Itens por página (page size)"
            type="number"
            value={numField(data.page_size)}
            onChange={(e) => patch({ page_size: parseNumField(e.target.value) })}
            placeholder="20"
          />
          {((data.pagination_mode as string) || 'page') === 'page' && (
            <>
              <Input
                label="Nome do parâmetro de página"
                value={strField(data.page_param)}
                onChange={(e) => patch({ page_param: e.target.value })}
                placeholder="page"
              />
              <Input
                label="Página inicial"
                type="number"
                value={numField(data.page_start)}
                onChange={(e) => patch({ page_start: parseNumField(e.target.value) })}
                placeholder="0"
              />
              <Input
                label="Nome do parâmetro de tamanho (opcional)"
                value={strField(data.page_size_param)}
                onChange={(e) => patch({ page_size_param: e.target.value })}
                placeholder="size"
              />
            </>
          )}
          {((data.pagination_mode as string) || 'page') === 'offset' && (
            <>
              <Input
                label="Parâmetro offset"
                value={strField(data.offset_param)}
                onChange={(e) => patch({ offset_param: e.target.value })}
                placeholder="offset"
              />
              <Input
                label="Parâmetro limit"
                value={strField(data.limit_param)}
                onChange={(e) => patch({ limit_param: e.target.value })}
                placeholder="limit"
              />
              <Input
                label="Offset inicial"
                type="number"
                value={numField(data.offset_start)}
                onChange={(e) => patch({ offset_start: parseNumField(e.target.value) })}
                placeholder="0"
              />
            </>
          )}
          {((data.pagination_mode as string) || 'page') === 'cursor' && (
            <>
              <Input
                label="Parâmetro cursor"
                value={strField(data.cursor_param)}
                onChange={(e) => patch({ cursor_param: e.target.value })}
                placeholder="cursor"
              />
              <Input
                label="JSON Path do próximo cursor"
                value={strField(data.cursor_path)}
                onChange={(e) => patch({ cursor_path: e.target.value })}
                placeholder="$.meta.next_cursor"
              />
            </>
          )}
          {((data.pagination_mode as string) || 'page') === 'next_url' && (
            <Input
              label="JSON Path da próxima URL"
              value={strField(data.next_url_path)}
              onChange={(e) => patch({ next_url_path: e.target.value })}
              placeholder="$.links.next"
            />
          )}
          <Input
            label="JSON Path has_more (opcional)"
            value={(data.has_more_path as string) || ''}
            onChange={(e) => patch({ has_more_path: e.target.value })}
            placeholder="$.has_more"
          />
          <Input
            label="JSON Path última página (opcional)"
            value={(data.last_path as string) || ''}
            onChange={(e) => patch({ last_path: e.target.value })}
            placeholder="$.last (Spring — para quando last=true)"
          />
          <p className="text-xs text-gray-500">
            Resposta Spring/Unnotech traz <code className="bg-gray-100 px-1 rounded">last</code> e{' '}
            <code className="bg-gray-100 px-1 rounded">number</code> no JSON — isso é só metadado.
            Na requisição use parâmetro <code className="bg-gray-100 px-1 rounded">page</code> e{' '}
            <code className="bg-gray-100 px-1 rounded">size</code> (página inicial geralmente <code className="bg-gray-100 px-1 rounded">0</code>).
          </p>
          <Button
            size="sm"
            variant="secondary"
            type="button"
            onClick={() =>
              patch({
                pagination_mode: 'page',
                items_path: '$.content',
                page_param: 'page',
                page_size_param: 'size',
                page_start: 0,
                page_size: 20,
                stop_when_partial: false,
                last_path: '$.last',
              })
            }
          >
            Preset: Spring / Unnotech (salve como perfil do banco depois)
          </Button>
          <label className="flex items-center gap-2 text-xs text-gray-600">
            <input
              type="checkbox"
              checked={Boolean(data.stop_when_partial)}
              onChange={(e) => patch({ stop_when_partial: e.target.checked })}
            />
            Parar se a página vier incompleta (desligado para APIs com size fixo)
          </label>
        </>
      )}

      {nodeType === 'extract_items' && (
        <Input
          label="JSON Path da lista"
          value={strField(data.items_path)}
          onChange={(e) => patch({ items_path: e.target.value })}
          placeholder="$.content"
        />
      )}

      {nodeType === 'map_fields' && (
        <div className="space-y-3">
          <p className="text-xs text-gray-500">
            Use &quot;Testar nó&quot; e depois &quot;Mapear campos&quot; para criar o layout a partir do JSON da API.
          </p>
          {(data.mappings || []).length === 0 ? (
            <p className="text-xs text-amber-600">Nenhum mapeamento configurado.</p>
          ) : (
            (data.mappings || []).map((mapping, idx) => (
              <div key={idx} className="border border-gray-100 rounded-lg p-2 space-y-2">
                <Input
                  label="Campo origem (JSON path)"
                  value={mapping.source_path}
                  onChange={(e) => {
                    const mappings = [...(data.mappings || [])];
                    mappings[idx] = { ...mappings[idx], source_path: e.target.value };
                    patch({ mappings });
                  }}
                />
                <label className="block text-xs font-medium text-gray-600">Campo do sistema</label>
                <SearchSelect
                  placeholder="Selecione..."
                  allowEmpty
                  value={mapping.layout_field}
                  options={modelFields.map((f) => ({ value: f.name, label: f.verbose_name }))}
                  onChange={(e) => {
                    const mappings = [...(data.mappings || [])];
                    mappings[idx] = { ...mappings[idx], layout_field: e.target.value };
                    patch({ mappings });
                  }}
                />
                <EtlMappingRuleFields
                  mapping={mapping}
                  fieldTransforms={fieldTransforms}
                  conditionOperators={conditionOperators}
                  onChange={(rulePatch) => {
                    const mappings = [...(data.mappings || [])];
                    mappings[idx] = { ...mappings[idx], ...rulePatch };
                    patch({ mappings });
                  }}
                />
                <button
                  type="button"
                  className="text-xs text-red-600 hover:underline"
                  onClick={() => {
                    const mappings = (data.mappings || []).filter((_, i) => i !== idx);
                    patch({ mappings });
                  }}
                >
                  Remover
                </button>
              </div>
            ))
          )}
        </div>
      )}

      {nodeType === 'create_batch' && (
        <>
          <p className="text-xs text-gray-500">
            O layout é criado automaticamente ao mapear os campos da API.
          </p>
          {data.layout_id ? (
            <div className="text-xs bg-green-50 text-green-800 rounded-lg p-2 space-y-1">
              <p><span className="font-medium">Layout:</span> {data.layout_name || data.layout_id}</p>
              <p className="text-green-700/80 font-mono text-[10px]">{data.layout_id}</p>
            </div>
          ) : (
            <p className="text-xs text-amber-600">Nenhum layout criado ainda. Teste um nó e mapeie os campos.</p>
          )}
        </>
      )}
    </div>
  );
}

export function EtlFlowEditor({ flowId }: { flowId: string }) {
  const [flow, setFlow] = useState<ProposalEtlFlow | null>(null);
  const [name, setName] = useState('');
  const [isActive, setIsActive] = useState(false);
  const [bankId, setBankId] = useState('');
  const [nodeTypesMeta, setNodeTypesMeta] = useState<EtlMetaNodeType[]>([]);
  const [authTypes, setAuthTypes] = useState<EtlMetaAuthType[]>([]);
  const [paginationModes, setPaginationModes] = useState<{ id: string; label: string }[]>([]);
  const [fieldTransforms, setFieldTransforms] = useState<{ id: string; label: string }[]>([]);
  const [conditionOperators, setConditionOperators] = useState<{ id: string; label: string }[]>([]);
  const [modelFields, setModelFields] = useState<ModelField[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testOutput, setTestOutput] = useState<Record<string, unknown> | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aiWarnings, setAiWarnings] = useState<string[]>([]);
  const [mappingModalOpen, setMappingModalOpen] = useState(false);
  const [mappingSample, setMappingSample] = useState<Record<string, unknown> | null>(null);
  const [mappingItemsPath, setMappingItemsPath] = useState('$.data');
  const [sharedAuthEnabled, setSharedAuthEnabled] = useState(false);
  const [sharedAuthType, setSharedAuthType] = useState('none');
  const [sharedAuthConfig, setSharedAuthConfig] = useState<Record<string, string>>({});
  const [consoleOpen, setConsoleOpen] = useState(false);
  const [consoleLogs, setConsoleLogs] = useState<EtlExecutionLogEntry[]>([]);
  const [consoleStatus, setConsoleStatus] = useState<'idle' | 'running' | 'success' | 'failed'>('idle');
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedNodeId) || null,
    [nodes, selectedNodeId],
  );

  const mapFieldsNode = useMemo(
    () => nodes.find((n) => (n.data as EtlFlowNodeData).nodeType === 'map_fields') || null,
    [nodes],
  );

  const mapFieldsInitialMappings = useMemo(
    () => (mapFieldsNode?.data as EtlFlowNodeData)?.mappings || [],
    [mapFieldsNode],
  );

  const loadModelFields = useCallback(async () => {
    try {
      const res = await api.get<{ model_fields: ModelField[] }>(ENDPOINTS.PROPOSAL_FIELDS);
      setModelFields(res.model_fields);
      return res.model_fields;
    } catch {
      setModelFields([]);
      return [];
    }
  }, []);

  async function openMappingModalFromOutputs(outputs: Record<string, unknown>, nodeId: string) {
    const flowNodes = nodes.map((n) => ({
      id: n.id,
      data: n.data as Record<string, unknown>,
    }));
    const flowEdges = edges.map((e) => ({ source: e.source, target: e.target }));
    const sample = extractSampleFromTestOutputs(outputs, nodeId, flowNodes, flowEdges);
    if (!sample) {
      setError('Não foi possível encontrar uma lista no resultado. Teste um nó que retorne dados (HTTP, Paginar, Extrair lista ou Detalhar itens).');
      return;
    }

    await loadModelFields();

    setMappingSample(sample.item);
    setMappingItemsPath(sample.itemsPath);
    setMappingModalOpen(true);
    setError(null);
  }

  function applyFieldMappings(result: EtlMappingApplyResult) {
    const mapNode = mapFieldsNode;
    if (!mapNode) {
      setError('Adicione um nó "Mapear campos" ao fluxo para aplicar o mapeamento.');
      return;
    }
    handleNodeDataChange(mapNode.id, {
      ...(mapNode.data as EtlFlowNodeData),
      mappings: result.mappings,
    });

    const batchNode = nodes.find((n) => (n.data as EtlFlowNodeData).nodeType === 'create_batch');
    if (batchNode) {
      handleNodeDataChange(batchNode.id, {
        ...(batchNode.data as EtlFlowNodeData),
        layout_id: result.layoutId,
        layout_name: result.layoutName,
        bank_id: result.bankId,
      });
    }

    const extractNode = nodes.find((n) => (n.data as EtlFlowNodeData).nodeType === 'extract_items');
    if (extractNode && result.itemsPath) {
      handleNodeDataChange(extractNode.id, {
        ...(extractNode.data as EtlFlowNodeData),
        items_path: result.itemsPath,
      });
    }

    if (result.bankId && !bankId) {
      setBankId(result.bankId);
    }

    setSelectedNodeId(mapNode.id);
    setMessage('Layout criado e mapeamento aplicado. Salve o fluxo.');
  }

  useEffect(() => {
    const key = `etl-warnings-${flowId}`;
    const raw = sessionStorage.getItem(key);
    if (raw) {
      try {
        setAiWarnings(JSON.parse(raw) as string[]);
      } catch {
        /* ignore */
      }
      sessionStorage.removeItem(key);
    }
  }, [flowId]);

  function applyFlowState(flowRes: ProposalEtlFlow) {
    setFlow(flowRes);
    setName(flowRes.name);
    setIsActive(flowRes.is_active);
    setBankId(flowRes.bank || '');
    setSharedAuthEnabled(Boolean(flowRes.shared_auth_enabled));
    setSharedAuthType(flowRes.shared_auth_type || 'none');
    setSharedAuthConfig(flowRes.shared_auth_config || {});
    const def = flowRes.flow_definition || { nodes: [], edges: [] };
    setNodes(toReactFlowNodes(def));
    setEdges(toReactFlowEdges(def));
  }

  const reloadFlow = useCallback(async () => {
    const flowRes = await api.get<ProposalEtlFlow>(ENDPOINTS.PROPOSAL_ETL_DETAIL(flowId));
    applyFlowState(flowRes);
  }, [flowId, setNodes, setEdges]);

  useEffect(() => {
    async function load() {
      try {
        const [flowRes, metaRes] = await Promise.all([
          api.get<ProposalEtlFlow>(ENDPOINTS.PROPOSAL_ETL_DETAIL(flowId)),
          api.get<{
            node_types: EtlMetaNodeType[];
            auth_types: EtlMetaAuthType[];
            pagination_modes: { id: string; label: string }[];
            field_transforms?: { id: string; label: string }[];
            condition_operators?: { id: string; label: string }[];
          }>(
            ENDPOINTS.PROPOSAL_ETL_META,
          ),
        ]);
        applyFlowState(flowRes);
        setNodeTypesMeta(metaRes.node_types);
        setAuthTypes(metaRes.auth_types);
        setPaginationModes(metaRes.pagination_modes || []);
        setFieldTransforms(metaRes.field_transforms || []);
        setConditionOperators(metaRes.condition_operators || []);
        loadModelFields();
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'Erro ao carregar fluxo.');
      }
    }
    load();
  }, [flowId, setNodes, setEdges, loadModelFields]);

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) =>
        addEdge({ ...connection, id: `e-${connection.source}-${connection.target}` }, eds),
      );
    },
    [setEdges],
  );

  const removeNodeById = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== nodeId));
      setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
      setSelectedNodeId((current) => (current === nodeId ? null : current));
    },
    [setNodes, setEdges],
  );

  const onNodesDelete = useCallback(
    (deleted: Node[]) => {
      const ids = new Set(deleted.map((n) => n.id));
      setEdges((eds) => eds.filter((e) => !ids.has(e.source) && !ids.has(e.target)));
      setSelectedNodeId((current) => (current && ids.has(current) ? null : current));
    },
    [setEdges],
  );

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== 'Delete' && e.key !== 'Backspace') return;
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if (!selectedNodeId) return;
      e.preventDefault();
      removeNodeById(selectedNodeId);
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [selectedNodeId, removeNodeById]);

  function handleNodeDataChange(nodeId: string, data: EtlFlowNodeData) {
    setNodes((nds) =>
      nds.map((n) => (n.id === nodeId ? { ...n, data } : n)),
    );
  }

  function addNode(type: string, label: string) {
    const id = newNodeId(type);
    const x = 80 + nodes.length * 40;
    const y = 120 + (nodes.length % 3) * 80;
    setNodes((nds) => [
      ...nds,
      {
        id,
        type: 'etlNode',
        position: { x, y },
        data: { nodeType: type, label },
      },
    ]);
    setSelectedNodeId(id);
  }

  async function handleSave(): Promise<boolean> {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const normalized = normalizeFlowNodes(nodes, authTypes);
      const flow_definition = fromReactFlow(normalized, edges);
      const updated = await api.patch<ProposalEtlFlow>(ENDPOINTS.PROPOSAL_ETL_DETAIL(flowId), {
        name,
        is_active: isActive,
        bank: bankId || null,
        flow_definition,
        shared_auth_enabled: sharedAuthEnabled,
        shared_auth_type: sharedAuthType,
        shared_auth_config: sharedAuthConfig,
      });
      setFlow(updated);
      setNodes(normalized);
      setMessage('Fluxo salvo.');
      return true;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao salvar.');
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function handleTestNode() {
    if (!selectedNodeId) {
      setError('Selecione um nó para testar.');
      return;
    }
    setTesting(true);
    setError(null);
    setTestOutput(null);
    setConsoleOpen(true);
    setConsoleStatus('running');
    setActiveRunId(null);
    setActiveBatchId(null);
    try {
      const saved = await handleSave();
      if (!saved) return;
      const res = await api.post<{
        node_id: string;
        outputs: Record<string, unknown>;
        execution_log?: EtlExecutionLogEntry[];
      }>(
        ENDPOINTS.PROPOSAL_ETL_TEST_NODE(flowId),
        { node_id: selectedNodeId },
      );
      setTestOutput(res.outputs);
      setConsoleLogs(res.execution_log || []);
      setConsoleStatus('success');
      setMessage(`Teste do nó concluído.`);
      await openMappingModalFromOutputs(res.outputs, selectedNodeId);
    } catch (err) {
      setConsoleStatus('failed');
      setError(err instanceof ApiError ? err.message : 'Erro no teste.');
    } finally {
      setTesting(false);
    }
  }

  async function handleRun() {
    setRunning(true);
    setError(null);
    setMessage(null);
    setConsoleOpen(true);
    setConsoleStatus('running');
    setConsoleLogs([]);
    setActiveRunId(null);
    setActiveBatchId(null);
    try {
      const saved = await handleSave();
      if (!saved) return;

      const res = await api.post<{
        run: ProposalEtlRun;
        status: string;
        message?: string;
      }>(ENDPOINTS.PROPOSAL_ETL_RUN(flowId));

      const runId = res.run.id;
      setActiveRunId(runId);
      setMessage('Execução iniciada em background…');

      const pollIntervalMs = 2500;
      const maxPolls = 360;
      for (let i = 0; i < maxPolls; i += 1) {
        await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
        const runStatus = await api.get<ProposalEtlRun>(ENDPOINTS.PROPOSAL_ETL_RUN_DETAIL(runId));

        if (runStatus.execution_log?.length) {
          setConsoleLogs(runStatus.execution_log);
        }

        if (runStatus.status === 'running') {
          setMessage(
            `Executando… ${runStatus.fetched_count ? `${runStatus.fetched_count} itens obtidos` : 'aguarde'}`,
          );
          continue;
        }

        if (runStatus.status === 'success') {
          setConsoleStatus('success');
          setActiveBatchId(runStatus.proposal_batch);
          setMessage(
            runStatus.proposal_batch
              ? `Lote criado (${runStatus.fetched_count} itens). Veja o console ou abra o lote.`
              : `Execução concluída (${runStatus.fetched_count} itens).`,
          );
          return;
        }

        if (runStatus.status === 'failed') {
          setConsoleStatus('failed');
          setError(runStatus.error_message || 'Execução ETL falhou.');
          return;
        }
      }

      setMessage('Execução ainda em andamento. Acompanhe pelo console.');
    } catch (err) {
      setConsoleStatus('failed');
      setError(err instanceof ApiError ? err.message : 'Erro na execução.');
    } finally {
      setRunning(false);
    }
  }

  if (!flow && !error) {
    return <div className="p-8 text-gray-500">Carregando editor...</div>;
  }

  return (
    <div className="flex flex-col h-[calc(100vh-var(--header-height,64px)-48px)] min-h-0 overflow-hidden">
      <div className="shrink-0">
      <PageHeader
        title={name || 'Editor ETL'}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <a href="/proposal-etl">
              <Button variant="ghost" size="sm" icon={<ArrowLeft size={16} />}>
                Voltar
              </Button>
            </a>
            <Button size="sm" variant="secondary" loading={testing} icon={<FlaskConical size={16} />} onClick={handleTestNode}>
              Testar nó
            </Button>
            <Button
              size="sm"
              variant="secondary"
              icon={<Terminal size={16} />}
              onClick={() => setConsoleOpen((v) => !v)}
            >
              Console
            </Button>
            <Button size="sm" loading={running} icon={<Play size={16} />} onClick={handleRun}>
              Executar
            </Button>
            <Button size="sm" loading={saving} icon={<Save size={16} />} onClick={handleSave}>
              Salvar
            </Button>
          </div>
        }
      />
      </div>

      {(message || error) && (
        <div className={clsx('mx-4 mb-2 px-3 py-2 rounded-lg text-sm shrink-0', error ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700')}>
          {error || message}
        </div>
      )}

      {aiWarnings.length > 0 && (
        <div className="mx-4 mb-2 px-3 py-2 rounded-lg text-sm bg-amber-50 text-amber-900 border border-amber-100 shrink-0">
          <p className="font-medium mb-1">Rascunho gerado — revise antes de executar:</p>
          <ul className="list-disc list-inside space-y-0.5 text-xs">
            {aiWarnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex flex-1 min-h-0 flex-col mx-4 mb-4 overflow-hidden rounded-xl border border-gray-200 bg-white">
        <div className="flex flex-1 min-h-0 overflow-hidden">
        <aside className="w-52 border-r border-gray-100 shrink-0 flex flex-col min-h-0 max-h-full">
          <div className="flex-1 min-h-[120px] overflow-y-auto p-3 space-y-2">
            <p className="text-xs font-semibold text-gray-500 uppercase">Nós</p>
            {nodeTypesMeta.map((nt) => (
              <button
                key={nt.id}
                type="button"
                onClick={() => addNode(nt.id, nt.label)}
                className="w-full text-left text-xs px-2 py-1.5 rounded-lg border border-gray-100 hover:bg-gray-50"
              >
                {nt.label}
              </button>
            ))}
            <p className="text-[10px] text-gray-400 pt-1">
              Clique no canvas e pressione Delete para excluir o nó selecionado.
            </p>
          </div>
          <div className="shrink-0 max-h-[min(340px,45vh)] overflow-y-auto border-t border-gray-100 p-3 space-y-2 bg-gray-50/50">
            <Input label="Nome" value={name} onChange={(e) => setName(e.target.value)} />
            <SearchSelect
              label="Banco"
              options_url={ENDPOINTS.BANKS}
              value={bankId}
              onChange={(e) => setBankId(e.target.value)}
            />
            <label className="flex items-center gap-2 text-xs text-gray-700 rounded-lg border border-gray-200 bg-white px-3 py-2">
              <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
              Fluxo ativo (agendamento)
            </label>
            <EtlSharedAuthPanel
              enabled={sharedAuthEnabled}
              authType={sharedAuthType}
              authConfig={sharedAuthConfig}
              authTypes={authTypes}
              onEnabledChange={setSharedAuthEnabled}
              onAuthTypeChange={(type, defaults) => {
                setSharedAuthType(type);
                setSharedAuthConfig(defaults);
              }}
              onAuthConfigChange={setSharedAuthConfig}
            />
            <EtlBankProfilePanel
              bankId={bankId}
              flowId={flowId}
              onProfileApplied={() => {
                reloadFlow().catch(() => setError('Erro ao recarregar fluxo após aplicar perfil.'));
              }}
            />
          </div>
        </aside>

        <div className="flex-1 min-h-0 min-w-0 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodesDelete={onNodesDelete}
            nodeTypes={nodeTypes}
            nodesDeletable
            edgesDeletable
            deleteKeyCode={['Delete', 'Backspace']}
            onNodeClick={(_, node) => setSelectedNodeId(node.id)}
            onPaneClick={() => setSelectedNodeId(null)}
            tabIndex={0}
            fitView
            style={{ width: '100%', height: '100%' }}
          >
            <Background gap={16} />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>

        <aside className="w-80 border-l border-gray-100 shrink-0 flex flex-col min-h-0 overflow-y-auto">
          <NodeConfigPanel
            node={selectedNode}
            authTypes={authTypes}
            paginationModes={paginationModes}
            fieldTransforms={fieldTransforms}
            conditionOperators={conditionOperators}
            modelFields={modelFields}
            sharedAuthEnabled={sharedAuthEnabled}
            onChange={handleNodeDataChange}
            onDelete={removeNodeById}
          />
          {testOutput && selectedNodeId && (
            <div className="border-t border-gray-100 p-3">
              <div className="flex items-center justify-between gap-2 mb-1">
                <p className="text-xs font-semibold text-gray-600">Resultado do teste</p>
                <Button
                  size="sm"
                  variant="secondary"
                  type="button"
                  onClick={() => openMappingModalFromOutputs(testOutput, selectedNodeId)}
                >
                  Mapear campos
                </Button>
              </div>
              <pre className="text-[10px] bg-gray-50 rounded p-2 overflow-auto max-h-40">
                {JSON.stringify(testOutput, null, 2)}
              </pre>
            </div>
          )}
        </aside>
        </div>
        <EtlExecutionConsole
          open={consoleOpen}
          onToggle={() => setConsoleOpen((v) => !v)}
          entries={consoleLogs}
          status={consoleStatus}
          runId={activeRunId}
          batchId={activeBatchId}
        />
      </div>

      {mappingSample && (
        <EtlFieldMappingModal
          open={mappingModalOpen}
          onClose={() => setMappingModalOpen(false)}
          sampleItem={mappingSample}
          itemsPath={mappingItemsPath}
          modelFields={modelFields}
          initialMappings={mapFieldsInitialMappings}
          defaultBankId={bankId}
          defaultLayoutName={name ? `${name} - API` : 'Layout API ETL'}
          onApply={applyFieldMappings}
        />
      )}
    </div>
  );
}
