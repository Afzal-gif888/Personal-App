import React, { useState, useMemo } from 'react';
import {
  Plus,
  MessageSquare,
  Search,
  Edit2,
  Trash2,
  Check,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import type { Conversation } from '../../types';
import { Button } from '../ui/Button';
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
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

interface GroupedConversations {
  today: Conversation[];
  yesterday: Conversation[];
  previous7Days: Conversation[];
  older: Conversation[];
}

export const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  conversations,
  activeId,
  onSelect,
  onNewChat,
  onRename,
  onDelete,
  isCreating = false,
  className = '',
  collapsed = false,
  onToggleCollapse,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

  // Filter conversations by search query
  const filteredConversations = useMemo(() => {
    if (!searchQuery.trim()) return conversations;
    const query = searchQuery.toLowerCase();
    return conversations.filter((c) => c.title.toLowerCase().includes(query));
  }, [conversations, searchQuery]);

  // Group conversations chronologically (Today, Yesterday, Previous 7 days, Older)
  const grouped = useMemo(() => {
    const groups: GroupedConversations = {
      today: [],
      yesterday: [],
      previous7Days: [],
      older: [],
    };

    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const startOfYesterday = startOfToday - 86400000;
    const startOf7Days = startOfToday - 6 * 86400000;

    filteredConversations.forEach((conv) => {
      const date = new Date(conv.updated_at || conv.created_at).getTime();
      if (date >= startOfToday) {
        groups.today.push(conv);
      } else if (date >= startOfYesterday) {
        groups.yesterday.push(conv);
      } else if (date >= startOf7Days) {
        groups.previous7Days.push(conv);
      } else {
        groups.older.push(conv);
      }
    });

    return groups;
  }, [filteredConversations]);

  const startEditing = (conv: Conversation) => {
    setEditingId(conv.id);
    setEditingTitle(conv.title);
  };

  const saveRename = (id: string) => {
    if (editingTitle.trim()) {
      onRename(id, editingTitle.trim());
    }
    setEditingId(null);
    setEditingTitle('');
  };

  const cancelRename = () => {
    setEditingId(null);
    setEditingTitle('');
  };

  if (collapsed) {
    return (
      <div className="w-12 h-full flex flex-col items-center py-3 border-r border-[#EAEAEA] bg-[#FAFAFA] shrink-0">
        <button
          onClick={onToggleCollapse}
          title="Expand Chat History"
          className="p-1.5 rounded-md hover:bg-[#EAEAEA] text-[#666666] mb-3 transition-colors cursor-pointer"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
        <button
          onClick={onNewChat}
          title="New Chat"
          disabled={isCreating}
          className="p-2 rounded-lg bg-black text-white hover:bg-neutral-800 transition-colors shadow-xs cursor-pointer"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>
    );
  }

  const renderGroup = (title: string, list: Conversation[]) => {
    if (list.length === 0) return null;

    return (
      <div key={title} className="space-y-1 mb-4">
        <h4 className="px-2 text-[10px] font-semibold text-[#8A8A8A] uppercase tracking-wider">
          {title}
        </h4>
        <div className="space-y-0.5">
          {list.map((conv) => {
            const isActive = conv.id === activeId;
            const isEditing = editingId === conv.id;

            if (isEditing) {
              return (
                <div
                  key={conv.id}
                  className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg bg-white border border-black shadow-xs"
                >
                  <input
                    type="text"
                    value={editingTitle}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') saveRename(conv.id);
                      if (e.key === 'Escape') cancelRename();
                    }}
                    autoFocus
                    className="flex-1 text-xs text-[#111111] bg-transparent focus:outline-none min-w-0"
                  />
                  <button
                    onClick={() => saveRename(conv.id)}
                    className="p-1 text-emerald-600 hover:text-emerald-700 cursor-pointer"
                    title="Save"
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={cancelRename}
                    className="p-1 text-[#8A8A8A] hover:text-[#111111] cursor-pointer"
                    title="Cancel"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            }

            return (
              <div
                key={conv.id}
                className={cn(
                  'group relative flex items-center justify-between rounded-lg px-2.5 py-2 text-xs transition-colors cursor-pointer',
                  isActive
                    ? 'bg-white text-[#111111] font-medium shadow-xs border border-[#EAEAEA]'
                    : 'text-[#666666] hover:bg-[#F2F2F2] hover:text-[#111111]'
                )}
                onClick={() => onSelect(conv.id)}
              >
                <div className="flex items-center gap-2 min-w-0 flex-1 pr-1">
                  <MessageSquare className={cn('w-3.5 h-3.5 shrink-0', isActive ? 'text-black' : 'text-[#8A8A8A]')} />
                  <span className="truncate text-left">{conv.title}</span>
                </div>

                {/* Actions Menu */}
                <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 shrink-0 transition-opacity">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      startEditing(conv);
                    }}
                    className="p-1 rounded text-[#8A8A8A] hover:text-[#111111] hover:bg-neutral-200/60 transition-colors"
                    title="Rename conversation"
                  >
                    <Edit2 className="w-3 h-3" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm(`Delete conversation "${conv.title}"?`)) {
                        onDelete(conv.id);
                      }
                    }}
                    className="p-1 rounded text-[#8A8A8A] hover:text-red-600 hover:bg-neutral-200/60 transition-colors"
                    title="Delete conversation"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div
      className={cn(
        'w-64 h-full flex flex-col border-r border-[#EAEAEA] bg-[#FAFAFA] shrink-0 text-left select-none',
        className
      )}
    >
      {/* Sidebar Header */}
      <div className="p-3 border-b border-[#EAEAEA] space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold text-[#8A8A8A] uppercase tracking-wider">
            Conversations
          </span>
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className="p-1 rounded text-[#8A8A8A] hover:text-[#111111] hover:bg-[#EAEAEA] transition-colors cursor-pointer"
              title="Collapse history"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* New Chat Button */}
        <Button
          variant="primary"
          size="sm"
          onClick={onNewChat}
          isLoading={isCreating}
          leftIcon={<Plus className="w-4 h-4" />}
          className="w-full justify-center h-8 text-xs font-medium"
        >
          New Chat
        </Button>

        {/* Search Bar */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#8A8A8A]" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-2.5 py-1 text-xs bg-white rounded-md border border-[#EAEAEA] placeholder:text-[#8A8A8A] text-[#111111] focus:outline-none focus:border-black"
          />
        </div>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto p-2.5">
        {filteredConversations.length === 0 ? (
          <div className="text-center py-8 px-2 text-[#8A8A8A] text-xs">
            {searchQuery ? 'No matching conversations' : 'No conversations yet'}
          </div>
        ) : (
          <>
            {renderGroup('Today', grouped.today)}
            {renderGroup('Yesterday', grouped.yesterday)}
            {renderGroup('Previous 7 days', grouped.previous7Days)}
            {renderGroup('Older', grouped.older)}
          </>
        )}
      </div>
    </div>
  );
};
