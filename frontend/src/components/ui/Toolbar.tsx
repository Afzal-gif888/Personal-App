import React from 'react';
import { Search, X, ChevronDown } from 'lucide-react';
import { cn } from '../../utils/cn';

/** Filter bar that sits above a table. */
export const Toolbar: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className }) => (
  <div className={cn('flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between', className)}>{children}</div>
);

export const SearchField: React.FC<{
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}> = ({ value, onChange, placeholder = 'Search…', className }) => (
  <div className={cn('relative w-full lg:w-72', className)}>
    <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-fg-faint pointer-events-none" />
    <input
      type="search"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      aria-label={placeholder}
      className="w-full h-9 pl-9 pr-8 rounded-lg border border-line-strong bg-surface text-sm text-fg placeholder:text-fg-faint shadow-xs focus:outline-none focus:border-accent focus:shadow-focus [&::-webkit-search-cancel-button]:hidden"
    />
    {value && (
      <button
        onClick={() => onChange('')}
        aria-label="Clear search"
        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded text-fg-faint hover:text-fg"
      >
        <X className="size-3.5" />
      </button>
    )}
  </div>
);

/** Compact select for toolbars (no label, matches SearchField height). */
export const FilterSelect: React.FC<{
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  label: string;
}> = ({ value, onChange, options, label }) => (
  <div className="relative shrink-0">
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label={label}
      className="h-9 pl-3 pr-9 rounded-lg border border-line-strong bg-surface text-sm text-fg shadow-xs appearance-none cursor-pointer focus:outline-none focus:border-accent focus:shadow-focus"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 size-4 text-fg-faint pointer-events-none" />
  </div>
);

export const TableFooter: React.FC<{ shown: number; total: number; noun: string }> = ({ shown, total, noun }) => (
  <div className="px-5 py-3 border-t border-line text-xs text-fg-subtle">
    Showing <span className="font-medium text-fg-muted tabular">{shown}</span> of{' '}
    <span className="font-medium text-fg-muted tabular">{total}</span> {noun}
  </div>
);
