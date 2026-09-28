import { useCallback, useEffect, useState } from 'react';
import type { EtlVariableExtraction } from '../../../../lib/api/types/etl';
import { Button } from '../../ui/Button';
import { Input } from '../../ui/Input';

interface ExtractionRow {
  id: string;
  name: string;
  path: string;
}

function newRow(name = '', path = ''): ExtractionRow {
  return { id: `var-${Math.random().toString(36).slice(2, 9)}`, name, path };
}

function extractionsToRows(extractions: EtlVariableExtraction[] | undefined): ExtractionRow[] {
  if (!extractions?.length) return [];
  return extractions.map((ext) => newRow(ext.name, ext.path));
}

function rowsToExtractions(rows: ExtractionRow[]): EtlVariableExtraction[] {
  return rows
    .filter((row) => row.name.trim() && row.path.trim())
    .map((row) => ({ name: row.name.trim(), path: row.path.trim() }));
}

interface EtlVariableExtractionsSectionProps {
  extractions: EtlVariableExtraction[] | undefined;
  onChange: (extractions: EtlVariableExtraction[]) => void;
  nodeId: string;
}

export function EtlVariableExtractionsSection({
  extractions,
  onChange,
  nodeId,
}: EtlVariableExtractionsSectionProps) {
  const [rows, setRows] = useState(() => extractionsToRows(extractions));

  useEffect(() => {
    setRows(extractionsToRows(extractions));
  }, [nodeId]);

  const commitRows = useCallback(
    (nextRows: ExtractionRow[]) => {
      setRows(nextRows);
      onChange(rowsToExtractions(nextRows));
    },
    [onChange],
  );

  return (
    <div className="space-y-2 border-t border-gray-100 pt-3 mt-2">
      <p className="text-xs font-medium text-gray-700">Variáveis extraídas</p>
      <p className="text-xs text-gray-500 leading-snug">
        Guarde campos específicos no item para usar em condicionais e mapeamentos.
        Paths são relativos ao JSON Path do detalhe (ex.:{' '}
        <code className="bg-gray-100 px-1 rounded">user_uuid</code>,{' '}
        <code className="bg-gray-100 px-1 rounded">partners[0]</code>).
        Use <code className="bg-gray-100 px-1 rounded">$.data.campo</code> para ler do corpo bruto.
      </p>
      {rows.map((row) => (
        <div key={row.id} className="flex gap-2 items-end">
          <div className="flex-1">
            <Input
              label="Nome da variável"
              value={row.name}
              onChange={(e) => {
                commitRows(rows.map((r) => (r.id === row.id ? { ...r, name: e.target.value } : r)));
              }}
              placeholder="user_uuid"
            />
          </div>
          <div className="flex-1">
            <Input
              label="JSON path"
              value={row.path}
              onChange={(e) => {
                commitRows(rows.map((r) => (r.id === row.id ? { ...r, path: e.target.value } : r)));
              }}
              placeholder="partners[0].uuid"
            />
          </div>
          <button
            type="button"
            className="text-xs text-red-600 hover:underline pb-2"
            onClick={() => commitRows(rows.filter((r) => r.id !== row.id))}
          >
            Remover
          </button>
        </div>
      ))}
      <Button
        size="sm"
        variant="secondary"
        type="button"
        onClick={() => commitRows([...rows, newRow('', '')])}
      >
        Adicionar variável
      </Button>
    </div>
  );
}
