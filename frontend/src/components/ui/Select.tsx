import React from 'react';
import type { SelectHTMLAttributes } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: SelectOption[];
  error?: string;
  helperText?: string;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, options, error, helperText, id, ...props }, ref) => {
    const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="w-full space-y-1.5 text-left">
        {label && (
          <label htmlFor={selectId} className="block text-xs font-medium text-[#111111]">
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          <select
            ref={ref}
            id={selectId}
            className={cn(
              'w-full h-9 rounded-md border border-[#EAEAEA] bg-white pl-3 pr-8 text-xs sm:text-sm text-[#111111] appearance-none',
              'focus:outline-none focus:ring-1 focus:ring-black focus:border-black transition-colors cursor-pointer',
              'disabled:cursor-not-allowed disabled:bg-[#F7F7F7] disabled:text-[#8A8A8A]',
              error && 'border-red-500 focus:ring-red-500 focus:border-red-500',
              className
            )}
            {...props}
          >
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 w-4 h-4 text-[#8A8A8A] pointer-events-none shrink-0" />
        </div>
        {error && <p className="text-xs text-red-600 font-normal">{error}</p>}
        {!error && helperText && <p className="text-xs text-[#8A8A8A]">{helperText}</p>}
      </div>
    );
  }
);

Select.displayName = 'Select';
