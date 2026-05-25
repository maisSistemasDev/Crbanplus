import { PageShell } from '../../layout/PageShell';
import { BankList } from './BankList';
import { AgreementList } from './AgreementList';
import { TableList } from './TableList';

export function BankListPage() {
  return (
    <PageShell>
      <BankList />
    </PageShell>
  );
}

export function AgreementListPage() {
  return (
    <PageShell>
      <AgreementList />
    </PageShell>
  );
}

export function TableListPage() {
  return (
    <PageShell>
      <TableList />
    </PageShell>
  );
}
