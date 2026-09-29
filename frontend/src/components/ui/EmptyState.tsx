import React from 'react';
import { Inbox } from 'lucide-react';
import { Button } from './Button';
import { cn } from '../../utils/cn';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
  /** Renders without a border, for use inside a Panel or table. */
  bare?: boolean;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = <Inbox />,
  title,
  description,
  actionLabel,
  onAction,
  className,
  bare = false,
}) => (
  <div
    className={cn(
      'flex flex-col items-center justify-center text-center px-6 py-12',
      !bare && 'rounded-xl border border-dashed border-line-strong bg-surface',
      className
    )}
  >
    <div className="flex items-center justify-center size-10 rounded-lg border border-line bg-surface shadow-xs text-fg-subtle mb-4 [&_svg]:size-5">
      {icon}
    </div>
    <h3 className="text-sm font-semibold text-fg">{title}</h3>
    <p className="text-sm text-fg-subtle max-w-sm mt-1">{description}</p>
    {actionLabel && onAction && (
      <Button variant="secondary" size="sm" onClick={onAction} className="mt-5">
        {actionLabel}
      </Button>
    )}
  </div>
);
