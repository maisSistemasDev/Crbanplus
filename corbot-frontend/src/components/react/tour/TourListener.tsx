import { useStore } from '@nanostores/react';
import { useEffect } from 'react';
import { pendingTour } from '../../../lib/tour/store';
import { startTour, resumeTourIfPending } from '../../../lib/tour/driver';

/**
 * Componente invisível montado no DashboardLayout.
 * 1. Resume tour salvo no localStorage (navegação cross-page)
 * 2. Escuta o pendingTour store para tours iniciados no chat
 */
export function TourListener() {
  const steps = useStore(pendingTour);

  // Resume tour do localStorage ao carregar cada página
  useEffect(() => {
    resumeTourIfPending();
  }, []);

  // Reage a tours iniciados pelo chat widget
  useEffect(() => {
    if (steps && steps.length > 0) {
      startTour(steps);
      pendingTour.set(null);
    }
  }, [steps]);

  return null;
}
