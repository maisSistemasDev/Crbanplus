import { Toaster } from 'react-hot-toast';

export function ToastProvider() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          borderRadius: '8px',
          fontSize: '14px',
        },
        success: {
          style: { borderLeft: '4px solid var(--color-success)' },
          iconTheme: { primary: '#10b981', secondary: '#fff' },
        },
        error: {
          style: { borderLeft: '4px solid var(--color-error)' },
          iconTheme: { primary: '#ef4444', secondary: '#fff' },
        },
      }}
    />
  );
}
