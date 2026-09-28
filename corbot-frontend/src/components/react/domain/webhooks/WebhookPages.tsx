import { PageShell } from '../../layout/PageShell';
import { WebhookList } from './WebhookList';
import { WebhookEditor } from './WebhookEditor';

export function WebhookListPage() {
  return (
    <PageShell>
      <WebhookList />
    </PageShell>
  );
}

export function WebhookCreatePage() {
  return (
    <PageShell>
      <WebhookEditor />
    </PageShell>
  );
}

export function WebhookEditPage({ webhookId }: { webhookId: string }) {
  return (
    <PageShell>
      <WebhookEditor webhookId={webhookId} />
    </PageShell>
  );
}
