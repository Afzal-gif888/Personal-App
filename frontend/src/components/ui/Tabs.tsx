import React from 'react';
import { cn } from '../../utils/cn';

export interface TabItem {
  id: string;
  label: React.ReactNode;
  badge?: number | string;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (tabId: string) => void;
  /** underline: page-level sections. pills: compact segmented control. */
  variant?: 'underline' | 'pills';
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({ tabs, activeTab, onChange, variant = 'underline', className }) => {
  if (variant === 'pills') {
    return (
      <div
        role="tablist"
        className={cn('inline-flex items-center gap-0.5 p-0.5 rounded-lg bg-subtle border border-line max-w-full overflow-x-auto no-scrollbar', className)}
      >
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              onClick={() => onChange(tab.id)}
              className={cn(
                'inline-flex items-center gap-1.5 h-7 px-2.5 rounded-md text-sm font-medium whitespace-nowrap transition-colors',
                isActive ? 'bg-surface text-fg shadow-xs' : 'text-fg-subtle hover:text-fg'
              )}
            >
              {tab.label}
              {tab.badge !== undefined && (
                <span className={cn('tabular text-xs', isActive ? 'text-fg-muted' : 'text-fg-faint')}>{tab.badge}</span>
              )}
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div role="tablist" className={cn('flex items-center gap-5 border-b border-line overflow-x-auto no-scrollbar', className)}>
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={cn(
              'relative inline-flex items-center gap-2 h-10 text-sm font-medium whitespace-nowrap transition-colors',
              isActive ? 'text-fg' : 'text-fg-subtle hover:text-fg'
            )}
          >
            {tab.label}
            {tab.badge !== undefined && (
              <span
                className={cn(
                  'tabular inline-flex items-center h-5 min-w-5 justify-center px-1.5 rounded-full text-xs',
                  isActive ? 'bg-accent-subtle text-accent-fg' : 'bg-subtle text-fg-subtle'
                )}
              >
                {tab.badge}
              </span>
            )}
            {isActive && <span className="absolute inset-x-0 -bottom-px h-0.5 bg-accent rounded-full" />}
          </button>
        );
      })}
    </div>
  );
};
