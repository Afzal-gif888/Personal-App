import React, { useState, useRef, useEffect, useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '../../utils/cn';

export interface DropdownItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  destructive?: boolean;
  /** Draws a separator above this item. */
  separated?: boolean;
}

export interface DropdownProps {
  trigger: React.ReactNode;
  items: DropdownItem[];
  align?: 'left' | 'right';
  header?: React.ReactNode;
  className?: string;
  menuClassName?: string;
}

interface MenuPosition {
  top?: number;
  bottom?: number;
  left?: number;
  right?: number;
}

/**
 * Menu rendered in a portal with fixed positioning so it is never clipped
 * by scrolling containers such as tables. Flips above the trigger near the viewport bottom.
 */
export const Dropdown: React.FC<DropdownProps> = ({ trigger, items, align = 'right', header, className, menuClassName }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState<MenuPosition>({});
  const triggerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (!isOpen || !triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const menuHeight = menuRef.current?.offsetHeight ?? 200;
    const openUp = rect.bottom + menuHeight + 8 > window.innerHeight && rect.top > menuHeight + 8;
    setPosition({
      ...(openUp ? { bottom: window.innerHeight - rect.top + 6 } : { top: rect.bottom + 6 }),
      ...(align === 'right' ? { right: window.innerWidth - rect.right } : { left: rect.left }),
    });
  }, [isOpen, align]);

  useEffect(() => {
    if (!isOpen) return;
    const close = () => setIsOpen(false);
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      if (!triggerRef.current?.contains(target) && !menuRef.current?.contains(target)) close();
    };
    const handleKey = (e: KeyboardEvent) => e.key === 'Escape' && close();
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKey);
    window.addEventListener('resize', close);
    window.addEventListener('scroll', close, true);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKey);
      window.removeEventListener('resize', close);
      window.removeEventListener('scroll', close, true);
    };
  }, [isOpen]);

  return (
    <div className={cn('relative inline-block text-left', className)} ref={triggerRef}>
      <div onClick={() => setIsOpen((o) => !o)}>{trigger}</div>

      {isOpen &&
        createPortal(
          <div
            ref={menuRef}
            role="menu"
            style={position}
            className={cn(
              'fixed z-[60] min-w-52 rounded-lg border border-line bg-surface p-1 shadow-lg animate-pop-in',
              menuClassName
            )}
          >
            {header && <div className="px-2.5 py-2 mb-1 border-b border-line">{header}</div>}
            {items.map((item) => (
              <React.Fragment key={item.id}>
                {item.separated && <div className="my-1 h-px bg-line" />}
                <button
                  role="menuitem"
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsOpen(false);
                    item.onClick();
                  }}
                  className={cn(
                    'w-full flex items-center gap-2.5 px-2.5 h-8 text-sm rounded-md text-left transition-colors [&_svg]:size-4',
                    item.destructive ? 'text-danger hover:bg-danger-subtle' : 'text-fg hover:bg-hover'
                  )}
                >
                  {item.icon && <span className={item.destructive ? 'text-danger' : 'text-fg-subtle'}>{item.icon}</span>}
                  <span>{item.label}</span>
                </button>
              </React.Fragment>
            ))}
          </div>,
          document.body
        )}
    </div>
  );
};
