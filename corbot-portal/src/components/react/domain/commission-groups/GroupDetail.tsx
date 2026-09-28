import { useEffect, useState } from 'react';
import { useStore } from '@nanostores/react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { $currentUser } from '../../../../lib/stores/auth';
import type { CommissionGroup } from '../../../../lib/api/types';
import { TeamBuilder } from './TeamBuilder';
import { ReadOnlyGroupView } from './ReadOnlyGroupView';
import { SectionSpinner } from '../../ui/Spinner';

interface GroupDetailProps {
  groupId: number;
}

export function GroupDetail({ groupId }: GroupDetailProps) {
  const user = useStore($currentUser);
  const [group, setGroup] = useState<CommissionGroup | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .get<CommissionGroup>(ENDPOINTS.COMMISSION_GROUP_DETAIL(groupId))
      .then(setGroup)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [groupId]);

  if (loading || !user) return <SectionSpinner />;
  if (error) return <div className="card text-sm text-red-600">{error}</div>;
  if (!group) return null;

  const canManage =
    user.role === 'admin' ||
    user.role === 'empresa_admin' ||
    user.role === 'gerente' ||
    (user.role === 'lider' && group.leader === user.id);

  return canManage ? <TeamBuilder groupId={groupId} /> : <ReadOnlyGroupView groupId={groupId} />;
}
