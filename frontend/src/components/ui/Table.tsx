import React from 'react';
import { cn } from '../../utils/cn';

/**
 * Minimal data-table primitives. Wrap in a Card with `flush` for the bordered container.
 * Hide low-priority columns on small screens with `className="hidden md:table-cell"`.
 */
export const Table: React.FC<React.TableHTMLAttributes<HTMLTableElement>> = ({ className, ...props }) => (
  <div className="w-full overflow-x-auto">
    <table className={cn('w-full text-sm border-collapse', className)} {...props} />
  </div>
);

export const THead: React.FC<React.HTMLAttributes<HTMLTableSectionElement>> = ({ className, ...props }) => (
  <thead className={cn('bg-subtle/70 border-b border-line', className)} {...props} />
);

export const TBody: React.FC<React.HTMLAttributes<HTMLTableSectionElement>> = ({ className, ...props }) => (
  <tbody className={cn('divide-y divide-line', className)} {...props} />
);

export const TR: React.FC<React.HTMLAttributes<HTMLTableRowElement> & { interactive?: boolean }> = ({
  className,
  interactive,
  ...props
}) => (
  <tr className={cn('transition-colors', interactive && 'cursor-pointer hover:bg-subtle/70', className)} {...props} />
);

export const TH: React.FC<React.ThHTMLAttributes<HTMLTableCellElement>> = ({ className, ...props }) => (
  <th
    className={cn(
      'h-10 px-4 first:pl-5 last:pr-5 text-left align-middle text-xs font-medium text-fg-subtle whitespace-nowrap',
      className
    )}
    {...props}
  />
);

export const TD: React.FC<React.TdHTMLAttributes<HTMLTableCellElement>> = ({ className, ...props }) => (
  <td className={cn('px-4 first:pl-5 last:pr-5 py-3 align-middle text-fg', className)} {...props} />
);
