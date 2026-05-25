import type { TourStep } from './store';

const LS_KEY = 'corbanplus_tour';

// ── Persistência cross-page ──────────────────────────────────────────────────

function saveTour(steps: TourStep[]) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(steps));
  } catch { /* noop */ }
}

function loadTour(): TourStep[] | null {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function clearTour() {
  try { localStorage.removeItem(LS_KEY); } catch { /* noop */ }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function elementExists(selector: string): boolean {
  try { return !!document.querySelector(selector); } catch { return false; }
}

function currentPath(): string {
  return typeof window !== 'undefined' ? window.location.pathname : '/';
}

/** Espera até 2s pelo elemento aparecer no DOM (para React lazy renders). */
function waitForElement(selector: string, timeout = 2000): Promise<Element | null> {
  return new Promise((resolve) => {
    const el = document.querySelector(selector);
    if (el) return resolve(el);

    const observer = new MutationObserver(() => {
      const found = document.querySelector(selector);
      if (found) {
        observer.disconnect();
        resolve(found);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    setTimeout(() => { observer.disconnect(); resolve(null); }, timeout);
  });
}

// ── Core ─────────────────────────────────────────────────────────────────────

export async function startTour(allSteps: TourStep[]) {
  if (!allSteps.length) return;

  const path = currentPath();

  // Separa passos da página atual (sem url ou url == path) dos de outras páginas
  const pageSteps: TourStep[] = [];
  const remainingSteps: TourStep[] = [];
  let passedCurrentPage = false;

  for (const step of allSteps) {
    const isCurrentPage = !step.url || step.url === path;
    if (!passedCurrentPage && isCurrentPage) {
      pageSteps.push(step);
    } else {
      passedCurrentPage = true;
      remainingSteps.push(step);
    }
  }

  // Se nenhum passo é desta página, navega para a primeira URL
  if (pageSteps.length === 0) {
    const nextUrl = allSteps.find((s) => s.url)?.url;
    if (nextUrl && nextUrl !== path) {
      saveTour(allSteps);
      window.location.href = nextUrl;
    }
    return;
  }

  // Aguarda elementos (React pode renderizar depois do mount)
  const visibleSteps: TourStep[] = [];
  for (const step of pageSteps) {
    const el = await waitForElement(step.element, 1500);
    if (el) visibleSteps.push(step);
  }

  if (visibleSteps.length === 0) {
    // Elementos não encontrados mesmo após espera — pula para próxima página
    if (remainingSteps.length > 0) {
      const nextUrl = remainingSteps.find((s) => s.url)?.url;
      if (nextUrl) {
        saveTour(remainingSteps);
        window.location.href = nextUrl;
      }
    }
    return;
  }

  const { driver } = await import('driver.js');
  await import('driver.js/dist/driver.css');

  const isLastPage = remainingSteps.length === 0;
  const nextUrl = !isLastPage ? remainingSteps.find((s) => s.url)?.url : undefined;

  const d = driver({
    animate: true,
    overlayOpacity: 0.75,
    stagePadding: 10,
    allowClose: true,
    doneBtnText: isLastPage ? 'Entendido ✓' : 'Continuar →',
    closeBtnText: '✕',
    nextBtnText: 'Próximo →',
    prevBtnText: '← Anterior',
    steps: visibleSteps.map((s) => ({
      element: s.element,
      popover: {
        title: s.title,
        description: s.description,
        side: s.side ?? 'bottom',
        align: s.align ?? 'start',
      },
    })),
    onDestroyStarted: () => {
      const isOnLastStep = !d.hasNextStep();

      if (isOnLastStep && !isLastPage && nextUrl) {
        // Usuário chegou ao fim desta página → continua no próximo
        saveTour(remainingSteps);
        d.destroy();
        window.location.href = nextUrl;
      } else {
        // Usuário fechou manualmente
        clearTour();
        d.destroy();
      }
    },
  });

  d.drive();
}

/** Chama no mount de cada página para retomar tour salvo. */
export async function resumeTourIfPending() {
  const steps = loadTour();
  if (!steps) return;
  clearTour(); // evita loop infinito
  await startTour(steps);
}

// Expõe globalmente para o agente chamar via window.startTour(steps)
if (typeof window !== 'undefined') {
  (window as unknown as Record<string, unknown>).startTour = startTour;
  (window as unknown as Record<string, unknown>).clearTour = clearTour;
}

