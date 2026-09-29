import React from 'react';
import { MoreHorizontal } from 'lucide-react';
import { Dropdown, type DropdownItem } from './Dropdown';

/** Kebab menu for per-row actions in tables and lists. */
export const RowActions: React.FC<{ items: DropdownItem[]; label?: string }> = ({ items, label = 'Row actions' }) => (
  <div onClick={(e) => e.stopPropagation()}>
    <Dropdown
      items={items}
      menuClassName="min-w-40"
      trigger={
        <button
          aria-label={label}
          className="inline-flex items-center justify-center size-9 md:size-8 rounded-md text-fg-subtle hover:text-fg hover:bg-hover transition-colors"
        >
          <MoreHorizontal className="size-4" />
        </button>
      }
    />
  </div>
);
