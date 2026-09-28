import { PageShell } from '../../layout/PageShell';
import { CommissionGroupList } from './CommissionGroupList';
import { CompanyGroupList } from './CompanyGroupList';
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

/** @deprecated Use TeamBuilderPage — grupos por Corban usam /commission-groups/{id} */
export function CompanyGroupDetailPage({ groupId }: { groupId: number }) {
  return (
    <PageShell>
      <TeamBuilder groupId={groupId} />
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
