import { PageShell } from '../../layout/PageShell';
import { UserForm } from './UserForm';
import { UserList } from './UserList';

export function UserCreatePage() {
  return (
    <PageShell>
      <UserForm />
    </PageShell>
  );
}

export function UserEditPage({ userId }: { userId: number }) {
  return (
    <PageShell>
      <UserForm userId={userId} />
    </PageShell>
  );
}

export function UserListPage() {
  return (
    <PageShell>
      <UserList />
    </PageShell>
  );
}

export function UserSellersPage() {
  return (
    <PageShell>
      <UserList title="Vendedores" showCreateButton={false} role="vendedor" />
    </PageShell>
  );
}

export function UserLeadersPage() {
  return (
    <PageShell>
      <UserList title="Lideres" showCreateButton={false} role="lider" />
    </PageShell>
  );
}

export function UserManagersPage() {
  return (
    <PageShell>
      <UserList title="Gerentes" showCreateButton={false} role="gerente" />
    </PageShell>
  );
}

export function UserCorbansPage() {
  return (
    <PageShell>
      <UserList title="Corbans" showCreateButton={false} role="empresa_admin" />
    </PageShell>
  );
}
