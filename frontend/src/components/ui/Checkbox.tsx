import React from 'react';
import type { InputHTMLAttributes } from 'react';
import { Check } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: React.ReactNode;
  description?: string;
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, description, checked, onChange, disabled, id, ...props }, ref) => {
    const checkboxId = id || (typeof label === 'string' ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="flex items-start gap-2.5 text-left select-none">
        <div className="relative flex items-center h-5">
          <input
            ref={ref}
            type="checkbox"
            id={checkboxId}
            checked={checked}
            onChange={onChange}
            disabled={disabled}
            className="peer sr-only"
            {...props}
          />
          <div
            onClick={() => !disabled && onChange?.({ target: { checked: !checked } } as any)}
            className={cn(
              'w-4 h-4 rounded border border-[#EAEAEA] bg-white transition-colors flex items-center justify-center cursor-pointer',
              'peer-focus-visible:ring-1 peer-focus-visible:ring-black',
              checked && 'bg-black border-black text-white',
              disabled && 'opacity-50 cursor-not-allowed bg-[#F7F7F7]',
              className
            )}
          >
            {checked && <Check className="w-3 h-3 stroke-3" />}
          </div>
        </div>
        {(label || description) && (
          <div className="text-xs">
            {label && (
              <label htmlFor={checkboxId} className="font-medium text-[#111111] cursor-pointer block">
                {label}
              </label>
            )}
            {description && <p className="text-[#8A8A8A] text-[11px] mt-0.5">{description}</p>}
          </div>
        )}
      </div>
    );
  }
);

Checkbox.displayName = 'Checkbox';
