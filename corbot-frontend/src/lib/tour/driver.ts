import type { TourStep } from './store';

const LS_KEY = 'corbanplus_tour';
const TOUR_NAV_KEY = 'corbanplus_tour_nav';

const FIRST_STEP_WAIT_MS = 9000;
const NEXT_STEP_WAIT_MS = 1500;

export type SavedTourState = {
  steps: TourStep[];
  /** Índice global no array `steps` (0-based). */
  globalIndex: number;
};

let activeGlobalIndex = 0;
let userClosedTour = false;
let pagehideRegistered = false;

// ── Persistência cross-page ──────────────────────────────────────────────────

export function saveTourState(steps: TourStep[], globalIndex: number) {
  try {
    const payload: SavedTourState = {
      steps,
      globalIndex: Math.max(0, Math.min(globalIndex, steps.length)),
    };
    localStorage.setItem(LS_KEY, JSON.stringify(payload));
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('corbot-tour-updated'));
    }
  } catch { /* noop */ }
}

export function peekSavedTour(): SavedTourState | null {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return { steps: parsed, globalIndex: 0 };
    }
    if (parsed && Array.isArray(parsed.steps)) {
      return {
        steps: parsed.steps,
        globalIndex: typeof parsed.globalIndex === 'number' ? parsed.globalIndex : 0,
      };
    }
    return null;
  } catch {
    return null;
  }
}

function loadTourState(): SavedTourState | null {
  return peekSavedTour();
}

export function clearTour() {
  try { localStorage.removeItem(LS_KEY); } catch { /* noop */ }
  try { sessionStorage.removeItem(TOUR_NAV_KEY); } catch { /* noop */ }
  activeGlobalIndex = 0;
  userClosedTour = false;
}

/** Marca que a próxima carga de página deve retomar o tour (navegação intencional). */
function markTourNavigation() {
  sessionStorage.setItem(TOUR_NAV_KEY, '1');
}

function consumeTourNavigation(): boolean {
  const pending = sessionStorage.getItem(TOUR_NAV_KEY) === '1';
  sessionStorage.removeItem(TOUR_NAV_KEY);
  return pending;
}

/** IDs data-tour exigidos pelo tour salvo (para abrir submenus da sidebar). */
export function getPendingTourTargetIds(): Set<string> {
  const navPending = sessionStorage.getItem(TOUR_NAV_KEY) === '1';
  const saved = peekSavedTour();
  if (!navPending && !saved) return new Set();
  if (!saved) return new Set();
  const ids = new Set<string>();
  for (const step of saved.steps) {
    const match = step.element.match(/data-tour=['"]([^'"]+)['"]/);
    if (match?.[1]) ids.add(match[1]);
  }
  return ids;
}

function ensurePagehideListener() {
  if (pagehideRegistered || typeof window === 'undefined') return;
  pagehideRegistered = true;
  window.addEventListener('pagehide', () => {
    if (userClosedTour) return;
    // Navegação intencional do tour: mantém estado para retomar na próxima página.
    if (sessionStorage.getItem(TOUR_NAV_KEY) === '1') return;
    // Usuário saiu manualmente (outro link, aba, etc.): abandona o tour.
    clearTour();
  });
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function normPath(p: string): string {
  return (p || '/').replace(/\/+$/, '') || '/';
}

function currentPath(): string {
  return normPath(typeof window !== 'undefined' ? window.location.pathname : '/');
}

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

function stepMatchesPage(step: TourStep, path: string): boolean {
  return !step.url || normPath(step.url) === path;
}

function firstIndexForPath(allSteps: TourStep[], path: string, minIndex = 0): number {
  const normalized = normPath(path);
  for (let i = minIndex; i < allSteps.length; i++) {
    const step = allSteps[i];
    if (step.url && normPath(step.url) === normalized) return i;
  }
  for (let i = minIndex; i < allSteps.length; i++) {
    if (stepMatchesPage(allSteps[i], normalized)) return i;
  }
  return minIndex;
}

function splitStepsFromIndex(allSteps: TourStep[], startIndex: number, path: string) {
  const slice = allSteps.slice(startIndex);
  const pageSteps: TourStep[] = [];
  const remainingSteps: TourStep[] = [];
  let passedCurrentPage = false;

  for (const step of slice) {
    const onPage = stepMatchesPage(step, path);
    if (!passedCurrentPage && onPage) {
      pageSteps.push(step);
    } else {
      passedCurrentPage = true;
      remainingSteps.push(step);
    }
  }

  return { pageSteps, remainingSteps };
}

function findNextTourUrl(allSteps: TourStep[], fromIndex: number, current: string): string | undefined {
  for (let i = fromIndex; i < allSteps.length; i++) {
    const url = allSteps[i].url;
    if (url && normPath(url) !== current) return url;
  }
  return undefined;
}

function navigateForTour(allSteps: TourStep[], nextUrl: string, fromIndex: number) {
  const nextIndex = firstIndexForPath(allSteps, nextUrl, fromIndex);
  saveTourState(allSteps, nextIndex);
  markTourNavigation();
  window.location.href = nextUrl;
}

type StartTourOptions = {
  /** True quando retomando após navegação intencional do próprio tour. */
  fromResume?: boolean;
};

// ── Core ─────────────────────────────────────────────────────────────────────

export async function startTour(
  allSteps: TourStep[],
  startGlobalIndex = 0,
  options: StartTourOptions = {},
): Promise<boolean> {
  if (!allSteps.length) return false;

  userClosedTour = false;
  activeGlobalIndex = Math.max(0, Math.min(startGlobalIndex, allSteps.length - 1));
  ensurePagehideListener();

  const path = currentPath();
  const { pageSteps, remainingSteps } = splitStepsFromIndex(allSteps, activeGlobalIndex, path);

  // Nenhum passo nesta página: só redireciona se for continuação intencional do tour.
  if (pageSteps.length === 0) {
    const nextUrl = findNextTourUrl(allSteps, activeGlobalIndex, path);
    if (nextUrl) {
      navigateForTour(allSteps, nextUrl, activeGlobalIndex);
      return true;
    }
    return false;
  }

  const visibleSteps: TourStep[] = [];
  for (let i = 0; i < pageSteps.length; i++) {
    const step = pageSteps[i];
    const wait = i === 0 ? FIRST_STEP_WAIT_MS : NEXT_STEP_WAIT_MS;
    const el = await waitForElement(step.element, wait);
    if (el) visibleSteps.push(step);
  }

  // Elementos não encontrados: só pula de página se for retomada intencional.
  if (visibleSteps.length === 0) {
    if (options.fromResume) {
      const nextUrl = findNextTourUrl(allSteps, activeGlobalIndex, path)
        ?? remainingSteps.find((s) => s.url)?.url;
      if (nextUrl && normPath(nextUrl) !== path) {
        navigateForTour(allSteps, nextUrl, activeGlobalIndex);
        return true;
      }
    }
    return false;
  }

  const { driver } = await import('driver.js');
  await import('driver.js/dist/driver.css');

  const isLastPage = remainingSteps.length === 0;
  const nextUrl = !isLastPage ? findNextTourUrl(allSteps, activeGlobalIndex + visibleSteps.length, path) : undefined;
  const pageStartGlobalIndex = activeGlobalIndex;

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
    onHighlighted: (_el, _step, { state }) => {
      activeGlobalIndex = pageStartGlobalIndex + state.activeIndex;
      saveTourState(allSteps, activeGlobalIndex);
    },
    onCloseClick: () => {
      userClosedTour = true;
    },
    onDestroyStarted: () => {
      const isOnLastStep = !d.hasNextStep();

      if (userClosedTour) {
        clearTour();
        d.destroy();
        return;
      }

      if (isOnLastStep && !isLastPage && nextUrl) {
        activeGlobalIndex = pageStartGlobalIndex + visibleSteps.length;
        d.destroy();
        navigateForTour(allSteps, nextUrl, activeGlobalIndex);
        return;
      }

      if (isOnLastStep && isLastPage) {
        clearTour();
      } else {
        saveTourState(allSteps, activeGlobalIndex);
      }
      d.destroy();
    },
  });

  saveTourState(allSteps, activeGlobalIndex);
  d.drive();
  return true;
}

/** Retoma tour apenas após navegação intencional do tour (flag em sessionStorage). */
export async function resumeTourIfPending(): Promise<boolean> {
  if (sessionStorage.getItem(TOUR_NAV_KEY) !== '1') return false;

  consumeTourNavigation();
  const saved = loadTourState();
  if (!saved?.steps.length) return false;

  return startTour(saved.steps, saved.globalIndex, { fromResume: true });
}

if (typeof window !== 'undefined') {
  (window as unknown as Record<string, unknown>).startTour = startTour;
  (window as unknown as Record<string, unknown>).clearTour = clearTour;
}
