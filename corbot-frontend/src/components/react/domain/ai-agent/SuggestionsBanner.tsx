import { useState, useEffect, useCallback } from 'react';
import { Lightbulb, CheckCircle, XCircle, ChevronDown, ChevronUp } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import type { TableUpdateSuggestion } from '../../../../lib/api/types';

interface Props {
  /** Filtra sugestões pelo grupo. Omitir para mostrar todas. */
  groupId?: number;
  onApplied?: () => void;
}

export function SuggestionsBanner({ groupId, onApplied }: Props) {
  const [suggestions, setSuggestions] = useState<TableUpdateSuggestion[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [processing, setProcessing] = useState<number | null>(null);

  const fetchSuggestions = useCallback(async () => {
    try {
      const params = new URLSearchParams({ status: 'pending' });
      if (groupId) params.set('group', String(groupId));
      const res = await api.get<TableUpdateSuggestion[]>(
        `${ENDPOINTS.AI_SUGGESTIONS}?${params}`,
      );
      setSuggestions(Array.isArray(res) ? res : []);
    } catch {
      // silencia — usuário pode não ter sugestões ainda
    }
  }, [groupId]);

  useEffect(() => {
    fetchSuggestions();
  }, [fetchSuggestions]);

  if (suggestions.length === 0) return null;

  async function handleAccept(id: number) {
    setProcessing(id);
    try {
      await api.post(ENDPOINTS.AI_SUGGESTION_ACCEPT(id), {});
      toast.success('Sugestão aplicada com sucesso!');
      setSuggestions((prev) => prev.filter((s) => s.id !== id));
      onApplied?.();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  async function handleReject(id: number) {
    setProcessing(id);
    try {
      await api.post(ENDPOINTS.AI_SUGGESTION_REJECT(id), {});
      toast.success('Sugestão descartada.');
      setSuggestions((prev) => prev.filter((s) => s.id !== id));
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setProcessing(null);
    }
  }

  return (
    <div
      className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4"
      data-tour="pending-suggestions-badge"
    >
      <div className="flex items-center gap-2 mb-3">
        <Lightbulb size={18} className="text-amber-500 shrink-0" />
        <span className="font-semibold text-amber-800 text-sm">
          {suggestions.length === 1
            ? '1 sugestão de configuração pendente'
            : `${suggestions.length} sugestões de configuração pendentes`}
        </span>
      </div>

      <div className="space-y-3">
        {suggestions.map((s) => (
          <div
            key={s.id}
            className="rounded-lg bg-white border border-amber-100 shadow-sm"
            data-tour="suggestion-card"
          >
            {/* Cabeçalho do card */}
            <div className="flex items-center justify-between px-4 py-3">
              <div>
                <p className="font-medium text-gray-800 text-sm">
                  {s.commission_group_name}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  Tabela: <span className="font-medium">{s.table_name}</span>{' '}
                  — {s.bank_name}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setExpanded(expanded === s.id ? null : s.id)}
                  className="text-xs text-amber-600 hover:text-amber-800 flex items-center gap-1"
                >
                  {expanded === s.id ? (
                    <>Ocultar <ChevronUp size={14} /></>
                  ) : (
                    <>Ver detalhes <ChevronDown size={14} /></>
                  )}
                </button>
                <button
                  onClick={() => handleReject(s.id)}
                  disabled={processing === s.id}
                  className="flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 disabled:opacity-50 transition-colors"
                >
                  <XCircle size={13} />
                  Rejeitar
                </button>
                <button
                  onClick={() => handleAccept(s.id)}
                  disabled={processing === s.id}
                  data-tour="accept-suggestion-btn"
                  className="flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50 transition-colors"
                >
                  <CheckCircle size={13} />
                  Aceitar
                </button>
              </div>
            </div>

            {/* Detalhes expandidos */}
            {expanded === s.id && (
              <div className="border-t border-amber-50 px-4 py-3 space-y-3">
                <p className="text-xs text-gray-600 leading-relaxed">{s.ai_reasoning}</p>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <p className="font-medium text-gray-500 mb-1">Configuração atual</p>
                    <pre className="bg-gray-50 rounded p-2 text-gray-700 overflow-auto max-h-32 text-[11px]">
                      {JSON.stringify(s.old_config, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <p className="font-medium text-green-600 mb-1">Sugestão da IA</p>
                    <pre className="bg-green-50 rounded p-2 text-green-800 overflow-auto max-h-32 text-[11px]">
                      {JSON.stringify(s.suggested_config, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
