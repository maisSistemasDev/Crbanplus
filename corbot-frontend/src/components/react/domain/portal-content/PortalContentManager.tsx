import { useEffect, useMemo, useState } from 'react';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import type { Company, PortalUsefulLink, PortalWallMessage } from '../../../../lib/api/types';
import { formatDateTime } from '../../../../lib/utils/format';
import { PageHeader } from '../../ui/PageHeader';
import { Button } from '../../ui/Button';
import { Modal } from '../../ui/Modal';
import { SearchSelect } from '../../ui/SearchSelect';

interface LinkFormState {
  title: string;
  url: string;
  display_order: number;
  is_active: boolean;
}

interface MessageFormState {
  title: string;
  message: string;
  company: string;
  starts_at: string;
  ends_at: string;
  display_order: number;
  is_active: boolean;
}

const EMPTY_LINK_FORM: LinkFormState = {
  title: '',
  url: '',
  display_order: 0,
  is_active: true,
};

const EMPTY_MESSAGE_FORM: MessageFormState = {
  title: '',
  message: '',
  company: '',
  starts_at: '',
  ends_at: '',
  display_order: 0,
  is_active: true,
};

function toLocalDateTimeInput(value: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

export function PortalContentManager() {
  const [links, setLinks] = useState<PortalUsefulLink[]>([]);
  const [messages, setMessages] = useState<PortalWallMessage[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);

  const companyOptions = useMemo(
    () => companies.map((company) => ({ value: String(company.id), label: company.name })),
    [companies],
  );

  const [linkModalOpen, setLinkModalOpen] = useState(false);
  const [messageModalOpen, setMessageModalOpen] = useState(false);
  const [editingLink, setEditingLink] = useState<PortalUsefulLink | null>(null);
  const [editingMessage, setEditingMessage] = useState<PortalWallMessage | null>(null);

  const [linkForm, setLinkForm] = useState<LinkFormState>(EMPTY_LINK_FORM);
  const [messageForm, setMessageForm] = useState<MessageFormState>(EMPTY_MESSAGE_FORM);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadAll();
  }, []);

  async function loadAll() {
    setLoading(true);
    try {
      const [linksRes, messagesRes, companiesRes] = await Promise.all([
        api.get<PortalUsefulLink[]>(ENDPOINTS.PORTAL_USEFUL_LINKS),
        api.get<PortalWallMessage[]>(ENDPOINTS.PORTAL_WALL_MESSAGES),
        api.get<Company[]>(ENDPOINTS.COMPANIES),
      ]);
      setLinks(Array.isArray(linksRes) ? linksRes : []);
      setMessages(Array.isArray(messagesRes) ? messagesRes : []);
      setCompanies(Array.isArray(companiesRes) ? companiesRes : []);
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  function openCreateLink() {
    setEditingLink(null);
    setLinkForm(EMPTY_LINK_FORM);
    setLinkModalOpen(true);
  }

  function openEditLink(item: PortalUsefulLink) {
    setEditingLink(item);
    setLinkForm({
      title: item.title,
      url: item.url,
      display_order: item.display_order,
      is_active: item.is_active,
    });
    setLinkModalOpen(true);
  }

  function openCreateMessage() {
    setEditingMessage(null);
    setMessageForm(EMPTY_MESSAGE_FORM);
    setMessageModalOpen(true);
  }

  function openEditMessage(item: PortalWallMessage) {
    setEditingMessage(item);
    setMessageForm({
      title: item.title,
      message: item.message,
      company: item.company ?? '',
      starts_at: toLocalDateTimeInput(item.starts_at),
      ends_at: toLocalDateTimeInput(item.ends_at),
      display_order: item.display_order,
      is_active: item.is_active,
    });
    setMessageModalOpen(true);
  }

  async function submitLink(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingLink) {
        await api.patch(ENDPOINTS.PORTAL_USEFUL_LINK_DETAIL(editingLink.id), linkForm);
        toast.success('Link útil atualizado com sucesso.');
      } else {
        await api.post(ENDPOINTS.PORTAL_USEFUL_LINKS, linkForm);
        toast.success('Link útil criado com sucesso.');
      }
      setLinkModalOpen(false);
      await loadAll();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  async function submitMessage(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...messageForm,
        company: messageForm.company || null,
        starts_at: messageForm.starts_at || null,
        ends_at: messageForm.ends_at || null,
      };
      if (editingMessage) {
        await api.patch(ENDPOINTS.PORTAL_WALL_MESSAGE_DETAIL(editingMessage.id), payload);
        toast.success('Mensagem do mural atualizada com sucesso.');
      } else {
        await api.post(ENDPOINTS.PORTAL_WALL_MESSAGES, payload);
        toast.success('Mensagem do mural criada com sucesso.');
      }
      setMessageModalOpen(false);
      await loadAll();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  async function deleteLink(item: PortalUsefulLink) {
    if (!window.confirm(`Excluir link "${item.title}"?`)) return;
    try {
      await api.delete(ENDPOINTS.PORTAL_USEFUL_LINK_DETAIL(item.id));
      toast.success('Link removido.');
      await loadAll();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    }
  }

  async function deleteMessage(item: PortalWallMessage) {
    if (!window.confirm(`Excluir mensagem "${item.title}"?`)) return;
    try {
      await api.delete(ENDPOINTS.PORTAL_WALL_MESSAGE_DETAIL(item.id));
      toast.success('Mensagem removida.');
      await loadAll();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Conteudo do Portal"
        subtitle="Postador de Links Uteis e Mural de Mensagens para os corbans"
      />

      <section className="card">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900">Links Uteis</h2>
          <Button size="sm" onClick={openCreateLink}>
            <Plus size={14} />
            Novo link
          </Button>
        </div>

        {loading ? (
          <p className="text-sm text-gray-500">Carregando...</p>
        ) : links.length === 0 ? (
          <p className="text-sm text-gray-500">Nenhum link cadastrado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs uppercase text-gray-500">
                  <th className="py-2 pr-3">Titulo</th>
                  <th className="py-2 pr-3">URL</th>
                  <th className="py-2 pr-3">Ordem</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Atualizado</th>
                  <th className="py-2 text-right">Acoes</th>
                </tr>
              </thead>
              <tbody>
                {links.map((item) => (
                  <tr key={item.id} className="border-b border-gray-50">
                    <td className="py-2 pr-3 font-medium text-gray-800">{item.title}</td>
                    <td className="py-2 pr-3 text-gray-600">{item.url}</td>
                    <td className="py-2 pr-3">{item.display_order}</td>
                    <td className="py-2 pr-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs ${item.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'}`}>
                        {item.is_active ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>
                    <td className="py-2 pr-3 text-gray-500">{formatDateTime(item.updated_at)}</td>
                    <td className="py-2 text-right">
                      <div className="inline-flex items-center gap-1">
                        <button className="rounded p-1 text-gray-500 hover:bg-gray-100" onClick={() => openEditLink(item)}>
                          <Pencil size={14} />
                        </button>
                        <button className="rounded p-1 text-red-600 hover:bg-red-50" onClick={() => deleteLink(item)}>
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900">Mural de Mensagens</h2>
          <Button size="sm" onClick={openCreateMessage}>
            <Plus size={14} />
            Nova mensagem
          </Button>
        </div>

        {loading ? (
          <p className="text-sm text-gray-500">Carregando...</p>
        ) : messages.length === 0 ? (
          <p className="text-sm text-gray-500">Nenhuma mensagem cadastrada.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs uppercase text-gray-500">
                  <th className="py-2 pr-3">Titulo</th>
                  <th className="py-2 pr-3">Corban alvo</th>
                  <th className="py-2 pr-3">Periodo</th>
                  <th className="py-2 pr-3">Ordem</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 text-right">Acoes</th>
                </tr>
              </thead>
              <tbody>
                {messages.map((item) => (
                  <tr key={item.id} className="border-b border-gray-50 align-top">
                    <td className="py-2 pr-3">
                      <p className="font-medium text-gray-800">{item.title}</p>
                      <p className="text-xs text-gray-500">{item.message}</p>
                    </td>
                    <td className="py-2 pr-3 text-gray-700">{item.company_name ?? 'Todos os corbans'}</td>
                    <td className="py-2 pr-3 text-gray-500">
                      {item.starts_at ? formatDateTime(item.starts_at) : 'Sem inicio'}
                      {' - '}
                      {item.ends_at ? formatDateTime(item.ends_at) : 'Sem fim'}
                    </td>
                    <td className="py-2 pr-3">{item.display_order}</td>
                    <td className="py-2 pr-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs ${item.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'}`}>
                        {item.is_active ? 'Ativa' : 'Inativa'}
                      </span>
                    </td>
                    <td className="py-2 text-right">
                      <div className="inline-flex items-center gap-1">
                        <button className="rounded p-1 text-gray-500 hover:bg-gray-100" onClick={() => openEditMessage(item)}>
                          <Pencil size={14} />
                        </button>
                        <button className="rounded p-1 text-red-600 hover:bg-red-50" onClick={() => deleteMessage(item)}>
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <Modal
        isOpen={linkModalOpen}
        onClose={() => setLinkModalOpen(false)}
        title={editingLink ? 'Editar link util' : 'Novo link util'}
      >
        <form className="space-y-3" onSubmit={submitLink}>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Titulo</label>
            <input
              required
              value={linkForm.title}
              onChange={(e) => setLinkForm((prev) => ({ ...prev, title: e.target.value }))}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">URL</label>
            <input
              required
              type="url"
              value={linkForm.url}
              onChange={(e) => setLinkForm((prev) => ({ ...prev, url: e.target.value }))}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Ordem</label>
            <input
              type="number"
              value={linkForm.display_order}
              onChange={(e) => setLinkForm((prev) => ({ ...prev, display_order: Number(e.target.value || 0) }))}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <label className="inline-flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={linkForm.is_active}
              onChange={(e) => setLinkForm((prev) => ({ ...prev, is_active: e.target.checked }))}
            />
            Ativo
          </label>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setLinkModalOpen(false)}>Cancelar</Button>
            <Button type="submit" disabled={saving}>{saving ? 'Salvando...' : 'Salvar'}</Button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={messageModalOpen}
        onClose={() => setMessageModalOpen(false)}
        title={editingMessage ? 'Editar mensagem' : 'Nova mensagem do mural'}
      >
        <form className="space-y-3" onSubmit={submitMessage}>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Titulo</label>
            <input
              required
              value={messageForm.title}
              onChange={(e) => setMessageForm((prev) => ({ ...prev, title: e.target.value }))}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Mensagem</label>
            <textarea
              required
              value={messageForm.message}
              onChange={(e) => setMessageForm((prev) => ({ ...prev, message: e.target.value }))}
              className="h-24 w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Corban alvo</label>
            <SearchSelect
              placeholder="Todos os corbans"
              allowEmpty
              value={messageForm.company}
              options={companyOptions}
              onChange={(e) => setMessageForm((prev) => ({ ...prev, company: e.target.value }))}
            />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Inicio de exibicao</label>
              <input
                type="datetime-local"
                value={messageForm.starts_at}
                onChange={(e) => setMessageForm((prev) => ({ ...prev, starts_at: e.target.value }))}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Fim de exibicao</label>
              <input
                type="datetime-local"
                value={messageForm.ends_at}
                onChange={(e) => setMessageForm((prev) => ({ ...prev, ends_at: e.target.value }))}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Ordem</label>
            <input
              type="number"
              value={messageForm.display_order}
              onChange={(e) => setMessageForm((prev) => ({ ...prev, display_order: Number(e.target.value || 0) }))}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <label className="inline-flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={messageForm.is_active}
              onChange={(e) => setMessageForm((prev) => ({ ...prev, is_active: e.target.checked }))}
            />
            Ativa
          </label>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setMessageModalOpen(false)}>Cancelar</Button>
            <Button type="submit" disabled={saving}>{saving ? 'Salvando...' : 'Salvar'}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
