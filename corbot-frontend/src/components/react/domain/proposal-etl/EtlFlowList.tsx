import { useCallback, useEffect, useState } from 'react';
import { Plus, Sparkles } from 'lucide-react';
import { api, ApiError } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import type { ProposalEtlFlow } from '../../../../lib/api/types/etl';
import { Button } from '../../ui/Button';
import { PageHeader } from '../../ui/PageHeader';
import { Badge } from '../../ui/Badge';
import { DataTable, type Column } from '../../ui/DataTable';
import { formatDate } from '../../../../lib/utils/format';
import { EtlGenerateFromDocModal } from './EtlGenerateFromDocModal';

const statusVariant: Record<string, 'success' | 'warning' | 'error' | 'default'> = {
  success: 'success',
  running: 'warning',
  failed: 'error',
};

const columns: Column<Record<string, unknown>>[] = [
  { key: 'name', header: 'Nome', sortable: true },
  { key: 'bank_name', header: 'Banco' },
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
    key: 'last_run_status',
    header: 'Última execução',
    render: (item) => {
      const status = item.last_run_status as string | null;
      if (!status) return <span className="text-gray-400">—</span>;
      return <Badge variant={statusVariant[status] || 'default'}>{status}</Badge>;
    },
  },
  {
    key: 'updated_at',
    header: 'Atualizado',
    render: (item) => formatDate(item.updated_at as string),
  },
];

export function EtlFlowList() {
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [generateOpen, setGenerateOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<ProposalEtlFlow[]>(ENDPOINTS.PROPOSAL_ETL_CONFIGS);
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

  async function handleCreate() {
    setCreating(true);
    setError(null);
    try {
      const flow = await api.post<ProposalEtlFlow>(ENDPOINTS.PROPOSAL_ETL_CONFIGS, {
        name: `Fluxo ETL ${new Date().toLocaleDateString('pt-BR')}`,
      });
      window.location.href = `/proposal-etl/${flow.id}`;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao criar fluxo.');
      setCreating(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="ETL de Propostas"
        subtitle="Configure fluxos visuais para importar propostas via API bancária."
        actions={
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" icon={<Sparkles size={16} />} onClick={() => setGenerateOpen(true)}>
              Gerar com IA
            </Button>
            <Button size="sm" loading={creating} icon={<Plus size={16} />} onClick={handleCreate}>
              Novo fluxo
            </Button>
          </div>
        }
      />

      {error && (
        <div className="mb-4 px-3 py-2 rounded-lg bg-red-50 text-red-700 text-sm">{error}</div>
      )}

      <DataTable
        columns={columns}
        data={data}
        loading={loading}
        onRowClick={(item) => {
          window.location.href = `/proposal-etl/${item.id}`;
        }}
        emptyMessage="Nenhum fluxo ETL configurado."
      />

      <EtlGenerateFromDocModal open={generateOpen} onClose={() => setGenerateOpen(false)} />
    </div>
  );
}
