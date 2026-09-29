import React, { useState } from 'react';
import { cn } from '../../utils/cn';

export interface TooltipProps {
  content: string;
  children: React.ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
  disabled?: boolean;
}

const POSITIONS = {
  top: 'bottom-full mb-1.5 left-1/2 -translate-x-1/2',
  bottom: 'top-full mt-1.5 left-1/2 -translate-x-1/2',
  left: 'right-full mr-2 top-1/2 -translate-y-1/2',
  right: 'left-full ml-2 top-1/2 -translate-y-1/2',
};

export const Tooltip: React.FC<TooltipProps> = ({ content, children, position = 'top', disabled = false }) => {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div
      className="relative inline-flex"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
    >
      {children}
      {isVisible && !disabled && (
        <div
          role="tooltip"
          className={cn(
            'absolute z-50 px-2 py-1 text-xs font-medium text-white bg-fg rounded-md shadow-sm whitespace-nowrap pointer-events-none animate-fade-in',
            POSITIONS[position]
          )}
        >
          {content}
        </div>
      )}
    </div>
  );
};
