import clsx from 'clsx';
import { Link, Unlink, AlertCircle, X } from 'lucide-react';
import type { FileColumn, ModelField } from '../../../../lib/api/types';
import { Badge } from '../../../ui/Badge';
import { MAPPING_COLORS, TYPE_COLORS } from './constants';
import type { FieldMappings } from './useFieldMapping';

interface FieldMappingPanelsProps {
  modelFields: ModelField[];
  sourceColumns: FileColumn[];
  sourcePanelTitle: string;
  mappings: FieldMappings;
  selectedDbField: string | null;
  onDbFieldClick: (fieldName: string) => void;
  onSourceColumnClick: (col: FileColumn) => void;
  onRemoveMapping: (fieldName: string, columnIndex: number) => void;
  onClearFieldMapping: (fieldName: string) => void;
  getMappingColorIndex: (fieldName: string) => number;
  isSourceColumnMapped: (colIndex: number) => string | null;
  showPreview?: boolean;
}

export function FieldMappingPanels({
  modelFields,
  sourceColumns,
  sourcePanelTitle,
  mappings,
  selectedDbField,
  onDbFieldClick,
  onSourceColumnClick,
  onRemoveMapping,
  onClearFieldMapping,
  getMappingColorIndex,
  isSourceColumnMapped,
  showPreview = true,
}: FieldMappingPanelsProps) {
  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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
                    type="button"
                    onClick={() => onDbFieldClick(field.name)}
                    className="w-full px-4 py-3 text-left flex items-center gap-3"
                  >
                    {isMapped && (
                      <span className={clsx('h-3 w-3 rounded-full shrink-0', MAPPING_COLORS[colorIdx % MAPPING_COLORS.length])} />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-800">{field.verbose_name}</span>
                        {field.required && <AlertCircle size={12} className="text-red-400" />}
                        {(field.name === 'bank_access' || field.name === 'digitador') && (
                          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-50 text-amber-700">
                            mapear 1 dos 2
                          </span>
                        )}
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
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onRemoveMapping(field.name, mapping.index);
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
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onClearFieldMapping(field.name);
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

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
            <h3 className="font-semibold text-sm text-gray-700">{sourcePanelTitle}</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {selectedDbField
                ? `Clique em uma ou mais colunas para mapear em "${modelFields.find((f) => f.name === selectedDbField)?.verbose_name}"`
                : 'Selecione um campo do sistema primeiro'}
            </p>
          </div>
          <div className="divide-y divide-gray-50 max-h-96 overflow-y-auto">
            {sourceColumns.map((col) => {
              const mappedTo = isSourceColumnMapped(col.column_index);
              const colorIdx = mappedTo ? getMappingColorIndex(mappedTo) : -1;
              const canSelect = selectedDbField && !mappedTo;

              return (
                <button
                  key={col.column_index}
                  type="button"
                  onClick={() => onSourceColumnClick(col)}
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

      {showPreview && Object.keys(mappings).length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
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
                <tr className="border-b border-gray-50">
                  {Object.entries(mappings).map(([dbField, mappingList]) => {
                    const samples = mappingList.map((mapping) => {
                      const col = sourceColumns.find((c) => c.column_index === mapping.index);
                      return col?.sample_data ?? '—';
                    }).filter((s) => s !== '—').join(' + ');

                    return (
                      <td key={dbField} className="px-3 py-2 text-xs text-gray-600">
                        {samples || '—'}
                      </td>
                    );
                  })}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  );
}
