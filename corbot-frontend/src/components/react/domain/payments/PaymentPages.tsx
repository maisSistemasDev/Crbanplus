import { PageShell } from '../../layout/PageShell';
import { PaymentList } from './PaymentList';
import { WithdrawalRequest } from './WithdrawalRequest';
import { CorbanPayWithdraw } from './CorbanPayWithdraw';

export function PaymentListPage() {
  return (
    <PageShell>
      <PaymentList />
    </PageShell>
  );
}

export function WithdrawalRequestPage() {
  return (
    <PageShell>
      <WithdrawalRequest />
    </PageShell>
  );
}

export function CorbanPayWithdrawPage() {
  return (
    <PageShell>
      <CorbanPayWithdraw />
    </PageShell>
  );
}
