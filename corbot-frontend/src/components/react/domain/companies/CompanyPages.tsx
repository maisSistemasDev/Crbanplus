import { PageShell } from '../../layout/PageShell';
import { CompanyForm } from './CompanyForm';
import { CompanyList } from './CompanyList';

export function CompanyCreatePage() {
  return (
    <PageShell>
      <CompanyForm />
    </PageShell>
  );
}

export function CompanyEditPage({ companyId }: { companyId: string }) {
  return (
    <PageShell>
      <CompanyForm companyId={companyId} />
    </PageShell>
  );
}

export function CompanyListPage() {
  return (
    <PageShell>
      <CompanyList />
    </PageShell>
  );
}
