import type { TourStep } from './store';

/**
 * Tours estáticos pré-definidos por nome.
 * O agente pode referenciar qualquer chave deste mapa sem precisar
 * descrever cada step individualmente.
 *
 * Convenção de data-tour IDs: kebab-case, descritivo do elemento.
 */
export const TOURS: Record<string, TourStep[]> = {
  'criar-grupo-comissao': [
    {
      element: "[data-tour='sidebar-commission-groups']",
      title: 'Grupos de Comissionamento',
      description: 'Acesse aqui para gerenciar todos os seus grupos.',
      side: 'right',
    },
    {
      element: "[data-tour='create-group-btn']",
      title: 'Criar Novo Grupo',
      description: 'Clique neste botão para criar um novo grupo de comissionamento.',
      side: 'bottom',
    },
    {
      element: "[data-tour='commission-rules-table']",
      title: 'Regras de Comissão',
      description: 'Defina aqui as taxas por tabela bancária para cada membro do grupo.',
      side: 'top',
    },
  ],

  'aceitar-sugestao-tabela': [
    {
      element: "[data-tour='pending-suggestions-badge']",
      title: 'Sugestão Pendente',
      description: 'Uma tabela foi atualizada e há uma sugestão de configuração aguardando sua revisão.',
      side: 'bottom',
    },
    {
      element: "[data-tour='suggestion-card']",
      title: 'Card de Sugestão',
      description: 'Aqui estão a configuração atual e a sugerida pela IA. Compare as taxas.',
      side: 'top',
    },
    {
      element: "[data-tour='accept-suggestion-btn']",
      title: 'Aceitar Sugestão',
      description: 'Clique em Aceitar para aplicar automaticamente as novas taxas ao grupo.',
      side: 'bottom',
    },
  ],

  'importar-csv': [
    {
      element: "[data-tour='sidebar-users']",
      title: 'Menu Usuários',
      description: 'Abra o menu de Usuários para acessar a importação em lote.',
      side: 'right',
    },
    {
      element: "[data-tour='import-csv-link']",
      title: 'Importar CSV',
      description: 'Clique em "Importar CSV" para enviar um arquivo com múltiplos usuários.',
      side: 'right',
    },
    {
      element: "[data-tour='csv-upload-area']",
      title: 'Área de Upload',
      description: 'Arraste o arquivo CSV ou clique para selecioná-lo. Use o template disponível.',
      side: 'bottom',
    },
  ],

  'configurar-tabela': [
    {
      element: "[data-tour='sidebar-banks']",
      title: 'Menu Bancos',
      description: 'As tabelas bancárias ficam aqui, dentro do menu Bancos.',
      side: 'right',
    },
    {
      element: "[data-tour='tables-link']",
      title: 'Tabelas',
      description: 'Acesse a listagem de todas as tabelas cadastradas.',
      side: 'right',
    },
    {
      element: "[data-tour='table-commission-rate']",
      title: 'Taxa Base',
      description: 'Este é o campo de taxa base da tabela — o teto que define o máximo distribuível.',
      side: 'top',
    },
  ],

  'criar-vendedor': [
    {
      element: "[data-tour='sidebar-users']",
      title: 'Menu Usuários',
      description: 'Comece abrindo o menu de Usuários.',
      side: 'right',
    },
    {
      element: "[data-tour='create-user-link']",
      title: 'Criar Usuário',
      description: 'Clique em "Criar" para cadastrar um novo vendedor individualmente.',
      side: 'right',
    },
    {
      element: "[data-tour='user-role-select']",
      title: 'Papel do Usuário',
      description: 'Selecione "Vendedor" para que o usuário seja vinculado a grupos de comissionamento.',
      side: 'bottom',
    },
  ],
};
