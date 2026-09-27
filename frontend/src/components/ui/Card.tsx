import React from 'react';
import type { HTMLAttributes } from 'react';
import { cn } from '../../utils/cn';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
  /** Removes inner padding so lists and tables can run edge to edge. */
  flush?: boolean;
}

export const Card: React.FC<CardProps> = ({ children, className, hoverable = false, flush = false, ...props }) => (
  <div
    className={cn(
      'rounded-xl border border-line bg-surface text-fg shadow-xs',
      !flush && 'p-5',
      hoverable && 'transition-colors hover:border-line-strong cursor-pointer',
      className
    )}
    {...props}
  >
    {children}
  </div>
);

export const CardHeader: React.FC<HTMLAttributes<HTMLDivElement>> = ({ children, className, ...props }) => (
  <div className={cn('flex flex-col gap-1 pb-4', className)} {...props}>
    {children}
  </div>
);

export const CardTitle: React.FC<HTMLAttributes<HTMLHeadingElement>> = ({ children, className, ...props }) => (
  <h3 className={cn('text-sm font-semibold text-fg', className)} {...props}>
    {children}
  </h3>
);

export const CardDescription: React.FC<HTMLAttributes<HTMLParagraphElement>> = ({ children, className, ...props }) => (
  <p className={cn('text-sm text-fg-subtle', className)} {...props}>
    {children}
  </p>
);

export const CardContent: React.FC<HTMLAttributes<HTMLDivElement>> = ({ children, className, ...props }) => (
  <div className={className} {...props}>
    {children}
  </div>
);

export const CardFooter: React.FC<HTMLAttributes<HTMLDivElement>> = ({ children, className, ...props }) => (
  <div className={cn('flex items-center gap-2 pt-4 mt-5 border-t border-line', className)} {...props}>
    {children}
  </div>
);

/**
 * Titled section used across dashboards: header row with an optional action,
 * then a flush body for lists or tables.
 */
export interface PanelProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  bodyClassName?: string;
}

export const Panel: React.FC<PanelProps> = ({ title, description, action, children, className, bodyClassName, ...props }) => (
  <section className={cn('rounded-xl border border-line bg-surface shadow-xs', className)} {...props}>
    <header className="flex items-start justify-between gap-3 px-5 py-4 border-b border-line">
      <div className="min-w-0">
        <h2 className="text-sm font-semibold text-fg">{title}</h2>
        {description && <p className="text-xs text-fg-subtle mt-0.5">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </header>
    <div className={bodyClassName}>{children}</div>
  </section>
);
