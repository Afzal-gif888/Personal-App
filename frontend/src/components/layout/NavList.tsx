import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import { NAV_GROUPS, isNavItemActive, type NavItem } from '../../config/navigation';
import { useApprovals } from '../../hooks/useApprovals';
import { Tooltip } from '../ui/Tooltip';
import { cn } from '../../utils/cn';

interface NavListProps {
  collapsed?: boolean;
  onNavigate?: () => void;
}

/** Grouped primary navigation, shared by the desktop sidebar and the mobile drawer. */
export const NavList: React.FC<NavListProps> = ({ collapsed = false, onNavigate }) => {
  const { approvals } = useApprovals();
  const pendingCount = approvals.filter((a) => a.status === 'pending').length;

  return (
    <nav aria-label="Primary" className="space-y-5">
      {NAV_GROUPS.map((group) => (
        <div key={group.id} className="space-y-0.5">
          {group.label &&
            (collapsed ? (
              <div className="mx-3 mb-2 h-px bg-line" />
            ) : (
              <div className="px-2.5 pb-1 text-xs font-medium text-fg-faint">{group.label}</div>
            ))}
          {group.items.map((item) => (
            <NavRow
              key={item.id}
              item={item}
              collapsed={collapsed}
              count={item.showApprovalCount ? pendingCount : undefined}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      ))}
    </nav>
  );
};

/**
 * A section icon in its colour: a lightly tinted tile normally, a solid tile with a white icon when
 * it's the current page. The colour comes from the item (a --color-nav-* token).
 */
export const NavIcon: React.FC<{ icon: LucideIcon; color: string; active?: boolean; size?: 'sm' | 'md' }> = ({
  icon: Icon,
  color,
  active = false,
  size = 'sm',
}) => (
  <span
    style={{ '--nav': color } as React.CSSProperties}
    className={cn(
      'inline-flex shrink-0 items-center justify-center rounded-md transition-colors',
      size === 'sm' ? 'size-6' : 'size-7',
      active
        ? 'bg-[var(--nav)] text-white shadow-xs'
        : 'bg-[color-mix(in_srgb,var(--nav)_12%,transparent)] text-[var(--nav)] group-hover:bg-[color-mix(in_srgb,var(--nav)_20%,transparent)]'
    )}
  >
    <Icon className={size === 'sm' ? 'size-3.5' : 'size-4'} strokeWidth={2.2} />
  </span>
);

export const NavRow: React.FC<{
  item: NavItem;
  collapsed?: boolean;
  count?: number;
  onNavigate?: () => void;
}> = ({ item, collapsed = false, count, onNavigate }) => {
  const location = useLocation();
  const active = isNavItemActive(item, location.pathname);
  const Icon = item.icon;
  const hasCount = count !== undefined && count > 0;

  const link = (
    <NavLink
      to={item.path}
      onClick={onNavigate}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'group relative flex items-center gap-2.5 h-10 md:h-8 rounded-md text-sm font-medium transition-colors',
        collapsed ? 'justify-center w-9 mx-auto' : 'px-2.5',
        active ? 'bg-hover text-fg' : 'text-fg-muted hover:bg-subtle hover:text-fg'
      )}
    >
      <NavIcon icon={Icon} color={item.color} active={active} />
      {!collapsed && <span className="truncate">{item.label}</span>}
      {hasCount &&
        (collapsed ? (
          <span className="absolute top-1 right-1 size-2 rounded-full bg-accent ring-2 ring-surface" />
        ) : (
          <span className="ml-auto tabular inline-flex items-center justify-center h-5 min-w-5 px-1.5 rounded-full bg-accent text-white text-xs font-semibold">
            {count}
          </span>
        ))}
    </NavLink>
  );

  return collapsed ? (
    <Tooltip content={item.label} position="right">
      {link}
    </Tooltip>
  ) : (
    link
  );
};
