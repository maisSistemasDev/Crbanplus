import { useCallback, useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import type { WebhookEndpoint } from '../../../../lib/api/types/webhooks';
import { Button } from '../../ui/Button';
import { PageHeader } from '../../ui/PageHeader';
import { Badge } from '../../ui/Badge';
import { DataTable, type Column } from '../../ui/DataTable';
import { formatDate } from '../../../../lib/utils/format';

const columns: Column<Record<string, unknown>>[] = [
  { key: 'name', header: 'Nome', sortable: true },
  { key: 'bank_name', header: 'Banco' },
  { key: 'layout_name', header: 'Layout', render: (item) => (item.layout_name as string) || '—' },
  {
    key: 'is_active',
    header: 'Ativo',
    render: (item) => (
      <Badge variant={item.is_active ? 'success' : 'default'}>
        {item.is_active ? 'Sim' : 'Não'}
      </Badge>
    ),
  },
  {
    key: 'delivery_count',
    header: 'Entregas',
    render: (item) => String(item.delivery_count ?? 0),
  },
  {
    key: 'updated_at',
    header: 'Atualizado',
    render: (item) => formatDate(item.updated_at as string),
  },
];

export function WebhookList() {
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<WebhookEndpoint[]>(ENDPOINTS.WEBHOOKS);
      setData(res as unknown as Record<string, unknown>[]);
    } catch {
      setData([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div>
      <PageHeader
        title="Webhooks"
        subtitle="Receba propostas via POST JSON. Um lote aberto por banco/dia; após processado, novas propostas geram outro lote no mesmo dia."
        actions={
          <a href="/proposals/webhooks/create">
            <Button size="sm">
              <Plus size={16} />
              Novo webhook
            </Button>
          </a>
        }
      />

      <DataTable
        columns={columns}
        data={data}
        loading={loading}
        onRowClick={(item) => {
          window.location.href = `/proposals/webhooks/${(item as { id: string }).id}`;
        }}
        keyExtractor={(item) => (item as { id: string }).id}
        emptyMessage="Nenhum webhook cadastrado"
      />
    </div>
  );
}
