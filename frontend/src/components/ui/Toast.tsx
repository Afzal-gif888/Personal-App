import React from 'react';
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';
import { useNotificationStore } from '../../stores/notificationStore';
import { cn } from '../../utils/cn';

export const ToastContainer: React.FC = () => {
  const { toasts, removeToast } = useNotificationStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none px-4 sm:px-0">
      {toasts.map((t) => {
        const icons = {
          success: <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />,
          error: <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />,
          warning: <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />,
          info: <Info className="w-4 h-4 text-sky-600 shrink-0" />,
        };

        return (
          <div
            key={t.id}
            className={cn(
              'pointer-events-auto flex items-start gap-3 p-3 bg-white border border-[#EAEAEA] rounded-lg shadow-md transition-all animate-in slide-in-from-bottom-5 duration-200 text-left'
            )}
          >
            {icons[t.type]}
            <div className="flex-1 space-y-0.5">
              <p className="text-xs font-semibold text-[#111111]">{t.message}</p>
              {t.description && <p className="text-[11px] text-[#666666]">{t.description}</p>}
            </div>
            <button
              onClick={() => removeToast(t.id)}
              className="text-[#8A8A8A] hover:text-[#111111] p-0.5 rounded transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
