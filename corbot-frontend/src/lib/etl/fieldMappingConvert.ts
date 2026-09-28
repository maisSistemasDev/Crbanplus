import type { FileColumn } from '../../../../lib/api/types';
import type { EtlFieldMapping } from '../../../../lib/api/types/etl';
import type { JsonLeafField } from '../../../../lib/etl/jsonPath';
import type { FieldMappings } from './useFieldMapping';

export function jsonLeavesToFileColumns(jsonFields: JsonLeafField[]): FileColumn[] {
  return jsonFields.map((f, index) => ({
    column_index: index,
    column_name: f.path,
    detected_type: f.type,
    sample_data: f.sample === '—' ? null : f.sample,
  }));
}

export function etlMappingsToFieldMappings(
  etlMappings: EtlFieldMapping[],
  sourceColumns: FileColumn[],
): FieldMappings {
  const result: FieldMappings = {};
  for (const m of etlMappings) {
    if (!m.layout_field || !m.source_path) continue;
    const col = sourceColumns.find((c) => c.column_name === m.source_path);
    const item = {
      index: col?.column_index ?? Object.values(result).flat().length,
      name: m.source_path,
      data_type: col?.detected_type || 'text',
    };
    result[m.layout_field] = [...(result[m.layout_field] || []), item];
  }
  return result;
}

export function fieldMappingsToEtlMappings(mappings: FieldMappings): EtlFieldMapping[] {
  const out: EtlFieldMapping[] = [];
  for (const [layoutField, list] of Object.entries(mappings)) {
    for (const item of list) {
      out.push({
        layout_field: layoutField,
        source_path: item.name,
        header_name: item.name,
      });
    }
  }
  return out;
}
