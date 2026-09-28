import { useEffect, useMemo, useState } from 'react';
import { Sparkles, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import type { EtlMappingApplyResult } from '../../../../lib/api/types/etl';
import type { EtlFieldMapping } from '../../../../lib/api/types/etl';
import type { ModelField } from '../../../../lib/api/types';
import { flattenJsonLeaves } from '../../../../lib/etl/jsonPath';
import {
  etlMappingsToFieldMappings,
  fieldMappingsToEtlMappings,
  jsonLeavesToFileColumns,
} from '../../../../lib/etl/fieldMappingConvert';
import { FieldMappingPanels } from '../proposals/field-mapping/FieldMappingPanels';
import { useFieldMapping } from '../proposals/field-mapping/useFieldMapping';
import { Modal } from '../../ui/Modal';
import { Button } from '../../ui/Button';
import { Badge } from '../../ui/Badge';
import { Select } from '../../ui/Select';
import { Input } from '../../ui/Input';

interface EtlFieldMappingModalProps {
  open: boolean;
  onClose: () => void;
  sampleItem: Record<string, unknown>;
  itemsPath: string;
  modelFields: ModelField[];
  initialMappings?: EtlFieldMapping[];
  defaultBankId?: string;
  defaultLayoutName?: string;
  onApply: (result: EtlMappingApplyResult) => void;
}

export function EtlFieldMappingModal({
  open,
  onClose,
  sampleItem,
  itemsPath,
  modelFields,
  initialMappings = [],
  defaultBankId = '',
  defaultLayoutName = '',
  onApply,
}: EtlFieldMappingModalProps) {
  const [suggesting, setSuggesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [bankId, setBankId] = useState(defaultBankId);
  const [layoutName, setLayoutName] = useState(defaultLayoutName);

  const jsonFields = useMemo(() => flattenJsonLeaves(sampleItem), [sampleItem]);
  const sourceColumns = useMemo(() => jsonLeavesToFileColumns(jsonFields), [jsonFields]);

  const {
    mappings,
    setMappings,
    selectedDbField,
    handleDbFieldClick,
    handleSourceColumnClick,
    handleRemoveMapping,
    handleClearFieldMapping,
    getMappingColorIndex,
    isSourceColumnMapped,
    allRequiredMapped,
    resetMappings,
  } = useFieldMapping(sourceColumns);

  const requiredOk = allRequiredMapped(modelFields);

  useEffect(() => {
    if (!open) return;
    resetMappings(etlMappingsToFieldMappings(initialMappings, sourceColumns));
    setBankId(defaultBankId);
    setLayoutName(defaultLayoutName);
  }, [open, initialMappings, defaultBankId, defaultLayoutName, sourceColumns, resetMappings]);

  async function handleAiSuggest() {
    if (!modelFields.length || !sourceColumns.length) return;
    setSuggesting(true);
    try {
      const res = await api.post<{
        mappings: Record<string, { index: number; name: string; data_type: string }[]>;
      }>(ENDPOINTS.AI_SUGGEST_MAPPING, { columns: sourceColumns, fields: modelFields });

      const suggested = res.mappings;
      if (!suggested || Object.keys(suggested).length === 0) {
        toast.error('A IA não encontrou sugestões para esta resposta.');
        return;
      }
      setMappings(suggested);
      const count = Object.keys(suggested).length;
      toast.success(`${count} campo${count !== 1 ? 's' : ''} mapeado${count !== 1 ? 's' : ''} automaticamente!`);
    } catch {
      toast.error('Erro ao buscar sugestão da IA.');
    } finally {
      setSuggesting(false);
    }
  }

  async function handleApply() {
    if (!bankId) {
      toast.error('Selecione um banco');
      return;
    }
    if (!layoutName.trim()) {
      toast.error('Digite um nome para o layout');
      return;
    }
    if (!requiredOk) {
      toast.error('Mapeie todos os campos obrigatórios');
      return;
    }

    setSaving(true);
    try {
      const res = await api.post<{ layout: string }>(ENDPOINTS.LAYOUTS, {
        bank: bankId,
        name: layoutName.trim(),
        mapping: mappings,
      });

      onApply({
        mappings: fieldMappingsToEtlMappings(mappings),
        layoutId: res.layout,
        layoutName: layoutName.trim(),
        bankId,
        itemsPath,
      });
      onClose();
      toast.success('Layout criado e mapeamento aplicado ao fluxo.');
    } catch {
      toast.error('Erro ao criar layout');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Mapear colunas da API" size="xl">
      <div className="p-4 space-y-4 max-h-[80vh] overflow-y-auto">
        <p className="text-sm text-gray-600">
          Amostra do <strong>primeiro item</strong> da lista
          {itemsPath ? (
            <> em <code className="bg-gray-100 px-1 rounded text-xs">{itemsPath}</code></>
          ) : null}
          . O layout será criado ao salvar, igual à importação por arquivo.
        </p>

        <details className="text-xs bg-gray-50 rounded-lg p-2">
          <summary className="cursor-pointer font-medium text-gray-700">Preview do item JSON</summary>
          <pre className="mt-2 overflow-auto max-h-32 text-[10px]">
            {JSON.stringify(sampleItem, null, 2)}
          </pre>
        </details>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleAiSuggest}
            disabled={suggesting || !modelFields.length}
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {suggesting ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
            Sugestão da IA
          </button>
          <span className="text-sm text-gray-500">
            {Object.keys(mappings).length} / {modelFields.length} campos mapeados
          </span>
          {requiredOk ? (
            <Badge variant="success">Pronto</Badge>
          ) : (
            <Badge variant="warning">Campos obrigatórios pendentes</Badge>
          )}
        </div>

        {modelFields.length === 0 ? (
          <p className="text-sm text-amber-700 bg-amber-50 rounded-lg p-3">
            Carregando campos do sistema...
          </p>
        ) : (
          <FieldMappingPanels
            modelFields={modelFields}
            sourceColumns={sourceColumns}
            sourcePanelTitle="Campos da API (1º item)"
            mappings={mappings}
            selectedDbField={selectedDbField}
            onDbFieldClick={handleDbFieldClick}
            onSourceColumnClick={handleSourceColumnClick}
            onRemoveMapping={handleRemoveMapping}
            onClearFieldMapping={handleClearFieldMapping}
            getMappingColorIndex={getMappingColorIndex}
            isSourceColumnMapped={isSourceColumnMapped}
          />
        )}

        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
          <h3 className="font-semibold text-sm text-gray-700 mb-4">Salvar Layout</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <Select
              label="Banco"
              options_url={ENDPOINTS.BANKS}
              value={bankId}
              onChange={(e) => setBankId(e.target.value)}
              required
            />
            <Input
              label="Nome do Layout"
              value={layoutName}
              onChange={(e) => setLayoutName(e.target.value)}
              placeholder="Ex: Layout API Unnotech"
              required
            />
            <Button onClick={handleApply} loading={saving} disabled={!requiredOk || !modelFields.length}>
              Criar layout e aplicar
            </Button>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
          <Button variant="secondary" onClick={onClose}>Cancelar</Button>
        </div>
      </div>
    </Modal>
  );
}
