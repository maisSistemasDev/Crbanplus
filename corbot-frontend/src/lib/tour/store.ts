import { atom } from 'nanostores';

export type TourStep = {
  /** Seletor CSS do elemento a destacar, ex: "[data-tour='create-group-btn']" */
  element: string;
  title: string;
  description: string;
  side?: 'top' | 'bottom' | 'left' | 'right';
  align?: 'start' | 'center' | 'end';
  /**
   * Caminho da página onde este elemento existe, ex: '/commission-groups'.
   * Omitir para elementos presentes em todas as páginas (ex: sidebar).
   */
  url?: string;
};

/**
 * O agente (ou qualquer parte do app) escreve aqui para disparar um tour.
 * O TourListener observa este store e executa o Driver.js.
 */
export const pendingTour = atom<TourStep[] | null>(null);
