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
  variant?: 'underline' | 'pills';
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeTab,
  onChange,
  variant = 'underline',
  className,
}) => {
  return (
    <div
      className={cn(
        'flex items-center gap-1 overflow-x-auto no-scrollbar text-left',
        variant === 'underline' && 'border-b border-[#EAEAEA]',
        className
      )}
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={cn(
              'flex items-center gap-2 px-3 py-2 text-xs font-medium transition-colors shrink-0 whitespace-nowrap cursor-pointer',
              variant === 'underline' && [
                'border-b-2 -mb-px',
                isActive
                  ? 'border-black text-[#111111] font-semibold'
                  : 'border-transparent text-[#666666] hover:text-[#111111]',
              ],
              variant === 'pills' && [
                'rounded-md',
                isActive
                  ? 'bg-black text-white font-semibold'
                  : 'bg-[#F7F7F7] text-[#666666] hover:bg-[#F3F3F3] hover:text-[#111111]',
              ]
            )}
          >
            <span>{tab.label}</span>
            {tab.badge !== undefined && (
              <span
                className={cn(
                  'rounded-full px-1.5 py-0.2 text-[10px] font-medium',
                  isActive
                    ? variant === 'pills'
                      ? 'bg-neutral-800 text-white'
                      : 'bg-black text-white'
                    : 'bg-[#EAEAEA] text-[#666666]'
                )}
              >
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};
