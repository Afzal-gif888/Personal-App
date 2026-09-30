import React from 'react';
import { ChevronsLeft, ChevronsRight } from 'lucide-react';
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
 * - ≥ lg: full width; the arrow next to the logo collapses it to a rail and back
 */
export const Sidebar: React.FC = () => {
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const isDesktop = useMediaQuery(BREAKPOINTS.lg);
  const collapsed = sidebarCollapsed || !isDesktop;
  const label = collapsed ? 'Expand sidebar' : 'Collapse sidebar';

  return (
    <aside
      className={cn(
        'hidden md:flex flex-col h-screen sticky top-0 z-30 shrink-0 bg-surface border-r border-line transition-[width] duration-200',
        collapsed ? 'w-16' : 'w-60'
      )}
    >
      <div
        className={cn(
          'relative flex items-center h-14 border-b border-line shrink-0',
          collapsed ? 'justify-center' : 'justify-between gap-2 pl-4 pr-2'
        )}
      >
        <Logo size="sm" withText={!collapsed} />
        {isDesktop &&
          (collapsed ? (
            // No room beside the logo in the rail: the arrow sits on the sidebar's edge instead.
            <button
              onClick={toggleSidebar}
              className="absolute -right-3 top-1/2 -translate-y-1/2 flex items-center justify-center size-6 rounded-full border border-line bg-surface text-fg-muted shadow-xs hover:text-fg hover:bg-subtle transition-colors"
              aria-label={label}
              title={label}
            >
              <ChevronsRight className="size-3.5" />
            </button>
          ) : (
            <button
              onClick={toggleSidebar}
              className="flex items-center justify-center size-7 shrink-0 rounded-md text-fg-subtle hover:text-fg hover:bg-subtle transition-colors"
              aria-label={label}
              title={label}
            >
              <ChevronsLeft className="size-4" />
            </button>
          ))}
      </div>

      <div className={cn('flex-1 overflow-y-auto py-4', collapsed ? 'px-2' : 'px-3')}>
        <NavList collapsed={collapsed} />
      </div>

      <div className={cn('border-t border-line py-3 shrink-0', collapsed ? 'px-2' : 'px-3')}>
        <NavRow item={SETTINGS_NAV} collapsed={collapsed} />
      </div>
    </aside>
  );
};
