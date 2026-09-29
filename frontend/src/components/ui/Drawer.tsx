import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  children: React.ReactNode;
  side?: 'left' | 'right';
  className?: string;
  bodyClassName?: string;
}

export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  children,
  side = 'left',
  className,
  bodyClassName,
}) => {
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
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-fg/40 animate-fade-in" onClick={onClose} aria-hidden="true" />
      <aside
        role="dialog"
        aria-modal="true"
        className={cn(
          'absolute inset-y-0 flex w-[280px] max-w-[85vw] flex-col bg-surface shadow-lg',
          side === 'left' ? 'left-0 border-r border-line animate-slide-in-left' : 'right-0 border-l border-line',
          className
        )}
      >
        <div className="flex items-center justify-between h-14 px-4 border-b border-line shrink-0">
          {title ?? <span />}
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-fg-faint hover:text-fg hover:bg-hover transition-colors"
            aria-label="Close"
          >
            <X className="size-4" />
          </button>
        </div>
        <div className={cn('flex-1 overflow-y-auto', bodyClassName ?? 'p-3')}>{children}</div>
      </aside>
    </div>
  );
};
