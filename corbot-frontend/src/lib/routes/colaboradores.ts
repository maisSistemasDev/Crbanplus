/** Rotas da área de colaboradores da promotora (UI). */
export const COLABORADORES_ROUTES = {
  list: '/colaboradores',
  create: '/colaboradores/create',
  edit: (id: number | string) => `/colaboradores/${id}/edit`,
  permissions: (id: number | string) => `/colaboradores/${id}/permissions`,
} as const;
