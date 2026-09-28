import { useState, useEffect, useMemo } from 'react';
import { CrudPage } from '../shared/CrudPage';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { api } from '../../../../lib/api/client';
import { Badge } from '../../ui/Badge';
import { SearchSelect } from '../../ui/SearchSelect';
import type { Column } from '../../ui/DataTable';
import { buildBankAccessFormFields } from './formFields';

const columns: Column<Record<string, unknown>>[] = [
  {
    key: 'bank_name',
    header: 'Banco',
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
    key: 'is_master',
    header: 'Master',
    render: (item) => (
      <Badge variant={item.is_master ? 'warning' : 'default'}>
        {item.is_master ? 'Corban' : 'Equipe'}
      </Badge>
    ),
  },
  {
    key: 'notes',
    header: 'Obs.',
    render: (item) => (item.notes as string) || '-',
  },
  {
    key: 'link',
    header: 'Link',
    render: (item) => {
      const link = item.link as string;
      if (!link) return '-';
      return (
        <a href={link} target="_blank" rel="noopener noreferrer" className="text-blue-600 text-xs underline">
          Abrir
        </a>
      );
    },
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

  const bankOptions = useMemo(() => banks.map((b) => ({ value: b.id, label: b.name })), [banks]);

  const bankFilter = (
    <SearchSelect
      className="w-full sm:w-56"
      placeholder="Todos os bancos"
      allowEmpty
      value={selectedBank}
      options={bankOptions}
      onChange={(e) => setSelectedBank(e.target.value)}
    />
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
      filterFormFields={(fields, item) => buildBankAccessFormFields(fields, { isEdit: !!item })}
      getEditModalTitle={(item) => String(item.bank_name || 'Acesso')}
    />
  );
}
