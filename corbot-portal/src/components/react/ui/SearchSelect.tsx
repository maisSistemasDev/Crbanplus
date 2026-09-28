import { useEffect, useMemo, useRef, useState } from 'react';
import clsx from 'clsx';
import { ChevronDown, Search } from 'lucide-react';

export interface SearchSelectOption {
  value: string | number;
  label: string;
}

interface SearchSelectProps {
  options: readonly SearchSelectOption[];
  value: string | number | null | undefined;
  onChange: (value: string) => void;
  label?: string;
  placeholder?: string;
  searchPlaceholder?: string;
  /** Mostra a opção vazia na lista (ex.: "Todos") para limpar a seleção. */
  allowEmpty?: boolean;
  /** Altura reduzida, para barras de filtro. */
  compact?: boolean;
  disabled?: boolean;
  required?: boolean;
  className?: string;
  triggerClassName?: string;
}

const EMPTY_VALUE = '';

export function SearchSelect({
  options,
  value,
  onChange,
  label,
  placeholder = 'Selecione...',
  searchPlaceholder = 'Buscar...',
  allowEmpty = false,
  compact = false,
  disabled = false,
  required = false,
  className,
  triggerClassName,
}: SearchSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch('');
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  const listOptions = useMemo(() => {
    if (!allowEmpty) return options;
    return [{ value: EMPTY_VALUE, label: placeholder }, ...options];
  }, [allowEmpty, options, placeholder]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return listOptions;
    return listOptions.filter((opt) => opt.label.toLowerCase().includes(q));
  }, [listOptions, search]);

  const selected = options.find((opt) => String(opt.value) === String(value ?? ''));

  function emit(next: string) {
    onChange(next);
    setOpen(false);
    setSearch('');
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Escape') {
      setOpen(false);
      setSearch('');
      return;
    }
    if (e.key === 'Enter' && filtered.length > 0) {
      e.preventDefault();
      emit(String(filtered[0].value));
    }
  }

  return (
    <div ref={containerRef} className={clsx('relative', className ?? 'w-full')}>
      {label && (
        <label className="mb-1 block text-sm font-medium text-gray-700">
          {label}
          {required && <span className="ml-0.5 text-red-500">*</span>}
        </label>
      )}

      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((prev) => !prev)}
        className={clsx(
          'flex w-full items-center justify-between gap-2 rounded-lg border text-sm outline-none transition-colors',
          compact ? 'h-8 px-2' : 'px-3 py-2',
          disabled
            ? 'cursor-not-allowed border-gray-200 bg-gray-50 text-gray-400'
            : 'border-[var(--color-border)] bg-white text-gray-700 focus:border-[var(--color-primary)]',
          !selected && !disabled && 'text-gray-400',
          triggerClassName,
        )}
      >
        <span className="truncate">{selected?.label || placeholder}</span>
        <ChevronDown size={15} className={clsx('shrink-0 text-gray-400 transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 min-w-full max-w-[min(20rem,90vw)] overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg">
          <div className="border-b border-gray-100 p-2">
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                autoFocus
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={searchPlaceholder}
                className="w-full rounded-md border border-gray-200 py-1.5 pl-8 pr-3 text-sm outline-none focus:border-[var(--color-primary)]"
              />
            </div>
          </div>
          <ul className="max-h-52 overflow-y-auto py-1">
            {filtered.length === 0 && <li className="px-3 py-2 text-sm text-gray-400">Nenhum resultado</li>}
            {filtered.map((opt) => (
              <li key={`${opt.value}`}>
                <button
                  type="button"
                  onClick={() => emit(String(opt.value))}
                  className={clsx(
                    'w-full px-3 py-2 text-left text-sm transition-colors hover:bg-gray-50',
                    opt.value === EMPTY_VALUE && 'text-gray-500',
                    String(opt.value) === String(value ?? '') &&
                      'bg-[var(--color-primary-bg)] font-medium text-[var(--color-primary-dark)]',
                  )}
                >
                  {opt.label}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
