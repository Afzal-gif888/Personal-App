import React from 'react';
import { AlertCircle, CheckCircle2, Info, AlertTriangle } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface AlertProps {
  variant?: 'info' | 'success' | 'warning' | 'error';
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const Alert: React.FC<AlertProps> = ({
  variant = 'info',
  title,
  children,
  className,
}) => {
  const styles = {
    info: 'bg-sky-50/60 border-sky-200 text-sky-900',
    success: 'bg-emerald-50/60 border-emerald-200 text-emerald-900',
    warning: 'bg-amber-50/60 border-amber-200 text-amber-900',
    error: 'bg-rose-50/60 border-rose-200 text-rose-900',
  };

  const icons = {
    info: <Info className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />,
    success: <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />,
    warning: <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />,
    error: <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />,
  };

  return (
    <div className={cn('flex items-start gap-2.5 p-3 rounded-md border text-xs text-left', styles[variant], className)}>
      {icons[variant]}
      <div className="space-y-0.5 flex-1">
        {title && <h4 className="font-semibold leading-none">{title}</h4>}
        <div className="text-[11px] leading-relaxed opacity-90">{children}</div>
      </div>
    </div>
  );
};
