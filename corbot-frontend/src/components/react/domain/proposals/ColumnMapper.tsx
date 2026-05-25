import { useState, useCallback } from 'react';
import { api } from '../../../../lib/api/client';
import { ENDPOINTS } from '../../../../lib/api/endpoints';
import { FileUpload } from '../../ui/FileUpload';
import { Select } from '../../ui/Select';
import { Input } from '../../ui/Input';
import { Button } from '../../ui/Button';
import { Badge } from '../../ui/Badge';
import clsx from 'clsx';
import { Link, Unlink, Check, AlertCircle, X } from 'lucide-react';
import toast from 'react-hot-toast';
import type { FileColumn, ModelField, Bank } from '../../../../lib/api/types';

interface Mapping {
  index: number;
  name: string;
  data_type: string;
}

const TYPE_COLORS: Record<string, string> = {
  text: 'bg-blue-100 text-blue-700',
  number: 'bg-purple-100 text-purple-700',
  currency: 'bg-green-100 text-green-700',
  decimal: 'bg-green-100 text-green-700',
  date: 'bg-orange-100 text-orange-700',
  datetime: 'bg-orange-100 text-orange-700',
  cpf: 'bg-yellow-100 text-yellow-700',
  boolean: 'bg-gray-100 text-gray-700',
  email: 'bg-indigo-100 text-indigo-700',
  phone: 'bg-pink-100 text-pink-700',
  ForeignKey: 'bg-cyan-100 text-cyan-700',
  CharField: 'bg-blue-100 text-blue-700',
  DecimalField: 'bg-green-100 text-green-700',
  DateField: 'bg-orange-100 text-orange-700',
};

const MAPPING_COLORS = [
  'bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500',
  'bg-pink-500', 'bg-cyan-500', 'bg-yellow-500', 'bg-red-500',
  'bg-indigo-500', 'bg-teal-500',
];

export function ColumnMapper() {
  const [step, setStep] = useState<'upload' | 'mapping' | 'saving'>('upload');
  const [fileColumns, setFileColumns] = useState<FileColumn[]>([]);
  const [modelFields, setModelFields] = useState<ModelField[]>([]);
  const [mappings, setMappings] = useState<Record<string, Mapping[]>>({});
  const [selectedDbField, setSelectedDbField] = useState<string | null>(null);
  const [bankId, setBankId] = useState('');
  const [layoutName, setLayoutName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [fileId, setFileId] = useState<string | null>(null);

  // Step 1: Upload file and get preview
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
      setFileId(response.proposal_file_id || null);
      setStep('mapping');
      toast.success('Arquivo processado com sucesso!');
    } catch {
      toast.error('Erro ao processar arquivo');
    } finally {
      setUploading(false);
    }
  }, []);

  // Map a DB field to a file column
  function handleDbFieldClick(fieldName: string) {
    if (selectedDbField === fieldName) {
      // Deselect if clicking again
      setSelectedDbField(null);
    } else {
      // Select this field to add more columns
      setSelectedDbField(fieldName);
    }
  }

  function handleFileColumnClick(col: FileColumn) {
    if (!selectedDbField) return;

    // Check if this file column is already mapped to any field
    const existingField = Object.entries(mappings).find(
      ([, mappingList]) => mappingList.some(m => m.index === col.column_index),
    );
    if (existingField) {
      toast.error(`Esta coluna ja esta mapeada para "${existingField[0]}"`);
      return;
    }

    // Add this column to the selected field's mapping list
    setMappings((prev) => ({
      ...prev,
      [selectedDbField]: [
        ...(prev[selectedDbField] || []),
        {
          index: col.column_index,
          name: col.column_name,
          data_type: col.detected_type,
        },
      ],
    }));
    toast.success('Coluna adicionada ao mapeamento');
    // Keep field selected to add more columns
  }

  // Remove a specific column from a field's mapping
  function handleRemoveMapping(fieldName: string, columnIndex: number) {
    setMappings((prev) => {
      const newList = prev[fieldName].filter(m => m.index !== columnIndex);
      if (newList.length === 0) {
        // Remove field if no columns left
        const { [fieldName]: _, ...rest } = prev;
        return rest;
      }
      return {
        ...prev,
        [fieldName]: newList,
      };
    });
    toast.success('Coluna removida do mapeamento');
  }

  // Clear all mappings for a field
  function handleClearFieldMapping(fieldName: string) {
    const newMappings = { ...mappings };
    delete newMappings[fieldName];
    setMappings(newMappings);
    setSelectedDbField(null);
    toast.success('Mapeamento limpo');
  }

  // Get mapping color index for visual pairing
  function getMappingColorIndex(fieldName: string): number {
    const keys = Object.keys(mappings);
    return keys.indexOf(fieldName);
  }

  function isFileColumnMapped(colIndex: number): string | null {
    for (const [field, mappingList] of Object.entries(mappings)) {
      if (mappingList.some(m => m.index === colIndex)) return field;
    }
    return null;
  }

  // Check if all required fields are mapped
  const allRequiredMapped = modelFields
    .filter((f) => f.required)
    .every((f) => mappings[f.name] && mappings[f.name].length > 0);

  // Save layout
  async function handleSave() {
    if (!bankId) {
      toast.error('Selecione um banco');
      return;
    }
    if (!layoutName) {
      toast.error('Digite um nome para o layout');
      return;
    }
    if (!allRequiredMapped) {
      toast.error('Mapeie todos os campos obrigatorios');
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

  // ===== RENDER =====

  if (step === 'upload') {
    return (
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Criar Layout de Importacao</h1>
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
        <h2 className="text-xl font-bold text-gray-900 mb-2">Layout criado com sucesso!</h2>
        <p className="text-gray-500 mb-6">O layout foi salvo e pode ser usado para importar propostas.</p>
        <div className="flex gap-3 justify-center">
          <Button variant="secondary" onClick={() => { setStep('upload'); setMappings({}); setFileColumns([]); setModelFields([]); }}>
            Criar Outro
          </Button>
          <a href="/proposals/batches/upload">
            <Button>Importar Propostas</Button>
          </a>
        </div>
      </div>
    );
  }

  // Step: mapping
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mapear Colunas</h1>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-500">
            {Object.keys(mappings).length} / {modelFields.length} campos mapeados
          </span>
          {allRequiredMapped ? (
            <Badge variant="success">Pronto</Badge>
          ) : (
            <Badge variant="warning">Campos obrigatorios pendentes</Badge>
          )}
        </div>
      </div>

      {/* Two side-by-side panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* LEFT: DB Fields */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
            <h3 className="font-semibold text-sm text-gray-700">Campos do Sistema</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Clique em um campo e depois clique nas colunas do arquivo para mapeá-las.
              <br />
              <span className="text-blue-600">💡 Você pode mapear múltiplas colunas para o mesmo campo</span>
            </p>
          </div>
          <div className="divide-y divide-gray-50 max-h-96 overflow-y-auto">
            {modelFields.map((field) => {
              const mappingList = mappings[field.name] || [];
              const isMapped = mappingList.length > 0;
              const isSelected = selectedDbField === field.name;
              const colorIdx = isMapped ? getMappingColorIndex(field.name) : -1;

              return (
                <div
                  key={field.name}
                  className={clsx(
                    'transition-colors',
                    isSelected && 'bg-[var(--color-primary-bg)] ring-2 ring-inset ring-[var(--color-primary)]',
                    isMapped && !isSelected && 'bg-green-50',
                    !isMapped && !isSelected && 'hover:bg-gray-50',
                  )}
                >
                  <button
                    onClick={() => handleDbFieldClick(field.name)}
                    className="w-full px-4 py-3 text-left flex items-center gap-3"
                  >
                    {isMapped && (
                      <span className={clsx('h-3 w-3 rounded-full shrink-0', MAPPING_COLORS[colorIdx % MAPPING_COLORS.length])} />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-800">{field.verbose_name}</span>
                        {field.required && <AlertCircle size={12} className="text-red-400" />}
                        <span className={clsx('text-[10px] font-medium px-1.5 py-0.5 rounded', TYPE_COLORS[field.type] || 'bg-gray-100 text-gray-600')}>
                          {field.type}
                        </span>
                      </div>
                      {isMapped && (
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {mappingList.map((mapping) => (
                            <span
                              key={mapping.index}
                              className="inline-flex items-center gap-1 text-xs bg-white border border-green-200 text-green-700 rounded px-1.5 py-0.5"
                            >
                              <Link size={9} />
                              {mapping.name}
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleRemoveMapping(field.name, mapping.index);
                                }}
                                className="hover:bg-red-100 rounded-full p-0.5"
                              >
                                <X size={10} />
                              </button>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    {isMapped && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleClearFieldMapping(field.name);
                        }}
                        className="shrink-0 p-1 hover:bg-red-100 rounded"
                        title="Limpar todos os mapeamentos"
                      >
                        <Unlink size={14} className="text-gray-400" />
                      </button>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* RIGHT: File Columns */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
            <h3 className="font-semibold text-sm text-gray-700">Colunas do Arquivo</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {selectedDbField
                ? `Clique em uma ou mais colunas para mapear em "${modelFields.find((f) => f.name === selectedDbField)?.verbose_name}"`
                : 'Selecione um campo do sistema primeiro'}
            </p>
          </div>
          <div className="divide-y divide-gray-50 max-h-96 overflow-y-auto">
            {fileColumns.map((col) => {
              const mappedTo = isFileColumnMapped(col.column_index);
              const colorIdx = mappedTo ? getMappingColorIndex(mappedTo) : -1;
              const canSelect = selectedDbField && !mappedTo;

              return (
                <button
                  key={col.column_index}
                  onClick={() => handleFileColumnClick(col)}
                  disabled={!canSelect && !mappedTo}
                  className={clsx(
                    'w-full px-4 py-3 text-left flex items-center gap-3 transition-colors',
                    canSelect && 'hover:bg-[var(--color-primary-bg)] cursor-pointer',
                    mappedTo && 'bg-green-50',
                    !canSelect && !mappedTo && 'opacity-60',
                  )}
                >
                  {mappedTo && (
                    <span className={clsx('h-3 w-3 rounded-full shrink-0', MAPPING_COLORS[colorIdx % MAPPING_COLORS.length])} />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-800">{col.column_name}</span>
                      <span className={clsx('text-[10px] font-medium px-1.5 py-0.5 rounded', TYPE_COLORS[col.detected_type] || 'bg-gray-100 text-gray-600')}>
                        {col.detected_type}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5 truncate">
                      Amostra: {col.sample_data ?? '—'}
                    </p>
                    {mappedTo && (
                      <p className="text-xs text-green-600 mt-0.5 flex items-center gap-1">
                        <Link size={10} /> {modelFields.find((f) => f.name === mappedTo)?.verbose_name}
                      </p>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Preview Table */}
      {Object.keys(mappings).length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden mb-6">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
            <h3 className="font-semibold text-sm text-gray-700">Preview dos Dados Mapeados</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  {Object.entries(mappings).map(([dbField, mappingList]) => {
                    const field = modelFields.find((f) => f.name === dbField);
                    const colorIdx = getMappingColorIndex(dbField);
                    return (
                      <th key={dbField} className="px-3 py-2 text-left">
                        <div className="flex items-center gap-1.5">
                          <span className={clsx('h-2.5 w-2.5 rounded-full', MAPPING_COLORS[colorIdx % MAPPING_COLORS.length])} />
                          <span className="text-xs font-semibold text-gray-700">{field?.verbose_name}</span>
                          {mappingList.length > 1 && (
                            <Badge variant="secondary" className="text-[9px] px-1 py-0">{mappingList.length} colunas</Badge>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {mappingList.map((mapping) => (
                            <p key={mapping.index} className="text-[10px] text-gray-400">
                              {mapping.name} ({mapping.data_type})
                            </p>
                          ))}
                        </div>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {[0, 1, 2].map((rowIdx) => (
                  <tr key={rowIdx} className="border-b border-gray-50">
                    {Object.entries(mappings).map(([dbField, mappingList]) => {
                      const samples = mappingList.map((mapping) => {
                        const col = fileColumns.find((c) => c.column_index === mapping.index);
                        return col?.sample_data ?? '—';
                      }).filter(s => s !== '—').join(' + ');
                      
                      return (
                        <td key={dbField} className="px-3 py-2 text-xs text-gray-600">
                          {rowIdx === 0 ? (samples || '—') : '—'}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Save Section */}
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
          <Button onClick={handleSave} loading={saving} disabled={!allRequiredMapped}>
            Salvar Layout
          </Button>
        </div>
      </div>
    </div>
  );
}
