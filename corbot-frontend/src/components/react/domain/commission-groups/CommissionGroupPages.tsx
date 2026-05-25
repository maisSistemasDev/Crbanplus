import { PageShell } from '../../layout/PageShell';
import { CommissionGroupList } from './CommissionGroupList';
import { CompanyGroupList } from './CompanyGroupList';
import { CompanyGroupDetail } from './CompanyGroupDetail';
import { TeamBuilder } from './TeamBuilder';

export function CommissionGroupListPage() {
  return (
    <PageShell>
      <CommissionGroupList />
    </PageShell>
  );
}

export function CompanyGroupListPage() {
  return (
    <PageShell>
      <CompanyGroupList />
    </PageShell>
  );
}

export function CompanyGroupDetailPage({ groupId }: { groupId: number }) {
  return (
    <PageShell>
      <CompanyGroupDetail groupId={groupId} />
    </PageShell>
  );
}

export function TeamBuilderPage({ groupId }: { groupId: number }) {
  return (
    <PageShell>
      <TeamBuilder groupId={groupId} />
    </PageShell>
  );
}
