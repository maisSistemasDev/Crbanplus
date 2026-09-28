import { useEffect, useRef, useState } from 'react';
import { Plus, X } from 'lucide-react';

interface MultiValueFilterProps {
  /** Valor final do filtro: itens separados por quebra de linha. */
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  /** Rótulo do botão que abre o textarea, ex.: "+ Matrícula". */
  addLabel: string;
}

function parseValues(raw: string) {
  return raw
    .split(/[\n\r,;]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

/**
 * Filtro que aceita um valor digitado direto no input ou vários valores
 * colados em um textarea (um por linha).
 */
export function MultiValueFilter({ value, onChange, placeholder, addLabel }: MultiValueFilterProps) {
  const values = parseValues(value);
  const isMulti = values.length > 1;

  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(value);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) setDraft(value);
  }, [open, value]);

  useEffect(() => {
    if (!open) return;
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  function applyDraft() {
    onChange(parseValues(draft).join('\n'));
    setOpen(false);
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="flex gap-1">
        <input
          type="text"
          placeholder={placeholder}
          value={isMulti ? `${values.length} valores` : value}
          readOnly={isMulti}
          onChange={(e) => onChange(e.target.value)}
          className={`w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)] ${
            isMulti ? 'cursor-pointer bg-gray-50' : ''
          }`}
          onClick={() => isMulti && setOpen(true)}
        />
        {isMulti ? (
          <button
            type="button"
            onClick={() => onChange('')}
            title="Limpar"
            className="rounded-lg border border-gray-200 px-2 text-gray-500 hover:bg-gray-50"
          >
            <X size={14} />
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setOpen((prev) => !prev)}
            title={addLabel}
            className="whitespace-nowrap rounded-lg border border-gray-200 px-2 text-xs text-gray-600 hover:bg-gray-50"
          >
            <Plus size={14} />
          </button>
        )}
      </div>

      {open && (
        <div className="absolute left-0 right-0 z-20 mt-1 rounded-lg border border-gray-200 bg-white p-3 shadow-lg">
          <p className="mb-1 text-xs font-medium text-gray-600">{addLabel}</p>
          <p className="mb-2 text-xs text-gray-400">Um valor por linha</p>
          <textarea
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="h-28 w-full rounded border border-gray-200 px-2 py-1 text-sm outline-none focus:border-[var(--color-primary)]"
            placeholder={placeholder}
          />
          <div className="mt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setDraft('');
                onChange('');
                setOpen(false);
              }}
              className="rounded px-2 py-1 text-xs text-gray-600 hover:bg-gray-50"
            >
              Limpar
            </button>
            <button
              type="button"
              onClick={applyDraft}
              className="rounded bg-[var(--color-primary)] px-3 py-1 text-xs font-medium text-white"
            >
              Aplicar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
