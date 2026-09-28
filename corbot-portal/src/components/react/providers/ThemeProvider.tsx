import { useEffect } from 'react';
import { useStore } from '@nanostores/react';
import { $theme, applyTheme, initTheme } from '../../../lib/stores/theme';

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useStore($theme);

  useEffect(() => {
    initTheme();
  }, []);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  return <>{children}</>;
}
