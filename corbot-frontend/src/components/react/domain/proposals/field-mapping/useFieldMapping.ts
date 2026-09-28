import { useState, useCallback } from 'react';
import toast from 'react-hot-toast';
import type { FileColumn, ModelField } from '../../../../lib/api/types';

export interface ColumnMappingItem {
  index: number;
  name: string;
  data_type: string;
}

export type FieldMappings = Record<string, ColumnMappingItem[]>;

export function useFieldMapping(sourceColumns: FileColumn[]) {
  const [mappings, setMappings] = useState<FieldMappings>({});
  const [selectedDbField, setSelectedDbField] = useState<string | null>(null);

  const handleDbFieldClick = useCallback((fieldName: string) => {
    setSelectedDbField((current) => (current === fieldName ? null : fieldName));
  }, []);

  const isSourceColumnMapped = useCallback(
    (colIndex: number): string | null => {
      for (const [field, mappingList] of Object.entries(mappings)) {
        if (mappingList.some((m) => m.index === colIndex)) return field;
      }
      return null;
    },
    [mappings],
  );

  const handleSourceColumnClick = useCallback(
    (col: FileColumn) => {
      if (!selectedDbField) return;

      const existingField = Object.entries(mappings).find(([, mappingList]) =>
        mappingList.some((m) => m.index === col.column_index),
      );
      if (existingField) {
        toast.error(`Esta coluna ja esta mapeada para "${existingField[0]}"`);
        return;
      }

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
    },
    [selectedDbField, mappings],
  );

  const handleRemoveMapping = useCallback((fieldName: string, columnIndex: number) => {
    setMappings((prev) => {
      const newList = prev[fieldName].filter((m) => m.index !== columnIndex);
      if (newList.length === 0) {
        const { [fieldName]: _, ...rest } = prev;
        return rest;
      }
      return { ...prev, [fieldName]: newList };
    });
    toast.success('Coluna removida do mapeamento');
  }, []);

  const handleClearFieldMapping = useCallback((fieldName: string) => {
    setMappings((prev) => {
      const next = { ...prev };
      delete next[fieldName];
      return next;
    });
    setSelectedDbField(null);
    toast.success('Mapeamento limpo');
  }, []);

  const getMappingColorIndex = useCallback(
    (fieldName: string): number => Object.keys(mappings).indexOf(fieldName),
    [mappings],
  );

  const allRequiredMapped = useCallback(
    (modelFields: ModelField[]) =>
      modelFields
        .filter((f) => f.required)
        .every((f) => mappings[f.name] && mappings[f.name].length > 0),
    [mappings],
  );

  const resetMappings = useCallback((initial?: FieldMappings) => {
    setMappings(initial || {});
    setSelectedDbField(null);
  }, []);

  return {
    mappings,
    setMappings,
    selectedDbField,
    setSelectedDbField,
    handleDbFieldClick,
    handleSourceColumnClick,
    handleRemoveMapping,
    handleClearFieldMapping,
    getMappingColorIndex,
    isSourceColumnMapped,
    allRequiredMapped,
    resetMappings,
  };
}
