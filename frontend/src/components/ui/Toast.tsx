import React from 'react';
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';
import { useNotificationStore } from '../../stores/notificationStore';

const ICONS = {
  success: <CheckCircle2 className="size-4 text-success" />,
  error: <AlertCircle className="size-4 text-danger" />,
  warning: <AlertTriangle className="size-4 text-warning" />,
  info: <Info className="size-4 text-accent" />,
};

export const ToastContainer: React.FC = () => {
  const { toasts, removeToast } = useNotificationStore();

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      className="fixed z-50 bottom-20 md:bottom-5 right-4 left-4 sm:left-auto flex flex-col gap-2 sm:w-96 pointer-events-none"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className="pointer-events-auto flex items-start gap-3 p-3.5 bg-surface border border-line rounded-lg shadow-lg animate-slide-up"
        >
          <span className="mt-0.5 shrink-0">{ICONS[t.type]}</span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-fg">{t.message}</p>
            {t.description && <p className="text-sm text-fg-subtle mt-0.5">{t.description}</p>}
          </div>
          <button
            onClick={() => removeToast(t.id)}
            className="text-fg-faint hover:text-fg p-0.5 rounded transition-colors"
            aria-label="Dismiss notification"
          >
            <X className="size-4" />
          </button>
        </div>
      ))}
    </div>
  );
};
