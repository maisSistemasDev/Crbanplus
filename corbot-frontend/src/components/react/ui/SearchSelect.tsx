import { useEffect, useMemo, useRef, useState } from 'react';
import clsx from 'clsx';
import { ChevronDown, Search } from 'lucide-react';
import { fetchSelectOptions, type SelectOption } from '../../../lib/api/formFieldOptions';

interface SearchSelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'onChange'> {
  label?: string;
  error?: string;
  options?: readonly SelectOption[];
  options_url?: string;
  placeholder?: string;
  searchPlaceholder?: string;
  /** Mostra a opção vazia na lista (ex.: "Todos") para limpar a seleção. */
  allowEmpty?: boolean;
  /** Altura reduzida, para barras de filtro. */
  compact?: boolean;
  triggerClassName?: string;
  onChange?: React.ChangeEventHandler<HTMLSelectElement>;
}

const EMPTY_VALUE = '';

export function SearchSelect({
  label,
  error,
  options: staticOptions,
  options_url,
  placeholder = 'Selecione...',
  searchPlaceholder = 'Buscar...',
  allowEmpty = false,
  compact = false,
  className,
  triggerClassName,
  value,
  onChange,
  name,
  required,
  disabled,
  ...props
}: SearchSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [fetchedOptions, setFetchedOptions] = useState<SelectOption[]>([]);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Sem estado para as opções estáticas: elas costumam vir em array inline.
  const options = staticOptions ?? fetchedOptions;

  useEffect(() => {
    if (!options_url) return;
    setLoading(true);
    fetchSelectOptions(options_url)
      .then(setFetchedOptions)
      .catch(() => setFetchedOptions([]))
      .finally(() => setLoading(false));
  }, [options_url]);

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

  function emit(nextValue: string) {
    onChange?.({
      target: { value: nextValue, name: name ?? '' },
    } as React.ChangeEvent<HTMLSelectElement>);
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

  const displayLabel = selected?.label || (loading ? 'Carregando...' : placeholder);

  return (
    <div ref={containerRef} className={clsx('relative w-full', className)}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label}
          {required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
      )}

      <button
        type="button"
        disabled={disabled || loading}
        onClick={() => setOpen((prev) => !prev)}
        className={clsx(
          'w-full flex items-center justify-between gap-2 border rounded-lg text-sm text-left transition-all outline-none',
          compact ? 'h-8 px-2 py-0' : 'px-3 py-2',
          error
            ? 'border-red-400 focus:ring-2 focus:ring-red-200'
            : 'border-gray-300 focus:ring-2 focus:ring-[var(--color-primary)]/20 focus:border-[var(--color-primary)]',
          !selected && !loading && 'text-gray-400',
          (disabled || loading) && 'opacity-60 cursor-not-allowed bg-gray-50',
          'bg-white',
          triggerClassName,
        )}
      >
        <span className="truncate">{displayLabel}</span>
        <ChevronDown size={16} className={clsx('shrink-0 text-gray-400 transition-transform', open && 'rotate-180')} />
      </button>

      {/* Campo oculto para validação HTML5 de required */}
      {required && (
        <select
          {...props}
          name={name}
          required
          value={value ?? ''}
          onChange={() => {}}
          tabIndex={-1}
          aria-hidden
          className="sr-only"
        >
          <option value=""> </option>
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      )}

      {open && (
        <div className="absolute z-50 mt-1 w-full min-w-[12rem] rounded-lg border border-gray-200 bg-white shadow-lg overflow-hidden">
          <div className="p-2 border-b border-gray-100">
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                autoFocus
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={searchPlaceholder}
                className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-md outline-none focus:border-[var(--color-primary)]"
              />
            </div>
          </div>
          <ul className="max-h-52 overflow-y-auto py-1">
            {loading && (
              <li className="px-3 py-2 text-sm text-gray-400">Carregando...</li>
            )}
            {!loading && filtered.length === 0 && (
              <li className="px-3 py-2 text-sm text-gray-400">Nenhum resultado</li>
            )}
            {!loading &&
              filtered.map((opt) => (
                <li key={`${opt.value}`}>
                  <button
                    type="button"
                    onClick={() => emit(String(opt.value))}
                    className={clsx(
                      'w-full px-3 py-2 text-left text-sm hover:bg-gray-50 transition-colors',
                      opt.value === EMPTY_VALUE && 'text-gray-500',
                      String(opt.value) === String(value ?? '') &&
                        'bg-[var(--color-primary)]/10 text-[var(--color-primary)] font-medium',
                    )}
                  >
                    {opt.label}
                  </button>
                </li>
              ))}
          </ul>
        </div>
      )}

      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
    </div>
  );
}
