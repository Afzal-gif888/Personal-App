import React from 'react';
import type { TextareaHTMLAttributes } from 'react';
import { cn } from '../../utils/cn';
import { FieldShell } from './Field';
import { fieldControlClass, useFieldId } from './fieldStyles';

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, helperText, id, rows = 3, ...props }, ref) => {
    const textareaId = useFieldId(id, label);

    return (
      <FieldShell id={textareaId} label={label} error={error} helperText={helperText} required={props.required}>
        <textarea
          ref={ref}
          id={textareaId}
          rows={rows}
          className={cn(fieldControlClass(!!error), 'px-3 py-2 resize-y min-h-20 leading-relaxed', className)}
          {...props}
        />
      </FieldShell>
    );
  }
);

Textarea.displayName = 'Textarea';
