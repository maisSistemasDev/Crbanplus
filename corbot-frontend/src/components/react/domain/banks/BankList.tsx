import { useState } from 'react';
import { CrudPage } from '../shared/CrudPage';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Badge } from '../../ui/Badge';
import { Button } from '../../ui/Button';
import { BankCSVImport } from './BankCSVImport';
import { Upload } from 'lucide-react';
import type { Column } from '../../ui/DataTable';

const columns: Column<Record<string, unknown>>[] = [
  {
    key: 'name',
    header: 'Nome',
    sortable: true,
    render: (item) => (
      <div className="flex items-center gap-3">
        {item.logo && (
          <img src={item.logo as string} alt="" className="h-8 w-8 rounded object-contain" />
        )}
        <span className="font-medium text-gray-900">{item.name as string}</span>
      </div>
    ),
  },
  { key: 'website', header: 'Website' },
  {
    key: 'is_active',
    header: 'Status',
    render: (item) => (
      <Badge variant={item.is_active ? 'success' : 'error'}>
        {item.is_active ? 'Ativo' : 'Inativo'}
      </Badge>
    ),
  },
];

export function BankList() {
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const customActions = (
    <Button variant="secondary" onClick={() => setImportModalOpen(true)} size="sm">
      <Upload size={16} />
      Importar CSV
    </Button>
  );

  return (
    <>
      <CrudPage
        key={refreshKey}
        title="Bancos"
        endpoint={ENDPOINTS.BANKS}
        formFieldsEndpoint={ENDPOINTS.FORM_FIELDS_BANKS}
        columns={columns}
        createLabel="Novo Banco"
        searchPlaceholder="Buscar banco..."
        customActions={customActions}
      />
      <BankCSVImport
        isOpen={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        onSuccess={() => { setRefreshKey((k) => k + 1); setImportModalOpen(false); }}
      />
    </>
  );
}
