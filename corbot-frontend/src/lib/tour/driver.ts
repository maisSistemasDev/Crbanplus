import type { TourStep } from './store';

let driverInstance: import('driver.js').driver | null = null;

async function getDriver() {
  if (!driverInstance) {
    const { driver } = await import('driver.js');
    await import('driver.js/dist/driver.css');
    driverInstance = driver({
      animate: true,
      overlayOpacity: 0.7,
      stagePadding: 8,
      allowClose: true,
      doneBtnText: 'Entendido',
      closeBtnText: 'Fechar',
      nextBtnText: 'Próximo →',
      prevBtnText: '← Anterior',
      onDestroyStarted: () => {
        driverInstance?.destroy();
      },
    });
  }
  return driverInstance;
}

export async function startTour(steps: TourStep[]) {
  if (!steps.length) return;
  const d = await getDriver();
  d.setSteps(
    steps.map((s) => ({
      element: s.element,
      popover: {
        title: s.title,
        description: s.description,
        side: s.side ?? 'bottom',
        align: s.align ?? 'start',
      },
    })),
  );
  d.drive();
}

export async function highlightElement(
  selector: string,
  title: string,
  description: string,
) {
  const d = await getDriver();
  d.highlight({
    element: selector,
    popover: { title, description },
  });
}

// Expõe globalmente para o agente chamar via window.startTour(steps)
if (typeof window !== 'undefined') {
  (window as unknown as Record<string, unknown>).startTour = startTour;
  (window as unknown as Record<string, unknown>).highlightElement = highlightElement;
}
