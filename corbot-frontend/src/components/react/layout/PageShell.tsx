import { useEffect, useState } from 'react';
import { useStore } from '@nanostores/react';
import { $isAuthenticated } from '../../../lib/stores/auth';
import { QueryProvider } from '../providers/QueryProvider';
import { ThemeProvider } from '../providers/ThemeProvider';
import { ToastProvider } from '../providers/ToastProvider';
import { SidebarContent } from './SidebarContent';
import { HeaderContent } from './HeaderContent';
import { MobileHome } from './MobileHome';
import { BottomNavBar } from './BottomNavBar';
import { $sidebarCollapsed } from '../../../lib/stores/sidebar';
import { usePushNotifications } from '../../../lib/hooks/usePushNotifications';

interface Props {
  children: React.ReactNode;
}

export function PageShell({ children }: Props) {
  const isAuthenticated = useStore($isAuthenticated);
  const collapsed = useStore($sidebarCollapsed);
  const [ready, setReady] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  usePushNotifications();

  useEffect(() => {
    if (!isAuthenticated) {
      window.location.href = `${window.location.origin}/login`;
      return;
    }
    setReady(true);
    const mq = window.matchMedia('(max-width: 767px)'); /* alinhado ao md: 768px do Tailwind */
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [isAuthenticated]);

  if (!ready) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin h-8 w-8 border-4 border-[var(--color-primary)] border-t-transparent rounded-full" />
      </div>
    );
  }

  // Determine if current path is the dashboard root (show app grid on mobile)
  const currentPath = typeof window !== 'undefined' ? window.location.pathname : '/';
  const isDashboard = currentPath === '/dashboard' || currentPath === '/';

  return (
    <QueryProvider>
      <ThemeProvider>
        {isMobile ? (
          <>
            {isDashboard ? (
              <MobileHome />
            ) : (
              <div
                className="flex flex-col min-h-screen bg-[var(--color-body-bg)]"
                style={{ paddingBottom: 'calc(var(--bottom-nav-height) + env(safe-area-inset-bottom, 0px))' }}
              >
                <HeaderContent />
                <main className="flex-1 overflow-y-auto p-3 bg-[var(--color-body-bg)]">
                  {children}
                </main>
              </div>
            )}
            <BottomNavBar />
          </>
        ) : (
          <div className="flex h-screen overflow-hidden">
            <SidebarContent />
            <div
              className="flex flex-col flex-1 overflow-hidden transition-all duration-250"
              style={{
                marginLeft: collapsed ? 'var(--sidebar-collapsed-width)' : 'var(--sidebar-width)',
              }}
            >
              <HeaderContent />
              <main className="flex-1 overflow-y-auto p-4 bg-[var(--color-body-bg)]">
                {children}
              </main>
            </div>
          </div>
        )}
        <ToastProvider />
      </ThemeProvider>
    </QueryProvider>
  );
}
