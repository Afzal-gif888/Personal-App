import { useId } from 'react';
import { cn } from '../../utils/cn';

export function fieldControlClass(hasError: boolean) {
  return cn(
    'w-full rounded-lg border bg-surface text-sm text-fg placeholder:text-fg-faint shadow-xs transition-[border-color,box-shadow]',
    'focus:outline-none focus:border-accent focus:shadow-focus',
    'disabled:cursor-not-allowed disabled:bg-subtle disabled:text-fg-subtle',
    hasError ? 'border-danger focus:border-danger' : 'border-line-strong'
  );
}

export function useFieldId(id?: string, label?: string) {
  const generated = useId();
  return id || (label ? `${label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${generated}` : generated);
}
