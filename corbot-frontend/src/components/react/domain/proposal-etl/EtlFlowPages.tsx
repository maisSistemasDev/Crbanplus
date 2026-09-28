import { PageShell } from '../../layout/PageShell';
import { EtlFlowList } from './EtlFlowList';
import { EtlFlowEditor } from './EtlFlowEditor';

export function EtlFlowListPage() {
  return (
    <PageShell>
      <EtlFlowList />
    </PageShell>
  );
}

export function EtlFlowEditorPage({ flowId }: { flowId: string }) {
  return (
    <PageShell>
      <EtlFlowEditor flowId={flowId} />
    </PageShell>
  );
}
