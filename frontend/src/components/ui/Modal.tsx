import React, { useEffect } from 'react';
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

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  maxWidth = 'md',
  footer,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const maxWidths = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs transition-opacity animate-in fade-in duration-200">
      <div
        className="fixed inset-0"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className={cn(
          'relative w-full rounded-lg border border-[#EAEAEA] bg-white p-5 shadow-lg transition-all z-10 text-left',
          maxWidths[maxWidth]
        )}
      >
        <div className="flex items-start justify-between pb-3 border-b border-[#EAEAEA]">
          <div>
            {title && <h2 className="text-base font-semibold text-[#111111]">{title}</h2>}
            {description && <p className="text-xs text-[#666666] mt-0.5">{description}</p>}
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-[#8A8A8A] hover:text-[#111111] hover:bg-[#F7F7F7] transition-colors"
          >
            <X className="w-4 h-4" />
            <span className="sr-only">Close modal</span>
          </button>
        </div>

        <div className="py-4 text-xs sm:text-sm text-[#111111] max-h-[75vh] overflow-y-auto">{children}</div>

        {footer && <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#EAEAEA]">{footer}</div>}
      </div>
    </div>
  );
};
