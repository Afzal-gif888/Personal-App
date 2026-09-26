import React from 'react';
import type { TextareaHTMLAttributes } from 'react';
import { cn } from '../../utils/cn';

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, helperText, id, rows = 3, ...props }, ref) => {
    const textareaId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="w-full space-y-1.5 text-left">
        {label && (
          <label htmlFor={textareaId} className="block text-xs font-medium text-[#111111]">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          rows={rows}
          className={cn(
            'w-full rounded-md border border-[#EAEAEA] bg-white p-3 text-xs sm:text-sm text-[#111111] placeholder:text-[#8A8A8A]',
            'focus:outline-none focus:ring-1 focus:ring-black focus:border-black transition-colors resize-y min-h-20',
            'disabled:cursor-not-allowed disabled:bg-[#F7F7F7] disabled:text-[#8A8A8A]',
            error && 'border-red-500 focus:ring-red-500 focus:border-red-500',
            className
          )}
          {...props}
        />
        {error && <p className="text-xs text-red-600 font-normal">{error}</p>}
        {!error && helperText && <p className="text-xs text-[#8A8A8A]">{helperText}</p>}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
