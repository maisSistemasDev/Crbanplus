import { useCallback, useEffect, useState } from 'react';
import { Check, Clipboard, Link2, Plus, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { Button } from '../../ui/Button';

interface RegistrationLink {
  id: string;
  expires_at: string | null;
  max_uses: number | null;
  uses_count: number;
  is_active: boolean;
  is_usable: boolean;
  created_at: string;
}

interface CreatedRegistrationLink extends RegistrationLink {
  token: string;
  url: string;
}

export function RegistrationLinksPanel({ groupId }: { groupId: number }) {
  const [links, setLinks] = useState<RegistrationLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [createdUrl, setCreatedUrl] = useState('');
  const [expiresAt, setExpiresAt] = useState('');
  const [maxUses, setMaxUses] = useState('');

  const loadLinks = useCallback(async () => {
    try {
      const data = await api.get<RegistrationLink[]>(
        ENDPOINTS.COMMISSION_GROUP_REGISTRATION_LINKS(groupId),
      );
      setLinks(data);
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [groupId]);

  useEffect(() => {
    void loadLinks();
  }, [loadLinks]);

  async function handleCreate() {
    setCreating(true);
    try {
      const result = await api.post<CreatedRegistrationLink>(
        ENDPOINTS.COMMISSION_GROUP_REGISTRATION_LINKS(groupId),
        {
          expires_at: expiresAt ? new Date(`${expiresAt}T23:59:59`).toISOString() : null,
          max_uses: maxUses ? Number(maxUses) : null,
        },
      );
      const publicUrl = `${window.location.origin}/cadastro/grupo/${result.token}`;
      setCreatedUrl(publicUrl);
      setCopied(false);
      setExpiresAt('');
      setMaxUses('');
      toast.success('Link de cadastro criado.');
      await loadLinks();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setCreating(false);
    }
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(createdUrl);
      setCopied(true);
      toast.success('Link copiado.');
    } catch {
      toast.error('Não foi possível copiar o link.');
    }
  }

  async function handleRevoke(linkId: string) {
    if (!window.confirm('Revogar este link de cadastro?')) return;
    try {
      await api.delete(
        ENDPOINTS.COMMISSION_GROUP_REGISTRATION_LINK_DETAIL(groupId, linkId),
      );
      toast.success('Link revogado.');
      await loadLinks();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    }
  }

  const activeLinks = links.filter((link) => link.is_active);

  return (
    <section className="mb-6 rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Link2 size={18} className="text-[var(--color-primary)]" />
            <h2 className="font-semibold text-gray-800">Link de cadastro da equipe</h2>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Quem se cadastrar por este link entra automaticamente nesta equipe.
          </p>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <label className="text-xs text-gray-600">
            Expira em
            <input
              type="date"
              value={expiresAt}
              onChange={(event) => setExpiresAt(event.target.value)}
              className="mt-1 block rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-700"
            />
          </label>
          <label className="text-xs text-gray-600">
            Limite de cadastros
            <input
              type="number"
              min={1}
              value={maxUses}
              onChange={(event) => setMaxUses(event.target.value)}
              placeholder="Sem limite"
              className="mt-1 block w-40 rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-700"
            />
          </label>
          <Button size="md" onClick={handleCreate} loading={creating}>
            <Plus size={15} />
            Gerar link
          </Button>
        </div>
      </div>

      {createdUrl && (
        <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-3">
          <p className="mb-2 text-xs font-medium text-green-800">
            Copie agora: por segurança, o endereço completo é exibido somente na criação.
          </p>
          <div className="flex gap-2">
            <input
              readOnly
              value={createdUrl}
              onFocus={(event) => event.currentTarget.select()}
              className="min-w-0 flex-1 rounded-lg border border-green-200 bg-white px-3 py-2 text-sm text-gray-700"
            />
            <Button variant="secondary" onClick={handleCopy}>
              {copied ? <Check size={15} /> : <Clipboard size={15} />}
              {copied ? 'Copiado' : 'Copiar'}
            </Button>
          </div>
        </div>
      )}

      <div className="mt-4 border-t border-gray-100 pt-4">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">
          Links gerados
        </p>
        {loading ? (
          <p className="text-sm text-gray-400">Carregando...</p>
        ) : links.length === 0 ? (
          <p className="text-sm text-gray-400">Nenhum link gerado para esta equipe.</p>
        ) : (
          <div className="space-y-2">
            {links.map((link) => (
              <div
                key={link.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-gray-50 px-3 py-2"
              >
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-600">
                  <span>
                    Criado em {new Date(link.created_at).toLocaleString('pt-BR')}
                  </span>
                  <span>
                    Usos: {link.uses_count}
                    {link.max_uses !== null ? `/${link.max_uses}` : ''}
                  </span>
                  <span>
                    {link.expires_at
                      ? `Expira em ${new Date(link.expires_at).toLocaleDateString('pt-BR')}`
                      : 'Sem expiração'}
                  </span>
                  <span
                    className={
                      link.is_usable
                        ? 'rounded-full bg-green-100 px-2 py-0.5 text-green-700'
                        : 'rounded-full bg-gray-200 px-2 py-0.5 text-gray-500'
                    }
                  >
                    {link.is_usable ? 'Ativo' : 'Inativo'}
                  </span>
                </div>
                {link.is_active && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRevoke(link.id)}
                    title="Revogar link"
                  >
                    <Trash2 size={14} className="text-red-500" />
                    Revogar
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
        {activeLinks.length > 1 && (
          <p className="mt-2 text-xs text-amber-600">
            Há {activeLinks.length} links ativos para esta equipe.
          </p>
        )}
      </div>
    </section>
  );
}
