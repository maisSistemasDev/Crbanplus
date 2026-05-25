import { PageShell } from '../../layout/PageShell';
import { CommissionList } from './CommissionList';
import { CommissionMirror } from './CommissionMirror';
import { GenerateCommissions } from './GenerateCommissions';

export function CommissionListPage() {
  return (
    <PageShell>
      <CommissionList />
    </PageShell>
  );
}

export function CommissionMirrorPage() {
  return (
    <PageShell>
      <CommissionMirror />
    </PageShell>
  );
}

export function GenerateCommissionsPage() {
  return (
    <PageShell>
      <GenerateCommissions />
    </PageShell>
  );
}
