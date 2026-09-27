import React from 'react';
import type { SelectHTMLAttributes } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '../../utils/cn';
import { FieldShell } from './Field';
import { fieldControlClass, useFieldId } from './fieldStyles';

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
    const selectId = useFieldId(id, label);

    return (
      <FieldShell id={selectId} label={label} error={error} helperText={helperText} required={props.required}>
        <div className="relative flex items-center">
          <select
            ref={ref}
            id={selectId}
            className={cn(fieldControlClass(!!error), 'h-9 pl-3 pr-9 appearance-none cursor-pointer', className)}
            {...props}
          >
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 size-4 text-fg-faint pointer-events-none" />
        </div>
      </FieldShell>
    );
  }
);

Select.displayName = 'Select';
