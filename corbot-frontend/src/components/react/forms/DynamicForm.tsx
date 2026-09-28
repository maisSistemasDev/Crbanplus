import { useState, useEffect } from 'react';
import { Input } from '../ui/Input';
import { SearchSelect } from '../ui/SearchSelect';
import { Button } from '../ui/Button';
import { FileUpload } from '../ui/FileUpload';
import { resolveOptionsUrl } from '../../../lib/api/formFieldOptions';
import type { FormFieldDef } from '../../../lib/api/types';

interface DynamicFormProps {
  fields: FormFieldDef[];
  initialValues?: Record<string, any>;
  onSubmit: (values: Record<string, any>) => void;
  onChange?: (name: string, value: any, values: Record<string, any>) => void;
  loading?: boolean;
  submitLabel?: string;
}

function DynamicFormField({
  field,
  value,
  onChange,
}: {
  field: FormFieldDef;
  value: any;
  onChange: (name: string, value: any) => void;
}) {
  switch (field.type) {
    case 'separator':
      return (
        <div className="col-span-full my-4 border-t border-gray-200 pt-4">
          <h3 className="text-lg font-semibold text-gray-900">{field.label}</h3>
        </div>
      );

    case 'select':
      return (
        <div data-tour={field.name === 'role' ? 'user-form-role' : undefined}>
          <SearchSelect
            label={field.label}
            required={field.required}
            options={field.options}
            options_url={resolveOptionsUrl(field)}
            value={value ?? ''}
            onChange={(e) => onChange(field.name, e.target.value)}
          />
        </div>
      );

    case 'checkbox':
      return (
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id={field.name}
            checked={!!value}
            onChange={(e) => onChange(field.name, e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
          />
          <label htmlFor={field.name} className="text-sm text-gray-700">
            {field.label}
          </label>
        </div>
      );

    case 'color':
      return (
        <div className="w-full">
          <label className="block text-sm font-medium text-gray-700 mb-1">{field.label}</label>
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={value || '#000000'}
              onChange={(e) => onChange(field.name, e.target.value)}
              className="h-10 w-14 rounded cursor-pointer border border-gray-300"
            />
            <Input
              value={value || ''}
              onChange={(e) => onChange(field.name, e.target.value)}
              placeholder="#000000"
              className="flex-1"
            />
          </div>
        </div>
      );

    case 'textarea':
      return (
        <div className="w-full">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {field.label}
            {field.required && <span className="text-red-500 ml-0.5">*</span>}
          </label>
          <textarea
            value={value || ''}
            onChange={(e) => onChange(field.name, e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-[var(--color-primary)]/20 focus:border-[var(--color-primary)]"
            required={field.required}
          />
        </div>
      );

    case 'file':
      return (
        <FileUpload
          label={field.label}
          accept={field.accept}
          onFileSelect={(file) => onChange(field.name, file)}
        />
      );

    case 'date':
      return (
        <Input
          label={field.label}
          type="date"
          required={field.required}
          value={value || ''}
          onChange={(e) => onChange(field.name, e.target.value)}
        />
      );

    case 'number':
      return (
        <Input
          label={field.label}
          type="number"
          required={field.required}
          min={field.min}
          max={field.max}
          step={field.step}
          value={value ?? ''}
          onChange={(e) => onChange(field.name, e.target.value)}
        />
      );

    case 'password':
      return (
        <Input
          label={field.label}
          type="password"
          required={field.required}
          value={value || ''}
          onChange={(e) => onChange(field.name, e.target.value)}
        />
      );

    default:
      return (
        <Input
          label={field.label}
          type={field.type === 'email' ? 'email' : field.type === 'url' ? 'url' : 'text'}
          required={field.required}
          mask={field.mask}
          value={value || ''}
          onChange={(e) => onChange(field.name, e.target.value)}
        />
      );
  }
}

export function DynamicForm({
  fields,
  initialValues = {},
  onSubmit,
  onChange,
  loading = false,
  submitLabel = 'Salvar',
}: DynamicFormProps) {
  const [values, setValues] = useState<Record<string, any>>(initialValues);

  useEffect(() => {
    const defaults: Record<string, any> = {};
    fields.forEach((f) => {
      if (f.value !== undefined) defaults[f.name] = f.value;
      else if (f.default !== undefined) defaults[f.name] = f.default;
    });
    setValues({ ...defaults, ...initialValues });
  }, [fields]);

  function handleChange(name: string, value: any) {
    setValues((prev) => {
      const next = { ...prev, [name]: value };
      onChange?.(name, value, next);
      return next;
    });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit(values);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {fields.map((field) => (
          <div key={field.name} className={field.type === 'textarea' ? 'md:col-span-2' : ''}>
            <DynamicFormField
              field={field}
              value={values[field.name]}
              onChange={handleChange}
            />
          </div>
        ))}
      </div>
      <div className="flex justify-end pt-4">
        <Button type="submit" loading={loading}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
