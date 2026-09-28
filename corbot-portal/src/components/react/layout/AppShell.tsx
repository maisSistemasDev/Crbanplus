import { useEffect, useState } from 'react';
import { useStore } from '@nanostores/react';
import { $isAuthenticated, $currentUser } from '../../../lib/stores/auth';
import { $sidebarCollapsed, $sidebarMobileOpen, closeMobileSidebar } from '../../../lib/stores/sidebar';
import { ThemeProvider } from '../providers/ThemeProvider';
import { ToastProvider } from '../providers/ToastProvider';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { BottomNavBar } from './BottomNavBar';
import { FullPageSpinner } from '../ui/Spinner';

const ADMIN_APP_URL = (import.meta.env.PUBLIC_ADMIN_APP_URL as string | undefined) || 'http://localhost:3000';

interface Props {
  children: React.ReactNode;
}

export function AppShell({ children }: Props) {
  const isAuthenticated = useStore($isAuthenticated);
  const user = useStore($currentUser);
  const collapsed = useStore($sidebarCollapsed);
  const mobileOpen = useStore($sidebarMobileOpen);
  const [ready, setReady] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      window.location.href = `${window.location.origin}/login`;
      return;
    }
    if (user && (user.role === 'admin' || user.role === 'colaborador')) {
      window.location.href = ADMIN_APP_URL;
      return;
    }
    setReady(true);
    const mq = window.matchMedia('(max-width: 767px)');
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => {
      setIsMobile(e.matches);
      if (!e.matches) closeMobileSidebar();
    };
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [isAuthenticated, user]);

  useEffect(() => {
    if (!isMobile) return;
    document.body.style.overflow = mobileOpen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [isMobile, mobileOpen]);

  if (!ready) return <FullPageSpinner />;

  return (
    <ThemeProvider>
      <div className="min-h-screen overflow-x-hidden bg-[var(--color-body-bg)]">
        <Sidebar isMobile={isMobile} />
        {isMobile && mobileOpen && (
          <button
            type="button"
            aria-label="Fechar menu"
            className="fixed inset-0 z-40 bg-black/40 md:hidden"
            onClick={closeMobileSidebar}
          />
        )}
        <div
          className="flex min-h-screen min-w-0 flex-col transition-all"
          style={{
            marginLeft: isMobile ? 0 : collapsed ? 'var(--sidebar-collapsed-width)' : 'var(--sidebar-width)',
            paddingBottom: isMobile
              ? 'calc(var(--bottom-nav-height) + env(safe-area-inset-bottom, 0px))'
              : undefined,
          }}
        >
          <Header isMobile={isMobile} />
          <main className="min-w-0 flex-1 p-3 md:p-5">{children}</main>
        </div>
        {isMobile && <BottomNavBar />}
      </div>
      <ToastProvider />
    </ThemeProvider>
  );
}
