import { useEffect, useState, useRef } from 'react';
import { useStore } from '@nanostores/react';
import { $tokens } from '../stores/auth';
import { createBatchSocket } from './client';
import type { BatchStatusMessage } from '../api/types';

export function useBatchProgress(batchId: string | null) {
  const tokens = useStore($tokens);
  const [status, setStatus] = useState<BatchStatusMessage | null>(null);
  const socketRef = useRef<{ close: () => void } | null>(null);

  useEffect(() => {
    if (!batchId || !tokens?.access) return;

    socketRef.current = createBatchSocket(
      batchId,
      tokens.access,
      (data) => setStatus(data),
    );

    return () => {
      socketRef.current?.close();
    };
  }, [batchId, tokens?.access]);

  return status;
}
