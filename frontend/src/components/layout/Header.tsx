import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, Search, LogOut, Settings, ChevronRight, Inbox, MessageSquare, User } from 'lucide-react';
import { useUIStore } from '../../stores/uiStore';
import { useAuthStore } from '../../stores/authStore';
import { useApprovals } from '../../hooks/useApprovals';
import { findNavContext } from '../../config/navigation';
import { Avatar } from '../ui/Avatar';
import { Dropdown } from '../ui/Dropdown';
import { Button } from '../ui/Button';
import { Tooltip } from '../ui/Tooltip';

export const Header: React.FC = () => {
  const { setMobileDrawerOpen, setCommandMenuOpen } = useUIStore();
  const { user, logout } = useAuthStore();
  const { approvals } = useApprovals();
  const location = useLocation();
  const navigate = useNavigate();

  const { group, item } = findNavContext(location.pathname);
  const pendingCount = approvals.filter((a) => a.status === 'pending').length;
  const onAssistant = location.pathname.startsWith('/chat');
  const displayName = user?.name || 'Student';

  return (
    <header className="sticky top-0 z-20 h-14 shrink-0 bg-surface/90 backdrop-blur border-b border-line px-4 sm:px-6 flex items-center justify-between gap-3">
      <div className="flex items-center gap-2 min-w-0">
        <button
          onClick={() => setMobileDrawerOpen(true)}
          className="md:hidden -ml-1.5 p-1.5 rounded-md text-fg-muted hover:text-fg hover:bg-hover"
          aria-label="Open navigation"
        >
          <Menu className="size-5" />
        </button>

        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-sm min-w-0">
          {group?.label && (
            <>
              <span className="hidden sm:inline text-fg-subtle">{group.label}</span>
              <ChevronRight className="hidden sm:inline size-3.5 text-fg-faint shrink-0" />
            </>
          )}
          {item && (
            <Link to={item.path} className="font-medium text-fg truncate hover:text-fg-muted">
              {item.label}
            </Link>
          )}
        </nav>
      </div>

      <div className="flex items-center gap-1.5 sm:gap-2">
        <button
          onClick={() => setCommandMenuOpen(true)}
          className="hidden lg:flex items-center gap-2 h-8 w-64 px-2.5 text-sm text-fg-faint bg-subtle border border-line rounded-md hover:border-line-strong transition-colors"
        >
          <Search className="size-4" />
          <span className="flex-1 text-left">Search or jump to…</span>
          <kbd className="font-sans text-xs text-fg-subtle bg-surface border border-line rounded px-1.5">Ctrl K</kbd>
        </button>
        <Button
          variant="ghost"
          size="sm"
          iconOnly
          className="lg:hidden"
          onClick={() => setCommandMenuOpen(true)}
          aria-label="Search"
        >
          <Search className="size-4" />
        </Button>

        <Tooltip content={pendingCount ? `${pendingCount} awaiting review` : 'No pending approvals'} position="bottom">
          <Link
            to="/approvals"
            className="relative inline-flex items-center justify-center size-8 rounded-md text-fg-muted hover:bg-hover hover:text-fg transition-colors"
            aria-label={`Approvals, ${pendingCount} pending`}
          >
            <Inbox className="size-4" />
            {pendingCount > 0 && (
              <span className="absolute top-1 right-1 size-2 rounded-full bg-accent ring-2 ring-surface" />
            )}
          </Link>
        </Tooltip>

        {!onAssistant && (
          <Button
            size="sm"
            className="hidden sm:inline-flex"
            leftIcon={<MessageSquare className="size-4" />}
            onClick={() => navigate('/chat')}
          >
            Ask assistant
          </Button>
        )}

        <div className="w-px h-5 bg-line mx-1 hidden sm:block" />

        <Dropdown
          header={
            <div className="min-w-0">
              <p className="text-sm font-medium text-fg truncate">{displayName}</p>
              <p className="text-xs text-fg-subtle truncate">{user?.email}</p>
            </div>
          }
          trigger={
            <button className="flex items-center rounded-full focus-visible:outline-none focus-visible:shadow-focus" aria-label="Account menu">
              <Avatar name={displayName} src={user?.avatarUrl} size="sm" />
            </button>
          }
          items={[
            { id: 'profile', label: 'Profile', icon: <User />, onClick: () => navigate('/settings/profile') },
            { id: 'settings', label: 'Preferences', icon: <Settings />, onClick: () => navigate('/settings/preferences') },
            {
              id: 'logout',
              label: 'Sign out',
              icon: <LogOut />,
              destructive: true,
              separated: true,
              onClick: async () => {
                await logout();
                navigate('/login');
              },
            },
          ]}
        />
      </div>
    </header>
  );
};
