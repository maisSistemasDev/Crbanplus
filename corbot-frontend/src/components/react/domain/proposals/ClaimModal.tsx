import { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';

import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import type { Company, PaginatedResponse } from '../../../../lib/api/types';
import { formatCurrency } from '../../../../lib/utils/format';
import { Modal } from '../../ui/Modal';
import { Button } from '../../ui/Button';
import { SearchSelect } from '../../ui/SearchSelect';

type ClaimType = 'fraude' | 'pago_corban_errado';

export interface ClaimProposal {
  id: string;
  contract_number: string;
  client_name: string;
  amount: number;
  company_name?: string;
}

interface ClaimModalProps {
  isOpen: boolean;
  onClose: () => void;
  proposal: ClaimProposal | null;
  onSuccess: () => void;
}

const CLAIM_OPTIONS: Array<{ value: ClaimType; label: string; description: string }> = [
  {
    value: 'fraude',
    label: 'Fraude confirmada',
    description: 'Gera débito no corban da proposta, no valor da proposta.',
  },
  {
    value: 'pago_corban_errado',
    label: 'Pago ao corban errado',
    description:
      'Gera débito no corban que recebeu, vincula o corban correto e devolve a proposta para "Aguardando pagamento".',
  },
];

export function ClaimModal({ isOpen, onClose, proposal, onSuccess }: ClaimModalProps) {
  const [claimType, setClaimType] = useState<ClaimType>('fraude');
  const [correctCompany, setCorrectCompany] = useState('');
  const [description, setDescription] = useState('');
  const [companies, setCompanies] = useState<Company[]>([]);
  const [saving, setSaving] = useState(false);

  const companyOptions = useMemo(
    () =>
      companies.map((company) => ({
        value: String(company.id),
        label: company.document ? `${company.name} - ${company.document}` : company.name,
      })),
    [companies],
  );

  useEffect(() => {
    if (!isOpen) return;
    setClaimType('fraude');
    setCorrectCompany('');
    setDescription('');
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || claimType !== 'pago_corban_errado' || companies.length > 0) return;

    api
      .get<PaginatedResponse<Company> | Company[]>(`${ENDPOINTS.COMPANIES}?page_size=500`)
      .then((res) => setCompanies(Array.isArray(res) ? res : res.results))
      .catch((error) => toast.error(extractErrorMessage(error)));
  }, [isOpen, claimType, companies.length]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!proposal) return;

    if (claimType === 'pago_corban_errado' && !correctCompany) {
      toast.error('Selecione o corban correto.');
      return;
    }

    setSaving(true);
    try {
      await api.post(ENDPOINTS.CLAIMS, {
        proposal: proposal.id,
        claim_type: claimType,
        description: description.trim(),
        ...(claimType === 'pago_corban_errado' ? { correct_company: correctCompany } : {}),
      });
      toast.success('Sinistro registrado e débito gerado.');
      onSuccess();
      onClose();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Registrar sinistro" size="lg">
      {proposal && (
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="rounded-lg bg-gray-50 p-3 text-sm">
            <p className="font-medium text-gray-900">
              Proposta {proposal.contract_number || proposal.id}
            </p>
            <p className="text-xs text-gray-500">
              {proposal.client_name || 'Cliente não informado'}
              {proposal.company_name ? ` · ${proposal.company_name}` : ''} ·{' '}
              {formatCurrency(proposal.amount)}
            </p>
          </div>

          <div className="space-y-2">
            {CLAIM_OPTIONS.map((option) => (
              <label
                key={option.value}
                className={`flex cursor-pointer items-start gap-2 rounded-lg border p-3 text-sm ${
                  claimType === option.value
                    ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/5'
                    : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                <input
                  type="radio"
                  name="claim_type"
                  value={option.value}
                  checked={claimType === option.value}
                  onChange={() => setClaimType(option.value)}
                  className="mt-0.5"
                />
                <span>
                  <span className="font-medium text-gray-800">{option.label}</span>
                  <span className="block text-xs text-gray-500">{option.description}</span>
                </span>
              </label>
            ))}
          </div>

          {claimType === 'pago_corban_errado' && (
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Corban correto</label>
              <SearchSelect
                required
                placeholder="Selecione"
                value={correctCompany}
                options={companyOptions}
                onChange={(e) => setCorrectCompany(e.target.value)}
              />
            </div>
          )}

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Observações</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Descreva o que foi apurado"
              className="h-24 w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? 'Registrando...' : 'Registrar sinistro'}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}
