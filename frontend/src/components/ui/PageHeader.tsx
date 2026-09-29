import React from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface PageHeaderProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  /** Optional "back" link rendered above the title. */
  back?: { to: string; label: string };
  meta?: React.ReactNode;
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({ title, description, actions, back, meta, className }) => (
  <div className={cn('flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between', className)}>
    <div className="min-w-0">
      {back && (
        <Link
          to={back.to}
          className="inline-flex items-center gap-1 text-sm font-medium text-fg-subtle hover:text-fg mb-3 -ml-1"
        >
          <ChevronLeft className="size-4" />
          {back.label}
        </Link>
      )}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-xl sm:text-2xl font-semibold tracking-tight text-fg">{title}</h1>
        {meta}
      </div>
      {description && <p className="text-sm text-fg-subtle mt-1 max-w-2xl">{description}</p>}
    </div>
    {actions && <div className="flex items-center gap-2 shrink-0 flex-wrap">{actions}</div>}
  </div>
);

/** Standard vertical rhythm for a page body. */
export const Page: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className }) => (
  <div className={cn('space-y-6', className)}>{children}</div>
);
