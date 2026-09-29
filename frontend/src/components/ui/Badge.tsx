import React from 'react';
import { cn } from '../../utils/cn';

export type BadgeVariant = 'neutral' | 'success' | 'warning' | 'error' | 'info' | 'outline' | 'black';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  /** Leading status dot. */
  dot?: boolean;
}

const VARIANTS: Record<BadgeVariant, string> = {
  neutral: 'bg-subtle text-fg-muted border-line',
  outline: 'bg-surface text-fg-muted border-line',
  black: 'bg-fg text-white border-fg',
  success: 'bg-success-subtle text-success border-success-line',
  warning: 'bg-warning-subtle text-warning border-warning-line',
  error: 'bg-danger-subtle text-danger border-danger-line',
  info: 'bg-accent-subtle text-accent-fg border-accent-line',
};

const DOTS: Record<BadgeVariant, string> = {
  neutral: 'bg-fg-faint',
  outline: 'bg-fg-faint',
  black: 'bg-white',
  success: 'bg-success',
  warning: 'bg-warning',
  error: 'bg-danger',
  info: 'bg-accent',
};

export const Badge: React.FC<BadgeProps> = ({
  children,
  className,
  variant = 'neutral',
  size = 'sm',
  dot = false,
  ...props
}) => (
  <span
    className={cn(
      'inline-flex items-center font-medium border rounded-md whitespace-nowrap',
      size === 'sm' ? 'text-xs h-5 px-1.5 gap-1' : 'text-xs h-6 px-2 gap-1.5',
      VARIANTS[variant],
      className
    )}
    {...props}
  >
    {dot && <span className={cn('size-1.5 rounded-full', DOTS[variant])} />}
    {children}
  </span>
);
