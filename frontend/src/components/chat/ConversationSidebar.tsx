import React, { useState, useMemo } from 'react';
import { SquarePen, Search, Pencil, Trash2 } from 'lucide-react';
import type { Conversation } from '../../types';
import { Button } from '../ui/Button';
import { RowActions } from '../ui/RowActions';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { cn } from '../../utils/cn';

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeId: string;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onRename: (id: string, newTitle: string) => void;
  onDelete: (id: string) => void;
  isCreating?: boolean;
  className?: string;
}

const GROUPS = ['Today', 'Yesterday', 'Previous 7 days', 'Older'] as const;

function groupFor(dateStr: string): (typeof GROUPS)[number] {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const t = new Date(dateStr).getTime();
  if (t >= startOfToday) return 'Today';
  if (t >= startOfToday - 86400000) return 'Yesterday';
  if (t >= startOfToday - 7 * 86400000) return 'Previous 7 days';
  return 'Older';
}

export const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  conversations,
  activeId,
  onSelect,
  onNewChat,
  onRename,
  onDelete,
  isCreating = false,
  className,
}) => {
  const [query, setQuery] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [deleting, setDeleting] = useState<Conversation | null>(null);

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    const result: Record<string, Conversation[]> = {};
    conversations
      .filter((c) => !q || c.title.toLowerCase().includes(q))
      .forEach((c) => {
        (result[groupFor(c.updatedAt || c.createdAt)] ||= []).push(c);
      });
    return result;
  }, [conversations, query]);

  const hasResults = Object.keys(grouped).length > 0;

  const commitRename = (id: string) => {
    if (editingTitle.trim()) onRename(id, editingTitle.trim());
    setEditingId(null);
  };

  return (
    <div className={cn('w-72 h-full flex flex-col bg-surface border-r border-line shrink-0', className)}>
      <div className="flex items-center justify-between h-12 px-4 border-b border-line shrink-0">
        <span className="text-sm font-semibold text-fg">Conversations</span>
        <Button variant="ghost" size="sm" iconOnly onClick={onNewChat} isLoading={isCreating} aria-label="New conversation">
          <SquarePen className="size-4" />
        </Button>
      </div>

      <div className="p-3 shrink-0">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-fg-faint" />
          <input
            type="search"
            placeholder="Search conversations"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full h-8 pl-8 pr-2.5 text-sm rounded-md bg-subtle border border-line placeholder:text-fg-faint text-fg focus:outline-none focus:border-accent focus:bg-surface"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {!hasResults ? (
          <p className="text-center py-10 text-sm text-fg-subtle">
            {query ? 'No matching conversations' : 'No conversations yet'}
          </p>
        ) : (
          GROUPS.filter((g) => grouped[g]).map((group) => (
            <div key={group} className="mb-3">
              <div className="px-2 py-1.5 text-xs font-medium text-fg-faint">{group}</div>
              {grouped[group].map((conv) => {
                const isActive = conv.id === activeId;

                if (editingId === conv.id) {
                  return (
                    <input
                      key={conv.id}
                      autoFocus
                      value={editingTitle}
                      onChange={(e) => setEditingTitle(e.target.value)}
                      onBlur={() => commitRename(conv.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') commitRename(conv.id);
                        if (e.key === 'Escape') setEditingId(null);
                      }}
                      aria-label="Conversation title"
                      className="w-full h-8 px-2 text-sm rounded-md border border-accent shadow-focus bg-surface text-fg focus:outline-none"
                    />
                  );
                }

                return (
                  <div
                    key={conv.id}
                    className={cn(
                      'group flex items-center gap-1 rounded-md pl-2.5 pr-0.5 h-8 transition-colors',
                      isActive ? 'bg-hover' : 'hover:bg-subtle'
                    )}
                  >
                    <button
                      onClick={() => onSelect(conv.id)}
                      className={cn('flex-1 min-w-0 text-left text-sm truncate', isActive ? 'text-fg font-medium' : 'text-fg-muted')}
                    >
                      {conv.title}
                    </button>
                    <div className={cn('transition-opacity', isActive ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 focus-within:opacity-100')}>
                      <RowActions
                        label={`Actions for ${conv.title}`}
                        items={[
                          {
                            id: 'rename',
                            label: 'Rename',
                            icon: <Pencil />,
                            onClick: () => {
                              setEditingId(conv.id);
                              setEditingTitle(conv.title);
                            },
                          },
                          { id: 'delete', label: 'Delete', icon: <Trash2 />, destructive: true, onClick: () => setDeleting(conv) },
                        ]}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ))
        )}
      </div>

      <ConfirmDialog
        isOpen={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={() => {
          if (deleting) onDelete(deleting.id);
          setDeleting(null);
        }}
        title="Delete conversation?"
        message={`"${deleting?.title ?? ''}" and its messages will be removed.`}
      />
    </div>
  );
};
