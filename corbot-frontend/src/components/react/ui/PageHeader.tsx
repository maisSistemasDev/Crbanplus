import clsx from 'clsx';

interface PageHeaderProps {
  title: React.ReactNode;
  subtitle?: string;
  /** Botões ou ações alinhados à direita */
  actions?: React.ReactNode;
  className?: string;
}

/**
 * Cabeçalho padrão de página — usa .page-title e .page-subtitle do global.css
 */
export function PageHeader({ title, subtitle, actions, className }: PageHeaderProps) {
  return (
    <div className={clsx('flex items-start justify-between gap-3 mb-4', className)}>
      <div className="min-w-0">
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {actions && (
        <div className="flex items-center gap-2 shrink-0">{actions}</div>
      )}
    </div>
  );
}
