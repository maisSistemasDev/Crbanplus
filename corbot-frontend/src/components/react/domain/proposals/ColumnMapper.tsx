import { useState, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { FileUpload } from '../../ui/FileUpload';
import { Select } from '../../ui/Select';
import { Input } from '../../ui/Input';
import { Button } from '../../ui/Button';
import { Badge } from '../../ui/Badge';
import { Check, Sparkles, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import type { FileColumn, ModelField } from '../../../../lib/api/types';
import { FieldMappingPanels } from './field-mapping/FieldMappingPanels';
import { useFieldMapping } from './field-mapping/useFieldMapping';

export function ColumnMapper() {
  const [step, setStep] = useState<'upload' | 'mapping' | 'saving'>('upload');
  const [fileColumns, setFileColumns] = useState<FileColumn[]>([]);
  const [modelFields, setModelFields] = useState<ModelField[]>([]);
  const [bankId, setBankId] = useState('');
  const [layoutName, setLayoutName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [suggesting, setSuggesting] = useState(false);

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
  } = useFieldMapping(fileColumns);

  const requiredOk = allRequiredMapped(modelFields);

  const handleFileSelect = useCallback(async (file: File) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await api.upload<{
        columns_order: FileColumn[];
        model_fields: ModelField[];
        proposal_file_id?: string;
      }>(ENDPOINTS.PREVIEW_ROWS, formData);

      setFileColumns(response.columns_order);
      setModelFields(response.model_fields);
      resetMappings();
      setStep('mapping');
      toast.success('Arquivo processado com sucesso!');
    } catch {
      toast.error('Erro ao processar arquivo');
    } finally {
      setUploading(false);
    }
  }, [resetMappings]);

  async function handleAiSuggest() {
    setSuggesting(true);
    try {
      const res = await api.post<{ mappings: Record<string, { index: number; name: string; data_type: string }[]> }>(
        ENDPOINTS.AI_SUGGEST_MAPPING,
        { columns: fileColumns, fields: modelFields },
      );
      const suggested = res.mappings;
      if (!suggested || Object.keys(suggested).length === 0) {
        toast.error('A IA não encontrou sugestões para este arquivo.');
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

  async function handleSave() {
    if (!bankId) {
      toast.error('Selecione um banco');
      return;
    }
    if (!layoutName) {
      toast.error('Digite um nome para o layout');
      return;
    }
    if (!requiredOk) {
      toast.error('Mapeie todos os campos obrigatorios');
      return;
    }

    // Validação específica: pelo menos um dos campos Digitador ou Acessos deve estar mapeado
    const mappedNames = new Set(Object.keys(mappings));
    if (!mappedNames.has('digitador') && !mappedNames.has('bank_access')) {
      toast.error('Mapeie pelo menos "Digitador" ou "Acessos" no layout');
      return;
    }

    setSaving(true);
    try {
      await api.post(ENDPOINTS.LAYOUTS, {
        bank: bankId,
        name: layoutName,
        mapping: mappings,
      });
      toast.success('Layout salvo com sucesso!');
      setStep('saving');
    } catch {
      toast.error('Erro ao salvar layout');
    } finally {
      setSaving(false);
    }
  }

  if (step === 'upload') {
    return (
      <div>
        <h1 className="page-title mb-4">Criar layout de importação</h1>
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 max-w-xl mx-auto">
          <h2 className="text-lg font-semibold mb-4">1. Selecione o Banco</h2>
          <Select
            label="Banco"
            options_url={ENDPOINTS.BANKS}
            value={bankId}
            onChange={(e) => setBankId(e.target.value)}
            required
          />
          <h2 className="text-lg font-semibold mt-6 mb-4">2. Envie o arquivo</h2>
          <FileUpload
            accept=".xlsx,.xls,.csv"
            onFileSelect={handleFileSelect}
            label="Arquivo de propostas"
          />
          {uploading && (
            <div className="mt-4 flex items-center gap-2 text-sm text-gray-500">
              <div className="animate-spin h-4 w-4 border-2 border-[var(--color-primary)] border-t-transparent rounded-full" />
              Processando arquivo...
            </div>
          )}
        </div>
      </div>
    );
  }

  if (step === 'saving') {
    return (
      <div className="text-center py-12">
        <div className="inline-flex items-center justify-center h-16 w-16 rounded-full bg-green-100 mb-4">
          <Check size={32} className="text-green-600" />
        </div>
        <h2 className="section-title mb-2">Layout criado com sucesso!</h2>
        <p className="text-gray-500 mb-6">O layout foi salvo e pode ser usado para importar propostas.</p>
        <div className="flex gap-3 justify-center">
          <Button variant="secondary" onClick={() => { setStep('upload'); resetMappings(); setFileColumns([]); setModelFields([]); }}>
            Criar Outro
          </Button>
          <a href="/proposals/batches/upload">
            <Button>Importar Propostas</Button>
          </a>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="page-title">Mapear colunas</h1>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleAiSuggest}
            disabled={suggesting}
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {suggesting ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
            Sugestão da IA
          </button>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-500">
              {Object.keys(mappings).length} / {modelFields.length} campos mapeados
            </span>
            {requiredOk ? (
              <Badge variant="success">Pronto</Badge>
            ) : (
              <Badge variant="warning">Campos obrigatorios pendentes</Badge>
            )}
          </div>
        </div>
      </div>

      <div className="mb-6">
        <FieldMappingPanels
          modelFields={modelFields}
          sourceColumns={fileColumns}
          sourcePanelTitle="Colunas do Arquivo"
          mappings={mappings}
          selectedDbField={selectedDbField}
          onDbFieldClick={handleDbFieldClick}
          onSourceColumnClick={handleSourceColumnClick}
          onRemoveMapping={handleRemoveMapping}
          onClearFieldMapping={handleClearFieldMapping}
          getMappingColorIndex={getMappingColorIndex}
          isSourceColumnMapped={isSourceColumnMapped}
        />
      </div>

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
            placeholder="Ex: Layout BMG INSS"
            required
          />
          <Button onClick={handleSave} loading={saving} disabled={!requiredOk}>
            Salvar Layout
          </Button>
        </div>
      </div>
    </div>
  );
}
