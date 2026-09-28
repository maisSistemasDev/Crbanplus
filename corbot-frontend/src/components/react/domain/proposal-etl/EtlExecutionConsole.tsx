import { useState } from 'react';
import clsx from 'clsx';
import { ChevronDown, ChevronUp, Terminal } from 'lucide-react';
import type { EtlExecutionLogEntry } from '../../../../lib/api/types/etl';

interface EtlExecutionConsoleProps {
  open: boolean;
  onToggle: () => void;
  entries: EtlExecutionLogEntry[];
  status?: 'idle' | 'running' | 'success' | 'failed';
  runId?: string | null;
  batchId?: string | null;
}

const LEVEL_STYLES: Record<string, string> = {
  info: 'text-blue-700 bg-blue-50',
  success: 'text-green-700 bg-green-50',
  error: 'text-red-700 bg-red-50',
  warn: 'text-amber-700 bg-amber-50',
};

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('pt-BR');
  } catch {
    return iso;
  }
}

export function EtlExecutionConsole({
  open,
  onToggle,
  entries,
  status = 'idle',
  runId,
  batchId,
}: EtlExecutionConsoleProps) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  function toggleEntry(idx: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }

  return (
    <div className="border-t border-gray-200 bg-gray-900 text-gray-100 shrink-0">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-2 text-sm hover:bg-gray-800"
      >
        <span className="flex items-center gap-2 font-medium">
          <Terminal size={16} />
          Console de execução
          {entries.length > 0 && (
            <span className="text-xs text-gray-400">({entries.length} eventos)</span>
          )}
          {status === 'running' && (
            <span className="text-xs text-amber-400 animate-pulse">executando…</span>
          )}
        </span>
        {open ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
      </button>

      {open && (
        <div className="max-h-40 overflow-y-auto px-4 pb-3 font-mono text-[11px] space-y-1">
          {runId && (
            <p className="text-gray-500 text-[10px] mb-2">
              Run: {runId}
              {batchId && (
                <>
                  {' · '}
                  <a href={`/proposals/batches/${batchId}`} className="text-emerald-400 hover:underline">
                    Ver lote
                  </a>
                </>
              )}
            </p>
          )}
          {entries.length === 0 ? (
            <p className="text-gray-500 py-2">Execute ou teste um nó para ver logs, parâmetros e resultados.</p>
          ) : (
            entries.map((entry, idx) => {
              const isOpen = expanded.has(idx);
              const hasDetail =
                Object.keys(entry.params || {}).length > 0
                || Object.keys(entry.result || {}).length > 0;
              return (
                <div key={`${entry.timestamp}-${idx}`} className="rounded border border-gray-800 bg-gray-950/50">
                  <button
                    type="button"
                    className="w-full text-left px-2 py-1.5 flex items-start gap-2 hover:bg-gray-800/50"
                    onClick={() => hasDetail && toggleEntry(idx)}
                  >
                    <span className="text-gray-500 shrink-0">{formatTime(entry.timestamp)}</span>
                    <span
                      className={clsx(
                        'text-[9px] uppercase px-1 rounded shrink-0',
                        LEVEL_STYLES[entry.level] || 'text-gray-400 bg-gray-800',
                      )}
                    >
                      {entry.level}
                    </span>
                    {entry.node_label && (
                      <span className="text-violet-300 shrink-0">[{entry.node_label}]</span>
                    )}
                    <span className="text-gray-200 flex-1">{entry.message}</span>
                    {hasDetail && (isOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}
                  </button>
                  {isOpen && hasDetail && (
                    <div className="px-2 pb-2 space-y-1 border-t border-gray-800">
                      {Object.keys(entry.params || {}).length > 0 && (
                        <pre className="text-gray-400 whitespace-pre-wrap break-all">
                          params: {JSON.stringify(entry.params, null, 2)}
                        </pre>
                      )}
                      {Object.keys(entry.result || {}).length > 0 && (
                        <pre className="text-emerald-400/80 whitespace-pre-wrap break-all">
                          result: {JSON.stringify(entry.result, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
