import { PageShell } from '../../layout/PageShell';
import { BatchList } from './BatchList';
import { BatchDetail } from './BatchDetail';
import { BatchUpload } from './BatchUpload';
import { LayoutList } from './LayoutList';
import { ColumnMapper } from './ColumnMapper';

export function BatchListPage() {
  return (
    <PageShell>
      <BatchList />
    </PageShell>
  );
}

export function BatchDetailPage({ batchId }: { batchId: string }) {
  return (
    <PageShell>
      <BatchDetail batchId={batchId} />
    </PageShell>
  );
}

export function BatchUploadPage() {
  return (
    <PageShell>
      <BatchUpload />
    </PageShell>
  );
}

export function LayoutListPage() {
  return (
    <PageShell>
      <LayoutList />
    </PageShell>
  );
}

export function LayoutCreatePage() {
  return (
    <PageShell>
      <ColumnMapper />
    </PageShell>
  );
}
