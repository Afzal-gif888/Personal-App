import React from 'react';
import { cn } from '../../utils/cn';

export interface StatCardProps {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  icon?: React.ReactNode;
  tone?: 'default' | 'danger' | 'warning' | 'success';
  onClick?: () => void;
  className?: string;
}

const TONES = {
  default: 'text-fg',
  danger: 'text-danger',
  warning: 'text-warning',
  success: 'text-success',
};

export const StatCard: React.FC<StatCardProps> = ({ label, value, hint, icon, tone = 'default', onClick, className }) => {
  const Comp = onClick ? 'button' : 'div';
  return (
    <Comp
      onClick={onClick}
      className={cn(
        'w-full text-left rounded-xl border border-line bg-surface p-4 sm:p-5 shadow-xs',
        onClick && 'transition-colors hover:border-line-strong focus-visible:outline-none focus-visible:shadow-focus',
        className
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-fg-subtle truncate">{label}</span>
        {icon && <span className="text-fg-faint [&_svg]:size-4">{icon}</span>}
      </div>
      <div className={cn('mt-2 text-2xl font-semibold tracking-tight tabular', TONES[tone])}>{value}</div>
      {hint && <div className="mt-1 text-xs text-fg-subtle truncate">{hint}</div>}
    </Comp>
  );
};
