import { useStore } from '@nanostores/react';
import { useEffect, useRef } from 'react';
import { pendingTour } from '../../../lib/tour/store';
import { saveTourState, startTour, resumeTourIfPending, clearTour, peekSavedTour } from '../../../lib/tour/driver';

const TOUR_NAV_KEY = 'corbanplus_tour_nav';

/**
 * Componente invisível montado no DashboardLayout.
 * 1. Resume tour salvo somente após navegação intencional do tour
 * 2. Escuta o pendingTour store para tours iniciados no chat
 */
export function TourListener() {
  const steps = useStore(pendingTour);
  const resumeAttempted = useRef(false);

  useEffect(() => {
    if (resumeAttempted.current) return;
    resumeAttempted.current = true;

    const timer = window.setTimeout(() => {
      if (sessionStorage.getItem(TOUR_NAV_KEY) === '1') {
        void resumeTourIfPending();
      } else if (peekSavedTour()) {
        clearTour();
      }
    }, 500);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!steps?.length) return;

    let cancelled = false;

    void (async () => {
      saveTourState(steps, 0);
      await new Promise((r) => setTimeout(r, 600));
      if (cancelled) return;

      const started = await startTour(steps, 0);
      if (!cancelled && started) {
        pendingTour.set(null);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [steps]);

  return null;
}
