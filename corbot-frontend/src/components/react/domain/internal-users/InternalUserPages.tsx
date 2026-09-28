import { PageShell } from '../../layout/PageShell';
import InternalUserList from './InternalUserList';
import InternalUserForm from './InternalUserForm';
import PermissionManager from './PermissionManager';

export function InternalUserListPage() {
  return (
    <PageShell>
      <InternalUserList />
    </PageShell>
  );
}

export function InternalUserCreatePage() {
  return (
    <PageShell>
      <InternalUserForm />
    </PageShell>
  );
}

export function InternalUserEditPage({ userId }: { userId: number }) {
  return (
    <PageShell>
      <InternalUserForm userId={userId} />
    </PageShell>
  );
}

export function InternalUserPermissionsPage({ userId }: { userId: string }) {
  return (
    <PageShell>
      <PermissionManager userId={userId} />
    </PageShell>
  );
}
