export interface JsonLeafField {
  path: string;
  value: unknown;
  sample: string;
  type: string;
}

function inferType(value: unknown): string {
  if (value === null || value === undefined) return 'text';
  if (typeof value === 'boolean') return 'boolean';
  if (typeof value === 'number') return Number.isInteger(value) ? 'number' : 'decimal';
  if (typeof value === 'string') {
    if (/^\d{11}$/.test(value.replace(/\D/g, ''))) return 'cpf';
    if (/^\d{4}-\d{2}-\d{2}/.test(value)) return 'date';
    return 'text';
  }
  return 'text';
}

export function resolveJsonPath(data: unknown, path: string): unknown {
  if (!path || path === '$' || path === '') return data;
  let p = path.trim();
  if (p.startsWith('$.')) p = p.slice(2);
  else if (p.startsWith('$')) p = p.slice(1).replace(/^\./, '');

  let current: unknown = data;
  for (const part of p.split('.')) {
    if (!part || current === null || current === undefined) return undefined;
    if (typeof current === 'object' && !Array.isArray(current)) {
      current = (current as Record<string, unknown>)[part];
    } else if (Array.isArray(current) && /^\d+$/.test(part)) {
      current = current[Number(part)];
    } else {
      return undefined;
    }
  }
  return current;
}

export function flattenJsonLeaves(
  obj: unknown,
  prefix = '',
  maxDepth = 6,
): JsonLeafField[] {
  const out: JsonLeafField[] = [];

  function walk(value: unknown, path: string, depth: number) {
    if (depth > maxDepth) return;
    if (value === null || value === undefined) {
      out.push({ path, value, sample: '—', type: 'text' });
      return;
    }
    if (Array.isArray(value)) {
      if (value.length === 0) {
        out.push({ path, value, sample: '[]', type: 'text' });
        return;
      }
      walk(value[0], path ? `${path}.0` : '0', depth + 1);
      return;
    }
    if (typeof value === 'object') {
      const entries = Object.entries(value as Record<string, unknown>);
      if (entries.length === 0) {
        out.push({ path: path || '(raiz)', value, sample: '{}', type: 'text' });
        return;
      }
      for (const [key, child] of entries) {
        const childPath = path ? `${path}.${key}` : key;
        if (child !== null && typeof child === 'object' && !Array.isArray(child) && depth < maxDepth) {
          walk(child, childPath, depth + 1);
        } else {
          const sample = child === null || child === undefined
            ? '—'
            : String(child).slice(0, 80);
          out.push({
            path: childPath,
            value: child,
            sample,
            type: inferType(child),
          });
        }
      }
      return;
    }
    out.push({
      path: path || 'value',
      value,
      sample: String(value).slice(0, 80),
      type: inferType(value),
    });
  }

  walk(obj, prefix, 0);
  const seen = new Set<string>();
  return out.filter((f) => {
    if (seen.has(f.path)) return false;
    seen.add(f.path);
    return true;
  });
}

export function extractFirstListItem(
  output: Record<string, unknown>,
  itemsPath: string,
): Record<string, unknown> | null {
  if (Array.isArray(output.items) && output.items.length > 0) {
    const first = output.items[0];
    if (first && typeof first === 'object' && !Array.isArray(first)) {
      return first as Record<string, unknown>;
    }
    return { value: first };
  }

  const body = output.body ?? output;
  const list = resolveJsonPath(body, itemsPath);
  if (Array.isArray(list) && list.length > 0) {
    const first = list[0];
    if (first && typeof first === 'object' && !Array.isArray(first)) {
      return first as Record<string, unknown>;
    }
    return { value: first };
  }

  if (body && typeof body === 'object' && !Array.isArray(body)) {
    const dataContent = resolveJsonPath(body, 'data');
    if (dataContent && typeof dataContent === 'object' && !Array.isArray(dataContent)) {
      return dataContent as Record<string, unknown>;
    }
    return body as Record<string, unknown>;
  }

  return null;
}

export function resolveItemsPathForNode(
  nodeId: string,
  nodes: { id: string; data: Record<string, unknown> }[],
): string {
  const node = nodes.find((n) => n.id === nodeId);
  const nodeType = node?.data?.nodeType as string | undefined;
  if (nodeType === 'extract_items' || nodeType === 'paginate_http') {
    return (node?.data?.items_path as string) || '$.data';
  }
  const extract = nodes.find((n) => n.data?.nodeType === 'extract_items');
  if (extract?.data?.items_path) return String(extract.data.items_path);
  const paginate = nodes.find((n) => n.data?.nodeType === 'paginate_http');
  if (paginate?.data?.items_path) return String(paginate.data.items_path);
  return '$.data';
}

// Nós cuja saída não serve de amostra para mapeamento (rows já mapeadas,
// trigger sem dados, lote criado). Nesses casos buscamos o nó anterior.
const NON_SAMPLE_NODE_TYPES = new Set(['map_fields', 'create_batch', 'schedule_trigger']);

export function extractSampleFromTestOutputs(
  outputs: Record<string, unknown>,
  nodeId: string,
  nodes: { id: string; data: Record<string, unknown> }[],
  edges: { source: string; target: string }[] = [],
): { item: Record<string, unknown>; itemsPath: string } | null {
  const nodeById = new Map(nodes.map((n) => [n.id, n]));
  const visited = new Set<string>();
  let currentId: string | undefined = nodeId;

  // Caminha do nó testado para trás (upstream) até achar uma saída com itens.
  while (currentId && !visited.has(currentId)) {
    visited.add(currentId);
    const node = nodeById.get(currentId);
    const nodeType = node?.data?.nodeType as string | undefined;
    const out = outputs[currentId] as Record<string, unknown> | undefined;

    if (out && (!nodeType || !NON_SAMPLE_NODE_TYPES.has(nodeType))) {
      const itemsPath = resolveItemsPathForNode(currentId, nodes);
      const item = extractFirstListItem(out, itemsPath);
      if (item) return { item, itemsPath };
    }

    currentId = edges.find((e) => e.target === currentId)?.source;
  }

  // Fallback: qualquer saída com lista de items não vazia.
  for (const n of nodes) {
    const nodeType = n.data?.nodeType as string | undefined;
    if (nodeType && NON_SAMPLE_NODE_TYPES.has(nodeType)) continue;
    const out = outputs[n.id] as Record<string, unknown> | undefined;
    if (!out || !Array.isArray(out.items) || out.items.length === 0) continue;
    const itemsPath = resolveItemsPathForNode(n.id, nodes);
    const item = extractFirstListItem(out, itemsPath);
    if (item) return { item, itemsPath };
  }

  return null;
}
