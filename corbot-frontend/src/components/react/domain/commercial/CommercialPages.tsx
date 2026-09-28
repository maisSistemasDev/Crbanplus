import { PageShell } from '../../layout/PageShell';
import { CommercialManagersPage } from './CommercialManagersPage';
import { CommercialTeamsPage } from './CommercialTeamsPage';
import { CommercialProductionPage } from './CommercialProductionPage';

export function CommercialManagersPageShell() {
  return (
    <PageShell>
      <CommercialManagersPage />
    </PageShell>
  );
}

export function CommercialTeamsPageShell() {
  return (
    <PageShell>
      <CommercialTeamsPage />
    </PageShell>
  );
}

export function CommercialProductionPageShell() {
  return (
    <PageShell>
      <CommercialProductionPage />
    </PageShell>
  );
}
