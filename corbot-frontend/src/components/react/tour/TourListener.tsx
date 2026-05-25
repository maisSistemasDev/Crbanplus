import { useStore } from '@nanostores/react';
import { useEffect } from 'react';
import { pendingTour } from '../../../lib/tour/store';
import { startTour } from '../../../lib/tour/driver';

/**
 * Componente invisível que escuta o pendingTour store e dispara o Driver.js.
 * Deve ser montado uma única vez no DashboardLayout com client:only="react".
 */
export function TourListener() {
  const steps = useStore(pendingTour);

  useEffect(() => {
    if (steps && steps.length > 0) {
      startTour(steps);
      pendingTour.set(null);
    }
  }, [steps]);

  return null;
}
