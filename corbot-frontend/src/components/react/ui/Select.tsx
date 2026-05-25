import { useEffect, useState } from 'react';
import clsx from 'clsx';
import { api } from '../../../lib/api/client';

interface Option {
  value: string | number;
  label: string;
}

interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'onChange'> {
  label?: string;
  error?: string;
  options?: Option[];
  options_url?: string;
  placeholder?: string;
  onChange?: React.ChangeEventHandler<HTMLSelectElement>;
}

export function Select({
  label,
  error,
  options: staticOptions,
  options_url,
  placeholder = 'Selecione...',
  className,
  ...props
}: SelectProps) {
  const [options, setOptions] = useState<Option[]>(staticOptions || []);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (options_url) {
      setLoading(true);
      api
        .get<Array<{ id: string | number; name: string }>>(options_url)
        .then((data) => {
          const items = Array.isArray(data) ? data : (data as any).results || [];
          setOptions(items.map((item: any) => ({ value: item.id, label: item.name })));
        })
        .catch(() => setOptions([]))
        .finally(() => setLoading(false));
    }
  }, [options_url]);

  useEffect(() => {
    if (staticOptions) setOptions(staticOptions);
  }, [staticOptions]);

  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label}
          {props.required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
      )}
      <select
        className={clsx(
          'w-full px-3 py-2 border rounded-lg text-sm transition-all outline-none appearance-none',
          'bg-white bg-[url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2712%27 height=%2712%27 viewBox=%270 0 12 12%27%3E%3Cpath fill=%27%236b7280%27 d=%27M2 4l4 4 4-4%27/%3E%3C/svg%3E")] bg-[right_0.75rem_center] bg-no-repeat pr-8',
          error
            ? 'border-red-400 focus:ring-2 focus:ring-red-200'
            : 'border-gray-300 focus:ring-2 focus:ring-[var(--color-primary)]/20 focus:border-[var(--color-primary)]',
          className,
        )}
        disabled={loading || props.disabled}
        {...props}
      >
        <option value="">{loading ? 'Carregando...' : placeholder}</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
    </div>
  );
}
