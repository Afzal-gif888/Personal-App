import React from 'react';

/** Shared label / helper / error layout for every form control. */
export const FieldShell: React.FC<{
  id?: string;
  label?: string;
  error?: string;
  helperText?: string;
  required?: boolean;
  children: React.ReactNode;
}> = ({ id, label, error, helperText, required, children }) => (
  <div className="w-full space-y-1.5">
    {label && (
      <label htmlFor={id} className="block text-sm font-medium text-fg">
        {label}
        {required && <span className="text-fg-faint font-normal"> *</span>}
      </label>
    )}
    {children}
    {error ? (
      <p className="text-xs text-danger">{error}</p>
    ) : (
      helperText && <p className="text-xs text-fg-subtle">{helperText}</p>
    )}
  </div>
);
