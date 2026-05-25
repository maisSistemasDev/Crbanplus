import type { TourStep } from './store';

/**
 * Tours estáticos pré-definidos por nome.
 *
 * Regras:
 * - Passos sem `url` existem em TODAS as páginas (ex: sidebar).
 * - Passos com `url` só existem na página indicada.
 * - O driver.ts navega automaticamente entre páginas via localStorage.
 * - Selectors usam data-tour attributes adicionados nos componentes.
 */
export const TOURS: Record<string, TourStep[]> = {
  'criar-grupo-comissao': [
    {
      element: "[data-tour='sidebar-commission-groups']",
      title: 'Menu Equipes',
      description: 'Clique aqui para gerenciar todos os grupos de comissionamento.',
      side: 'right',
    },
    {
      element: "[data-tour='create-group-btn']",
      title: 'Nova Equipe',
      description: 'Clique neste botao para criar um novo grupo de comissionamento.',
      side: 'bottom',
      url: '/commission-groups',
    },
    {
      element: "[data-tour='commission-rules-table']",
      title: 'Regras de Comissao',
      description: 'Aqui voce define as taxas de comissao por tabela bancaria para cada membro do grupo.',
      side: 'top',
      url: '/commission-groups',
    },
  ],

  'aceitar-sugestao-tabela': [
    {
      element: "[data-tour='pending-suggestions-badge']",
      title: 'Sugestao Pendente',
      description: 'Uma tabela bancaria foi atualizada. A IA sugeriu ajustes para manter suas equipes equilibradas.',
      side: 'bottom',
      url: '/commission-groups',
    },
    {
      element: "[data-tour='suggestion-card']",
      title: 'Detalhes da Sugestao',
      description: 'Compare a configuracao atual com a sugestao da IA.',
      side: 'top',
      url: '/commission-groups',
    },
    {
      element: "[data-tour='accept-suggestion-btn']",
      title: 'Aceitar ou Rejeitar',
      description: 'Clique em Aceitar para aplicar as novas taxas automaticamente, ou Rejeitar para manter as atuais.',
      side: 'bottom',
      url: '/commission-groups',
    },
  ],

  'importar-csv': [
    {
      element: "[data-tour='sidebar-users']",
      title: 'Menu Usuarios',
      description: 'Abra o menu de Usuarios para acessar a importacao em lote.',
      side: 'right',
    },
    {
      element: "[data-tour='import-csv-link']",
      title: 'Importar CSV',
      description: 'Clique aqui para ir a pagina de importacao de usuarios por arquivo CSV.',
      side: 'right',
    },
    {
      element: "[data-tour='csv-upload-area']",
      title: 'Area de Upload',
      description: 'Arraste o arquivo CSV ou clique para selecionar. Use o botao de template para baixar o modelo correto.',
      side: 'bottom',
      url: '/users/import',
    },
  ],

  'configurar-tabela': [
    {
      element: "[data-tour='sidebar-banks']",
      title: 'Menu Bancos',
      description: 'As tabelas bancarias ficam dentro do menu Bancos.',
      side: 'right',
    },
    {
      element: "[data-tour='tables-link']",
      title: 'Tabelas',
      description: 'Acesse a listagem de todas as tabelas cadastradas pelos bancos.',
      side: 'right',
    },
  ],

  'criar-vendedor': [
    {
      element: "[data-tour='sidebar-users']",
      title: 'Menu Usuarios',
      description: 'Comece abrindo o menu de Usuarios no painel lateral.',
      side: 'right',
    },
    {
      element: "[data-tour='create-user-link']",
      title: 'Criar Usuario',
      description: 'Clique em Criar para abrir o formulario de cadastro de novo usuario.',
      side: 'right',
    },
    {
      element: "[data-tour='user-form-role']",
      title: 'Papel do Usuario',
      description: 'Selecione Vendedor para que o usuario seja vinculado a grupos de comissionamento.',
      side: 'bottom',
      url: '/users/create',
    },
  ],
};
