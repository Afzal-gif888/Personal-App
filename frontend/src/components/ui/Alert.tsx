import React from 'react';
import { AlertCircle, CheckCircle2, Info, AlertTriangle } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface AlertProps {
  variant?: 'info' | 'success' | 'warning' | 'error';
  title?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

const STYLES = {
  info: 'bg-accent-subtle border-accent-line',
  success: 'bg-success-subtle border-success-line',
  warning: 'bg-warning-subtle border-warning-line',
  error: 'bg-danger-subtle border-danger-line',
};

const ICONS = {
  info: <Info className="size-4 text-accent" />,
  success: <CheckCircle2 className="size-4 text-success" />,
  warning: <AlertTriangle className="size-4 text-warning" />,
  error: <AlertCircle className="size-4 text-danger" />,
};

export const Alert: React.FC<AlertProps> = ({ variant = 'info', title, children, action, className }) => (
  <div className={cn('flex items-start gap-3 p-3.5 rounded-lg border', STYLES[variant], className)}>
    <span className="mt-0.5 shrink-0">{ICONS[variant]}</span>
    <div className="flex-1 min-w-0 text-sm">
      {title && <p className="font-medium text-fg">{title}</p>}
      <div className={cn('text-fg-muted', title && 'mt-0.5')}>{children}</div>
    </div>
    {action && <div className="shrink-0">{action}</div>}
  </div>
);
