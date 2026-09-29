import React from 'react';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { Logo } from '../ui/Logo';
import { NavList, NavRow } from './NavList';
import { SETTINGS_NAV } from '../../config/navigation';
import { useUIStore } from '../../stores/uiStore';
import { useMediaQuery, BREAKPOINTS } from '../../hooks/useMediaQuery';
import { cn } from '../../utils/cn';

/**
 * Desktop navigation.
 * - < md: hidden (mobile drawer + bottom bar take over)
 * - md–lg (tablets): always an icon rail to save width
 * - ≥ lg: full width, user can collapse to a rail
 */
export const Sidebar: React.FC = () => {
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const isDesktop = useMediaQuery(BREAKPOINTS.lg);
  const collapsed = sidebarCollapsed || !isDesktop;

  return (
    <aside
      className={cn(
        'hidden md:flex flex-col h-screen sticky top-0 z-30 shrink-0 bg-surface border-r border-line transition-[width] duration-200',
        collapsed ? 'w-16' : 'w-60'
      )}
    >
      <div className={cn('flex items-center h-14 border-b border-line shrink-0', collapsed ? 'justify-center' : 'px-4')}>
        <Logo size="sm" withText={!collapsed} subtext="Personal workspace" />
      </div>

      <div className={cn('flex-1 overflow-y-auto py-4', collapsed ? 'px-2' : 'px-3')}>
        <NavList collapsed={collapsed} />
      </div>

      <div className={cn('border-t border-line py-3 space-y-0.5 shrink-0', collapsed ? 'px-2' : 'px-3')}>
        <NavRow item={SETTINGS_NAV} collapsed={collapsed} />
        {isDesktop && (
          <button
            onClick={toggleSidebar}
            className={cn(
              'flex items-center gap-2.5 h-8 rounded-md text-sm font-medium text-fg-muted hover:bg-subtle hover:text-fg transition-colors',
              collapsed ? 'justify-center w-9 mx-auto' : 'w-full px-2.5'
            )}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <PanelLeftOpen className="size-4 text-fg-subtle" />
            ) : (
              <>
                <PanelLeftClose className="size-4 text-fg-subtle" />
                <span>Collapse</span>
              </>
            )}
          </button>
        )}
      </div>
    </aside>
  );
};
