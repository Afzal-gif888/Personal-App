import React from 'react';
import { cn } from '../../utils/cn';

/**
 * Tables don't fit on phones, so data pages render a table from `md` up
 * and a stacked list below it. Use <DesktopOnly> around the Table and
 * <MobileList> + <MobileRow> for the phone layout.
 */
export const DesktopOnly: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="hidden md:block">{children}</div>
);

export const MobileList: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className }) => (
  <ul className={cn('md:hidden divide-y divide-line', className)}>{children}</ul>
);

export interface MobileRowProps {
  title: React.ReactNode;
  /** Secondary line under the title. */
  subtitle?: React.ReactNode;
  /** Badges / metadata row under the subtitle. */
  meta?: React.ReactNode;
  /** Top-right value such as an amount or date. */
  aside?: React.ReactNode;
  leading?: React.ReactNode;
  actions?: React.ReactNode;
  onClick?: () => void;
  muted?: boolean;
}

export const MobileRow: React.FC<MobileRowProps> = ({ title, subtitle, meta, aside, leading, actions, onClick, muted }) => (
  <li
    onClick={onClick}
    className={cn('flex items-start gap-3 px-4 py-3.5', onClick && 'cursor-pointer active:bg-subtle')}
  >
    {leading && <div className="shrink-0 pt-0.5">{leading}</div>}
    <div className="min-w-0 flex-1">
      <div className="flex items-start justify-between gap-3">
        <p className={cn('text-sm font-medium break-words', muted ? 'text-fg-subtle line-through' : 'text-fg')}>{title}</p>
        {aside && <div className="shrink-0 text-sm text-right">{aside}</div>}
      </div>
      {subtitle && <div className="text-xs text-fg-subtle mt-0.5 break-words">{subtitle}</div>}
      {meta && <div className="flex flex-wrap items-center gap-1.5 mt-2">{meta}</div>}
    </div>
    {actions && (
      <div className="shrink-0 -mr-1.5 -mt-1" onClick={(e) => e.stopPropagation()}>
        {actions}
      </div>
    )}
  </li>
);

/**
 * Grid for StatCards: 2 columns on phones (an odd last card spans the row),
 * `cols` columns from lg up.
 */
export const StatGrid: React.FC<{ children: React.ReactNode; cols?: 3 | 4 }> = ({ children, cols = 4 }) => (
  <div
    className={cn(
      'grid grid-cols-2 gap-3 sm:gap-4',
      '[&>*:last-child:nth-child(odd)]:col-span-2',
      cols === 4 ? 'lg:grid-cols-4' : 'sm:grid-cols-3 sm:[&>*:last-child:nth-child(odd)]:col-span-1'
    )}
  >
    {children}
  </div>
);
