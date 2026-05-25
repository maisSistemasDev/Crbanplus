import { PageShell } from '../../layout/PageShell';
import { LogViewer } from './LogViewer';

export function AuditLogPage() {
  return (
    <PageShell>
      <LogViewer title="Logs de Auditoria" endpoint="/audit-logs/" />
    </PageShell>
  );
}

export function SystemLogPage() {
  return (
    <PageShell>
      <LogViewer title="Logs do Sistema" endpoint="/access-logs/" />
    </PageShell>
  );
}
