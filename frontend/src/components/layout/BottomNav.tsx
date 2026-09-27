import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Home, MessageSquare, Inbox, CheckSquare, Menu } from 'lucide-react';
import { useUIStore } from '../../stores/uiStore';
import { useApprovals } from '../../hooks/useApprovals';
import { cn } from '../../utils/cn';

const ITEMS = [
  { label: 'Home', icon: Home, path: '/dashboard' },
  { label: 'Assistant', icon: MessageSquare, path: '/chat' },
  { label: 'Approvals', icon: Inbox, path: '/approvals' },
  { label: 'Tasks', icon: CheckSquare, path: '/tasks' },
];

export const BottomNav: React.FC = () => {
  const { setMobileDrawerOpen } = useUIStore();
  const { approvals } = useApprovals();
  const location = useLocation();
  const pendingCount = approvals.filter((a) => a.status === 'pending').length;

  const itemClass = (active: boolean) =>
    cn(
      'flex flex-1 flex-col items-center justify-center gap-1 min-h-12 text-2xs font-medium transition-colors',
      active ? 'text-accent' : 'text-fg-subtle'
    );

  return (
    <nav
      aria-label="Quick navigation"
      className="md:hidden fixed bottom-0 inset-x-0 z-30 bg-surface border-t border-line pb-[env(safe-area-inset-bottom)]"
    >
      <div className="flex items-stretch h-14 max-w-lg mx-auto">
        {ITEMS.map((item) => {
          const Icon = item.icon;
          const active = location.pathname.startsWith(item.path);
          return (
            <NavLink key={item.path} to={item.path} className={itemClass(active)}>
              <span className="relative">
                <Icon className="size-5" strokeWidth={active ? 2.2 : 1.8} />
                {item.path === '/approvals' && pendingCount > 0 && (
                  <span className="absolute -top-1 -right-2 tabular min-w-4 h-4 px-1 rounded-full bg-accent text-white text-2xs leading-4 text-center">
                    {pendingCount}
                  </span>
                )}
              </span>
              {item.label}
            </NavLink>
          );
        })}
        <button onClick={() => setMobileDrawerOpen(true)} className={itemClass(false)}>
          <Menu className="size-5" strokeWidth={1.8} />
          More
        </button>
      </div>
    </nav>
  );
};
