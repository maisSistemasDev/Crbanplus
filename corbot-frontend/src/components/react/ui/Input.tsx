import { forwardRef } from 'react';
import clsx from 'clsx';
import { applyMask } from '../../../lib/utils/masks';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  mask?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, mask, className, onChange, ...props }, ref) => {
    function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
      if (mask) {
        e.target.value = applyMask(e.target.value, mask);
      }
      onChange?.(e);
    }

    return (
      <div className="w-full">
        {label && (
          <label className="block text-xs font-medium text-gray-700 mb-0.5">
            {label}
            {props.required && <span className="text-red-500 ml-0.5">*</span>}
          </label>
        )}
        <input
          ref={ref}
          className={clsx(
            'w-full px-2.5 py-1.5 border rounded-md text-sm transition-all outline-none',
            error
              ? 'border-red-400 focus:ring-2 focus:ring-red-200'
              : 'border-gray-300 focus:ring-2 focus:ring-[var(--color-primary)]/20 focus:border-[var(--color-primary)]',
            className,
          )}
          onChange={handleChange}
          {...props}
        />
        {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';
