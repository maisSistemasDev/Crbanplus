import { CrudPage } from '../shared/CrudPage';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { Badge } from '../../ui/Badge';
import type { Column } from '../../ui/DataTable';

const columns: Column<Record<string, unknown>>[] = [
  { key: 'name', header: 'Nome', sortable: true },
  { key: 'code', header: 'Codigo' },
  {
    key: 'description',
    header: 'Descricao',
    render: (item) => (
      <span className="text-gray-500 truncate max-w-xs block">
        {(item.description as string) || '-'}
      </span>
    ),
  },
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

export function AgreementList() {
  return (
    <CrudPage
      title="Convenios"
      endpoint={ENDPOINTS.AGREEMENTS}
      formFieldsEndpoint={ENDPOINTS.FORM_FIELDS_AGREEMENTS}
      columns={columns}
      createLabel="Novo Convenio"
      searchPlaceholder="Buscar convenio..."
    />
  );
}
