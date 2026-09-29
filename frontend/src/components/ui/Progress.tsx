import React from 'react';
import { cn } from '../../utils/cn';

export interface ProgressProps {
  value: number;
  tone?: 'accent' | 'success' | 'warning' | 'danger';
  size?: 'sm' | 'md';
  className?: string;
  label?: string;
}

const TONES = {
  accent: 'bg-accent',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-danger-solid',
};

export const Progress: React.FC<ProgressProps> = ({ value, tone = 'accent', size = 'sm', className, label }) => {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div
      role="progressbar"
      aria-valuenow={Math.round(clamped)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
      className={cn('w-full rounded-full bg-hover overflow-hidden', size === 'sm' ? 'h-1.5' : 'h-2', className)}
    >
      <div className={cn('h-full rounded-full transition-[width] duration-300', TONES[tone])} style={{ width: `${clamped}%` }} />
    </div>
  );
};
