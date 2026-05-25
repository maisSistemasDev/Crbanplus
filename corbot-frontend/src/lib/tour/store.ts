import { atom } from 'nanostores';

export type TourStep = {
  /** Seletor CSS ou atributo data-tour, ex: "[data-tour='create-group-btn']" */
  element: string;
  title: string;
  description: string;
  side?: 'top' | 'bottom' | 'left' | 'right';
  align?: 'start' | 'center' | 'end';
};

/**
 * O agente (ou qualquer parte do app) escreve aqui para disparar um tour.
 * O TourListener observa este store e executa o Driver.js.
 */
export const pendingTour = atom<TourStep[] | null>(null);
