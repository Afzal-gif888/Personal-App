import React, { useEffect, useId } from 'react';
import { X } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  description?: string;
  children: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl';
  footer?: React.ReactNode;
}

const MAX_WIDTHS = {
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-3xl',
};

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  maxWidth = 'md',
  footer,
}) => {
  const titleId = useId();

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center sm:p-4">
      <div className="absolute inset-0 bg-fg/40 animate-fade-in" onClick={onClose} aria-hidden="true" />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        className={cn(
          'relative w-full flex flex-col max-h-[92vh] bg-surface shadow-lg animate-pop-in',
          'rounded-t-2xl sm:rounded-xl border border-line',
          MAX_WIDTHS[maxWidth]
        )}
      >
        <div className="flex items-start justify-between gap-4 px-6 pt-5 pb-4">
          <div className="min-w-0">
            {title && (
              <h2 id={titleId} className="text-base font-semibold text-fg">
                {title}
              </h2>
            )}
            {description && <p className="text-sm text-fg-subtle mt-1">{description}</p>}
          </div>
          <button
            onClick={onClose}
            className="-mr-2 -mt-1 rounded-md p-1.5 text-fg-faint hover:text-fg hover:bg-hover transition-colors"
            aria-label="Close dialog"
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="px-6 pb-6 overflow-y-auto text-sm text-fg">{children}</div>

        {footer && (
          <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-line bg-subtle/60 rounded-b-xl">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
