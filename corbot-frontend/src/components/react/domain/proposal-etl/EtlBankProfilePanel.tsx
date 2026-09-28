import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { api, ApiError } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import type { ProposalEtlBankProfile } from '../../../../lib/api/types/etl';
import { Button } from '../../ui/Button';

interface EtlBankProfilePanelProps {
  bankId: string;
  flowId: string;
  onProfileApplied: () => void;
}

export function EtlBankProfilePanel({ bankId, flowId, onProfileApplied }: EtlBankProfilePanelProps) {
  const [profile, setProfile] = useState<ProposalEtlBankProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [applying, setApplying] = useState(false);

  const loadProfile = useCallback(async () => {
    if (!bankId) return;
    setLoading(true);
    try {
      const res = await api.get<ProposalEtlBankProfile>(ENDPOINTS.PROPOSAL_ETL_BANK_PROFILE(bankId));
      setProfile(res);
    } catch {
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, [bankId]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const hasSettings = Boolean(
    profile?.settings?.paginate_http
    || profile?.settings?.extract_items
    || (profile?.settings?.detail_steps?.length ?? 0) > 0,
  );

  async function handleSaveFromFlow() {
    setSaving(true);
    try {
      const res = await api.post<ProposalEtlBankProfile>(
        ENDPOINTS.PROPOSAL_ETL_BANK_PROFILE(bankId),
        { action: 'extract_from_flow', flow_id: flowId },
      );
      setProfile(res);
      toast.success('Perfil do banco salvo a partir deste fluxo.');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Erro ao salvar perfil.');
    } finally {
      setSaving(false);
    }
  }

  async function handleApplyToFlow() {
    setApplying(true);
    try {
      await api.post(ENDPOINTS.PROPOSAL_ETL_BANK_PROFILE(bankId), {
        action: 'apply_to_flow',
        flow_id: flowId,
      });
      toast.success('Perfil do banco aplicado ao fluxo.');
      onProfileApplied();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Erro ao aplicar perfil.');
    } finally {
      setApplying(false);
    }
  }

  if (!bankId) {
    return (
      <p className="text-xs text-amber-700 bg-amber-50 rounded-lg p-2">
        Selecione um banco para usar perfis ETL personalizados.
      </p>
    );
  }

  return (
    <div className="space-y-2 border-t border-gray-100 pt-3 mt-2">
      <p className="text-xs font-medium text-gray-700">Perfil ETL do banco</p>
      <p className="text-[10px] text-gray-500 leading-snug">
        Salve URL, paginação, auth e detalhes uma vez por banco. Reaplique em novos fluxos.
      </p>

      {loading ? (
        <p className="text-xs text-gray-400">Carregando perfil...</p>
      ) : hasSettings ? (
        <p className="text-[10px] text-green-700 bg-green-50 rounded px-2 py-1">
          Perfil salvo
          {profile?.settings?.detail_steps?.length
            ? ` · ${profile.settings.detail_steps.length} etapa(s) de detalhe`
            : ''}
        </p>
      ) : (
        <p className="text-[10px] text-gray-500">Nenhum perfil salvo ainda para este banco.</p>
      )}

      <Button
        size="sm"
        variant="secondary"
        type="button"
        loading={saving}
        className="w-full"
        onClick={handleSaveFromFlow}
      >
        Salvar fluxo como perfil
      </Button>
      <Button
        size="sm"
        type="button"
        loading={applying}
        disabled={!hasSettings}
        className="w-full"
        onClick={handleApplyToFlow}
      >
        Aplicar perfil ao fluxo
      </Button>
    </div>
  );
}
