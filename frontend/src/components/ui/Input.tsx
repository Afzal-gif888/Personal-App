import React from 'react';
import type { InputHTMLAttributes } from 'react';
import { cn } from '../../utils/cn';
import { FieldShell } from './Field';
import { fieldControlClass, useFieldId } from './fieldStyles';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, helperText, leftIcon, rightIcon, id, ...props }, ref) => {
    const inputId = useFieldId(id, label);

    return (
      <FieldShell id={inputId} label={label} error={error} helperText={helperText} required={props.required}>
        <div className="relative flex items-center">
          {leftIcon && (
            <span className="absolute left-3 text-fg-faint pointer-events-none [&_svg]:size-4">{leftIcon}</span>
          )}
          <input
            ref={ref}
            id={inputId}
            aria-invalid={!!error}
            className={cn(fieldControlClass(!!error), 'h-9 px-3', leftIcon && 'pl-9', rightIcon && 'pr-9', className)}
            {...props}
          />
          {rightIcon && <span className="absolute right-3 text-fg-faint [&_svg]:size-4">{rightIcon}</span>}
        </div>
      </FieldShell>
    );
  }
);

Input.displayName = 'Input';
