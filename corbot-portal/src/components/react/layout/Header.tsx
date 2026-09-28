import { useState, useRef, useEffect } from 'react';
import { useStore } from '@nanostores/react';
import { ChevronDown, LogOut, Menu, UserRound, KeyRound } from 'lucide-react';
import { $currentUser, clearAuth } from '../../../lib/stores/auth';
import { openMobileSidebar } from '../../../lib/stores/sidebar';
import { ROLE_LABELS, type Role } from '../../../lib/utils/roles';
import { RoleBadge } from '../ui/Badge';

export function Header({ isMobile = false }: { isMobile?: boolean }) {
  const user = useStore($currentUser);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('click', onClickOutside);
    return () => document.removeEventListener('click', onClickOutside);
  }, []);

  function handleLogout() {
    clearAuth();
    window.location.href = `${window.location.origin}/login`;
  }

  if (!user) return null;

  const fullName = `${user.first_name} ${user.last_name}`.trim() || user.email;
  const roleLabel = ROLE_LABELS[user.role as Role] ?? user.role;

  return (
    <header
      className="flex items-center justify-between gap-2 border-b border-[var(--color-header-border)] bg-[var(--color-header-bg)] px-3 md:px-5"
      style={{ height: 'var(--header-height)' }}
    >
      <div className="flex min-w-0 items-center gap-2">
        {isMobile && (
          <button
            type="button"
            onClick={openMobileSidebar}
            className="shrink-0 rounded-lg p-1.5 text-[var(--color-text)] hover:bg-gray-100"
            aria-label="Abrir menu"
          >
            <Menu className="h-5 w-5" />
          </button>
        )}
        <p className="page-title !text-sm truncate md:!text-base">{user.company_name ?? 'Portal'}</p>
      </div>

      <div className="relative" ref={ref}>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-2.5 rounded-lg px-2 py-1.5 hover:bg-gray-50 transition-colors"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--color-primary-bg)] text-[var(--color-primary-dark)]">
            <UserRound className="h-4 w-4" />
          </div>
          <div className="hidden text-left sm:block">
            <p className="text-sm font-medium leading-tight text-[var(--color-text)]">{fullName}</p>
            <RoleBadge role={user.role} label={roleLabel} />
          </div>
          <ChevronDown className="h-3.5 w-3.5 text-[var(--color-text-muted)]" />
        </button>

        {open && (
          <div className="absolute right-0 z-40 mt-1 w-52 overflow-hidden rounded-lg border border-[var(--color-border)] bg-white shadow-lg">
            <a
              href="/settings"
              className="flex items-center gap-2 px-4 py-2.5 text-sm text-[var(--color-text)] hover:bg-gray-50"
            >
              <UserRound className="h-4 w-4 text-[var(--color-primary)]" /> Meu perfil
            </a>
            <a
              href="/settings#senha"
              className="flex items-center gap-2 px-4 py-2.5 text-sm text-[var(--color-text)] hover:bg-gray-50"
            >
              <KeyRound className="h-4 w-4 text-[var(--color-primary)]" /> Alterar senha
            </a>
            <div className="border-t border-[var(--color-border)]" />
            <button
              type="button"
              onClick={handleLogout}
              className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-red-600 hover:bg-red-50"
            >
              <LogOut className="h-4 w-4" /> Sair
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
