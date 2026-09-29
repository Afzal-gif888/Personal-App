import React, { useId } from 'react';
import { cn } from '../../utils/cn';

export interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  className?: string;
}

export const Switch: React.FC<SwitchProps> = ({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  className,
}) => {
  const id = useId();

  return (
    <div className={cn('flex items-start justify-between gap-6', className)}>
      {(label || description) && (
        <div className="space-y-0.5">
          {label && (
            <label htmlFor={id} className="text-sm font-medium text-fg cursor-pointer">
              {label}
            </label>
          )}
          {description && <p className="text-sm text-fg-subtle">{description}</p>}
        </div>
      )}
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative inline-flex h-5 w-9 shrink-0 mt-0.5 rounded-full border-2 border-transparent transition-colors',
          'focus-visible:outline-none focus-visible:shadow-focus disabled:opacity-50 disabled:cursor-not-allowed',
          checked ? 'bg-accent' : 'bg-line-strong'
        )}
      >
        <span
          className={cn(
            'pointer-events-none inline-block size-4 rounded-full bg-white shadow-sm transition-transform',
            checked ? 'translate-x-4' : 'translate-x-0'
          )}
        />
      </button>
    </div>
  );
};
