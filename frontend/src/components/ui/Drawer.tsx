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
}

export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  children,
  side = 'left',
  className,
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

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      <aside
        className={cn(
          'fixed inset-y-0 z-50 flex w-72 sm:w-80 flex-col bg-white border-r border-[#EAEAEA] shadow-xl transition-transform duration-200 ease-in-out',
          side === 'left' ? 'left-0' : 'right-0 border-l border-r-0',
          className
        )}
      >
        <div className="flex items-center justify-between p-4 border-b border-[#EAEAEA]">
          {title ? (
            <div className="text-sm font-semibold text-[#111111]">{title}</div>
          ) : (
            <div />
          )}
          <button
            onClick={onClose}
            className="rounded-md p-1 text-[#8A8A8A] hover:text-[#111111] hover:bg-[#F7F7F7] transition-colors"
          >
            <X className="w-4 h-4" />
            <span className="sr-only">Close menu</span>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 text-left">{children}</div>
      </aside>
    </div>
  );
};
