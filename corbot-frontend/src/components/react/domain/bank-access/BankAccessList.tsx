import { useState, useEffect } from 'react';
import { CrudPage } from '../shared/CrudPage';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { api } from '../../../../lib/api/client';
import { Badge } from '../../ui/Badge';
import { formatDate } from '../../../../lib/utils/format';
import type { Column } from '../../ui/DataTable';

const columns: Column<Record<string, unknown>>[] = [
  {
    key: 'bank_name',
    header: 'Banco',
    sortable: true,
  },
  {
    key: 'company_name',
    header: 'Empresa',
    sortable: true,
  },
  {
    key: 'user_name',
    header: 'Usuario',
  },
  {
    key: 'username',
    header: 'Login',
    render: (item) => (
      <span className="font-mono text-xs">{item.username as string}</span>
    ),
  },
  {
    key: 'last_access',
    header: 'Ultimo Acesso',
    render: (item) => item.last_access ? formatDate(item.last_access as string) : '-',
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

export function BankAccessList() {
  const [banks, setBanks] = useState<{ id: string; name: string }[]>([]);
  const [selectedBank, setSelectedBank] = useState('');

  useEffect(() => {
    api.get<{ results?: { id: string; name: string }[]; id?: string; name?: string }[] | { results: { id: string; name: string }[] }>(
      `${ENDPOINTS.BANKS}?page_size=200`
    ).then((res) => {
      if (Array.isArray(res)) setBanks(res as { id: string; name: string }[]);
      else if (res.results) setBanks(res.results);
    }).catch(() => {});
  }, []);

  const bankFilter = (
    <select
      value={selectedBank}
      onChange={(e) => setSelectedBank(e.target.value)}
      className="h-9 rounded-md border border-gray-300 bg-white px-3 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      <option value="">Todos os bancos</option>
      {banks.map((b) => (
        <option key={b.id} value={b.id}>{b.name}</option>
      ))}
    </select>
  );

  return (
    <CrudPage
      title="Acessos"
      endpoint={ENDPOINTS.BANK_ACCESSES}
      formFieldsEndpoint={ENDPOINTS.FORM_FIELDS_BANK_ACCESS}
      columns={columns}
      createLabel="Novo Acesso"
      searchPlaceholder="Buscar acesso..."
      customActions={bankFilter}
      extraParams={selectedBank ? { bank: selectedBank } : {}}
    />
  );
}
