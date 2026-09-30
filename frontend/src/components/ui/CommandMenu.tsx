import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Plus, MessageSquare, CornerDownLeft } from 'lucide-react';
import { useUIStore } from '../../stores/uiStore';
import { ALL_NAV_ITEMS } from '../../config/navigation';
import { NavIcon } from '../layout/NavList';
import { cn } from '../../utils/cn';

interface CommandItem {
  id: string;
  label: string;
  hint?: string;
  group: 'Actions' | 'Go to';
  icon: React.ReactNode;
  path: string;
}

const COMMANDS: CommandItem[] = [
  { id: 'ask', label: 'Ask the assistant', hint: 'Start a request', group: 'Actions', icon: <MessageSquare />, path: '/chat' },
  { id: 'new-task', label: 'New task', group: 'Actions', icon: <Plus />, path: '/tasks' },
  { id: 'new-reminder', label: 'New reminder', group: 'Actions', icon: <Plus />, path: '/reminders' },
  { id: 'new-expense', label: 'Log an expense', group: 'Actions', icon: <Plus />, path: '/expenses' },
  ...ALL_NAV_ITEMS.map<CommandItem>((item) => {
    const Icon = item.icon;
    return { id: `nav-${item.id}`, label: item.label, hint: item.description, group: 'Go to', icon: <NavIcon icon={Icon} color={item.color} />, path: item.path };
  }),
];

export const CommandMenu: React.FC = () => {
  const { commandMenuOpen, setCommandMenuOpen } = useUIStore();
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCommandMenuOpen(!useUIStore.getState().commandMenuOpen);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setCommandMenuOpen]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return COMMANDS;
    return COMMANDS.filter((c) => c.label.toLowerCase().includes(q) || c.hint?.toLowerCase().includes(q));
  }, [query]);

  if (!commandMenuOpen) return null;

  const close = () => {
    setCommandMenuOpen(false);
    setQuery('');
    setActiveIndex(0);
  };

  const run = (item: CommandItem) => {
    navigate(item.path);
    close();
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') close();
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    }
    if (e.key === 'Enter' && filtered[activeIndex]) run(filtered[activeIndex]);
  };

  const groups = (['Actions', 'Go to'] as const)
    .map((g) => ({ name: g, items: filtered.filter((c) => c.group === g) }))
    .filter((g) => g.items.length > 0);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh] px-4" onKeyDown={onKeyDown}>
      <div className="absolute inset-0 bg-fg/40 animate-fade-in" onClick={close} aria-hidden="true" />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command menu"
        className="relative w-full max-w-xl rounded-xl border border-line bg-surface shadow-lg overflow-hidden animate-pop-in"
      >
        <div className="flex items-center gap-2.5 px-4 border-b border-line">
          <Search className="size-4 text-fg-faint shrink-0" />
          <input
            type="text"
            autoFocus
            placeholder="Search pages and actions…"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActiveIndex(0);
            }}
            className="w-full h-12 bg-transparent text-sm text-fg placeholder:text-fg-faint focus:outline-none"
          />
          <kbd className="hidden sm:inline font-sans text-xs text-fg-subtle bg-subtle border border-line rounded px-1.5">Esc</kbd>
        </div>

        <div ref={listRef} className="max-h-[50vh] overflow-y-auto p-2">
          {filtered.length === 0 ? (
            <p className="py-10 text-center text-sm text-fg-subtle">No results for “{query}”.</p>
          ) : (
            groups.map((group) => (
              <div key={group.name} className="mb-1 last:mb-0">
                <div className="px-2 pt-2 pb-1 text-xs font-medium text-fg-faint">{group.name}</div>
                {group.items.map((item) => {
                  const index = filtered.indexOf(item);
                  const active = index === activeIndex;
                  return (
                    <button
                      key={item.id}
                      onMouseEnter={() => setActiveIndex(index)}
                      onClick={() => run(item)}
                      className={cn(
                        'w-full flex items-center gap-3 h-10 px-2 rounded-md text-left transition-colors',
                        active ? 'bg-hover' : 'hover:bg-subtle'
                      )}
                    >
                      <span className="flex text-fg-subtle [&>svg]:size-4">{item.icon}</span>
                      <span className="text-sm font-medium text-fg">{item.label}</span>
                      {item.hint && <span className="text-sm text-fg-faint truncate">{item.hint}</span>}
                      {active && <CornerDownLeft className="ml-auto size-3.5 text-fg-faint shrink-0" />}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
