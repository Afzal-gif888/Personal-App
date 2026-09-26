import React from 'react';
import type { InputHTMLAttributes } from 'react';
import { cn } from '../../utils/cn';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, helperText, leftIcon, rightIcon, id, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="w-full space-y-1.5 text-left">
        {label && (
          <label htmlFor={inputId} className="block text-xs font-medium text-[#111111]">
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {leftIcon && (
            <div className="absolute left-3 text-[#8A8A8A] pointer-events-none shrink-0">{leftIcon}</div>
          )}
          <input
            ref={ref}
            id={inputId}
            className={cn(
              'w-full h-9 rounded-md border border-[#EAEAEA] bg-white px-3 text-xs sm:text-sm text-[#111111] placeholder:text-[#8A8A8A]',
              'focus:outline-none focus:ring-1 focus:ring-black focus:border-black transition-colors',
              'disabled:cursor-not-allowed disabled:bg-[#F7F7F7] disabled:text-[#8A8A8A]',
              leftIcon && 'pl-9',
              rightIcon && 'pr-9',
              error && 'border-red-500 focus:ring-red-500 focus:border-red-500',
              className
            )}
            {...props}
          />
          {rightIcon && <div className="absolute right-3 text-[#8A8A8A] shrink-0">{rightIcon}</div>}
        </div>
        {error && <p className="text-xs text-red-600 font-normal">{error}</p>}
        {!error && helperText && <p className="text-xs text-[#8A8A8A]">{helperText}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';
