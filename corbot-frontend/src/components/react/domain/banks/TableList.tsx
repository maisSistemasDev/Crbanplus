import { useState } from 'react';
import { CrudPage } from '../shared/CrudPage';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { API_URL } from '../../../../lib/api/client';
import { Badge } from '../../ui/Badge';
import { Button } from '../../ui/Button';
import { TableCSVImport } from './TableCSVImport';
import { TableRangesForm } from './TableRangesForm';
import { Upload, Download } from 'lucide-react';
import type { Column } from '../../ui/DataTable';
import toast from 'react-hot-toast';

interface CommissionRange {
  min_value: string | number;
  max_value: string | number;
  commission_rate: string | number;
}

const columns: Column<Record<string, unknown>>[] = [
  { key: 'name_in_bank', header: 'Nome no Banco', sortable: true },
  { key: 'bank_name', header: 'Banco', sortable: true },
  { key: 'agreement_name', header: 'Convênio', sortable: true },
  {
    key: 'commission_ranges',
    header: 'Faixas',
    render: (item) => {
      const ranges = item.commission_ranges as CommissionRange[] | undefined;
      if (!ranges || ranges.length === 0) return <span className="text-gray-400 text-xs">Sem faixas</span>;
      return (
        <div className="flex flex-col gap-0.5">
          {ranges.map((r, i) => (
            <span key={i} className="text-xs text-gray-700">
              R${Number(r.min_value).toLocaleString('pt-BR', { minimumFractionDigits: 2 })} – R${Number(r.max_value).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}: <strong>{r.commission_rate}%</strong>
            </span>
          ))}
        </div>
      );
    },
  },
  {
    key: 'is_active',
    header: 'Status',
    render: (item) => (
      <Badge variant={item.is_active ? 'success' : 'error'}>
        {item.is_active ? 'Ativa' : 'Inativa'}
      </Badge>
    ),
  },
];

export function TableList() {
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  async function handleExportCSV() {
    try {
      const tokens = localStorage.getItem('tokens');
      const accessToken = tokens ? JSON.parse(tokens).access : '';
      
      const response = await fetch(`${API_URL}${ENDPOINTS.TABLES_EXPORT_CSV}`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });
      
      if (!response.ok) throw new Error('Erro ao exportar');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tabelas_${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('Tabelas exportadas com sucesso!');
    } catch (error) {
      toast.error('Erro ao exportar tabelas');
    }
  }

  function handleImportSuccess() {
    setRefreshKey((prev) => prev + 1);
    setImportModalOpen(false);
  }

  const customActions = (
    <div className="flex gap-2">
      <Button variant="secondary" onClick={handleExportCSV} size="sm">
        <Download size={16} />
        Exportar CSV
      </Button>
      <Button variant="secondary" onClick={() => setImportModalOpen(true)} size="sm">
        <Upload size={16} />
        Importar CSV
      </Button>
    </div>
  );

  return (
    <>
      <CrudPage
        key={refreshKey}
        title="Tabelas"
        endpoint={ENDPOINTS.TABLES}
        formFieldsEndpoint={ENDPOINTS.FORM_FIELDS_TABLES}
        columns={columns}
        createLabel="Nova Tabela"
        searchPlaceholder="Buscar tabela..."
        customActions={customActions}
        selectable
        bulkDeleteEndpoint={ENDPOINTS.TABLES_BULK_DELETE}
        renderForm={({ item, onSubmit, onClose, saving }) => (
          <TableRangesForm
            item={item}
            onSubmit={onSubmit}
            onClose={onClose}
            saving={saving}
          />
        )}
      />
      
      <TableCSVImport
        isOpen={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        onSuccess={handleImportSuccess}
      />
    </>
  );
}
