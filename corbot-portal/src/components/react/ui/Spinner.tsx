import clsx from 'clsx';

export function Spinner({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        'animate-spin rounded-full border-2 border-[var(--color-primary)] border-t-transparent',
        className ?? 'h-6 w-6',
      )}
    />
  );
}

export function FullPageSpinner() {
  return (
    <div className="flex h-screen items-center justify-center bg-[var(--color-body-bg)]">
      <Spinner className="h-8 w-8" />
    </div>
  );
}

export function SectionSpinner() {
  return (
    <div className="flex justify-center py-10">
      <Spinner className="h-7 w-7" />
    </div>
  );
}
