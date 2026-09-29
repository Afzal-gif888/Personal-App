import React from 'react';
import type { InputHTMLAttributes } from 'react';
import { Check } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: React.ReactNode;
  description?: string;
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, description, checked, disabled, ...props }, ref) => (
    <label
      className={cn(
        'inline-flex items-start gap-2.5 select-none',
        disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'
      )}
      onClick={(e) => e.stopPropagation()}
    >
      <span className="relative flex items-center justify-center h-5">
        <input
          ref={ref}
          type="checkbox"
          checked={checked}
          disabled={disabled}
          className="peer sr-only"
          {...props}
        />
        <span
          aria-hidden="true"
          className={cn(
            'flex items-center justify-center size-4 rounded border transition-colors',
            'peer-focus-visible:shadow-focus',
            checked ? 'bg-accent border-accent text-white' : 'bg-surface border-line-strong',
            className
          )}
        >
          {checked && <Check className="size-3" strokeWidth={3} />}
        </span>
      </span>
      {(label || description) && (
        <span className="text-sm">
          {label && <span className="font-medium text-fg block">{label}</span>}
          {description && <span className="text-fg-subtle block mt-0.5">{description}</span>}
        </span>
      )}
    </label>
  )
);

Checkbox.displayName = 'Checkbox';
