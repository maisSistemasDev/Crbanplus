import { useState, useEffect, useMemo } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { extractErrorMessage } from '../../../../lib/api/errors';
import { Button } from '../../ui/Button';
import { Input } from '../../ui/Input';
import clsx from 'clsx';
import { Search, ChevronRight, ChevronLeft, Building, Check } from 'lucide-react';
import toast from 'react-hot-toast';
import type { Company } from '../../../../lib/api/types';

interface CompanySelectorProps {
  groupId: number;
  initialCompanyIds: string[];
  onUpdate?: () => void;
}

export function CompanySelector({ groupId, initialCompanyIds, onUpdate }: CompanySelectorProps) {
  const [allCompanies, setAllCompanies] = useState<Company[]>([]);
  const [linkedCompanyIds, setLinkedCompanyIds] = useState<string[]>(initialCompanyIds);
  const [selectedAvailable, setSelectedAvailable] = useState<Set<string>>(new Set());
  const [selectedLinked, setSelectedLinked] = useState<Set<string>>(new Set());
  const [searchAvailable, setSearchAvailable] = useState('');
  const [searchLinked, setSearchLinked] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const companies = await api.get<Company[]>(ENDPOINTS.COMPANIES);
        const companiesList = Array.isArray(companies) ? companies : (companies as any).results || [];
        setAllCompanies(companiesList);
      } catch (error) {
        toast.error(extractErrorMessage(error));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Split companies into available and linked
  const availableCompanies = useMemo(() => {
    return allCompanies.filter((c) => !linkedCompanyIds.includes(c.id));
  }, [allCompanies, linkedCompanyIds]);

  const linkedCompanies = useMemo(() => {
    return allCompanies.filter((c) => linkedCompanyIds.includes(c.id));
  }, [allCompanies, linkedCompanyIds]);

  // Filter by search
  const filteredAvailable = useMemo(() => {
    if (!searchAvailable) return availableCompanies;
    const q = searchAvailable.toLowerCase();
    return availableCompanies.filter(
      (c) => c.name.toLowerCase().includes(q) || (c.cnpj && c.cnpj.includes(q))
    );
  }, [availableCompanies, searchAvailable]);

  const filteredLinked = useMemo(() => {
    if (!searchLinked) return linkedCompanies;
    const q = searchLinked.toLowerCase();
    return linkedCompanies.filter(
      (c) => c.name.toLowerCase().includes(q) || (c.cnpj && c.cnpj.includes(q))
    );
  }, [linkedCompanies, searchLinked]);

  function toggleAvailableSelection(companyId: string) {
    setSelectedAvailable((prev) => {
      const next = new Set(prev);
      if (next.has(companyId)) next.delete(companyId);
      else next.add(companyId);
      return next;
    });
  }

  function toggleLinkedSelection(companyId: string) {
    setSelectedLinked((prev) => {
      const next = new Set(prev);
      if (next.has(companyId)) next.delete(companyId);
      else next.add(companyId);
      return next;
    });
  }

  function handleAddToLinked() {
    if (selectedAvailable.size === 0) return;
    setLinkedCompanyIds((prev) => [...prev, ...Array.from(selectedAvailable)]);
    setSelectedAvailable(new Set());
  }

  function handleRemoveFromLinked() {
    if (selectedLinked.size === 0) return;
    setLinkedCompanyIds((prev) => prev.filter((id) => !selectedLinked.has(id)));
    setSelectedLinked(new Set());
  }

  async function handleSave() {
    setSaving(true);
    try {
      await api.put(ENDPOINTS.COMMISSION_GROUP_BY_COMPANY_COMPANIES(groupId), {
        companies: linkedCompanyIds,
      });
      toast.success('Corbans atualizados com sucesso!');
      onUpdate?.();
    } catch (error) {
      toast.error(extractErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin h-8 w-8 border-4 border-[var(--color-primary)] border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
        <h3 className="font-semibold text-gray-800">Gerenciar Corbans</h3>
        <Button size="sm" onClick={handleSave} loading={saving}>
          <Check size={14} />
          Salvar
        </Button>
      </div>

      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto_1fr] gap-4">
          {/* Available Companies */}
          <div className="flex flex-col">
            <div className="mb-3 flex items-center justify-between">
              <h4 className="text-sm font-medium text-gray-700">
                Disponíveis ({filteredAvailable.length})
              </h4>
            </div>
            <div className="relative mb-3">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <Input
                placeholder="Buscar corbans..."
                value={searchAvailable}
                onChange={(e) => setSearchAvailable(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="border border-gray-200 rounded-lg overflow-hidden flex-1 min-h-[300px] max-h-[400px] overflow-y-auto">
              {filteredAvailable.length === 0 ? (
                <div className="flex items-center justify-center h-full text-sm text-gray-400">
                  {searchAvailable ? 'Nenhum corban encontrado' : 'Todos corbans vinculados'}
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {filteredAvailable.map((company) => (
                    <button
                      key={company.id}
                      onClick={() => toggleAvailableSelection(company.id)}
                      className={clsx(
                        'w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors flex items-center gap-3',
                        selectedAvailable.has(company.id) && 'bg-blue-50 hover:bg-blue-100'
                      )}
                    >
                      <div
                        className={clsx(
                          'w-5 h-5 rounded border-2 flex items-center justify-center transition-colors',
                          selectedAvailable.has(company.id)
                            ? 'bg-[var(--color-primary)] border-[var(--color-primary)]'
                            : 'border-gray-300'
                        )}
                      >
                        {selectedAvailable.has(company.id) && (
                          <Check size={12} className="text-white" />
                        )}
                      </div>
                      <Building size={16} className="text-gray-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{company.name}</p>
                        {company.cnpj && (
                          <p className="text-xs text-gray-500">{company.cnpj}</p>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Control Buttons */}
          <div className="flex lg:flex-col items-center justify-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleAddToLinked}
              disabled={selectedAvailable.size === 0}
              className="lg:rotate-0 rotate-90"
            >
              <ChevronRight size={16} />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRemoveFromLinked}
              disabled={selectedLinked.size === 0}
              className="lg:rotate-0 -rotate-90"
            >
              <ChevronLeft size={16} />
            </Button>
          </div>

          {/* Linked Companies */}
          <div className="flex flex-col">
            <div className="mb-3 flex items-center justify-between">
              <h4 className="text-sm font-medium text-gray-700">
                Vinculadas ({filteredLinked.length})
              </h4>
            </div>
            <div className="relative mb-3">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <Input
                placeholder="Buscar corbans..."
                value={searchLinked}
                onChange={(e) => setSearchLinked(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="border border-gray-200 rounded-lg overflow-hidden flex-1 min-h-[300px] max-h-[400px] overflow-y-auto">
              {filteredLinked.length === 0 ? (
                <div className="flex items-center justify-center h-full text-sm text-gray-400">
                  {searchLinked ? 'Nenhum corban encontrado' : 'Nenhum corban vinculado'}
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {filteredLinked.map((company) => (
                    <button
                      key={company.id}
                      onClick={() => toggleLinkedSelection(company.id)}
                      className={clsx(
                        'w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors flex items-center gap-3',
                        selectedLinked.has(company.id) && 'bg-blue-50 hover:bg-blue-100'
                      )}
                    >
                      <div
                        className={clsx(
                          'w-5 h-5 rounded border-2 flex items-center justify-center transition-colors',
                          selectedLinked.has(company.id)
                            ? 'bg-[var(--color-primary)] border-[var(--color-primary)]'
                            : 'border-gray-300'
                        )}
                      >
                        {selectedLinked.has(company.id) && (
                          <Check size={12} className="text-white" />
                        )}
                      </div>
                      <Building size={16} className="text-gray-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{company.name}</p>
                        {company.cnpj && (
                          <p className="text-xs text-gray-500">{company.cnpj}</p>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
