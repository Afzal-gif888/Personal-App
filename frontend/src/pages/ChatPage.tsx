import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Sparkles,
  Trash2,
  Menu,
  X,
  Edit2,
  Check,
  PanelLeftClose,
  PanelLeft,
} from 'lucide-react';
import { useChat } from '../hooks/useChat';
import { ChatMessageItem } from '../components/chat/ChatMessage';
import { TypingIndicator } from '../components/chat/TypingIndicator';
import { ConversationSidebar } from '../components/chat/ConversationSidebar';
import { Button } from '../components/ui/Button';
import { CHAT_UI_STORAGE_KEYS } from '../services/chatService';

export const ChatPage: React.FC = () => {
  const {
    conversations,
    activeConversation,
    activeConversationId,
    selectConversation,
    createConversation,
    isCreatingConversation,
    messages,
    isLoadingMessages,
    sendMessage,
    isSending,
    retryMessage,
    renameConversation,
    deleteConversation,
    handleActionDecision,
    isDeciding,
    clearHistory,
  } = useChat();

  const [inputText, setInputText] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem(CHAT_UI_STORAGE_KEYS.SIDEBAR_COLLAPSED) === 'true';
    } catch {
      return false;
    }
  });
  const [mobileHistoryOpen, setMobileHistoryOpen] = useState(false);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [tempTitle, setTempTitle] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Restore draft message for active conversation from temporary localStorage
  useEffect(() => {
    if (activeConversationId) {
      try {
        const draft = localStorage.getItem(`${CHAT_UI_STORAGE_KEYS.DRAFT_MESSAGE_PREFIX}${activeConversationId}`);
        setInputText(draft || '');
      } catch {
        // ignore
      }
    }
  }, [activeConversationId]);

  // Persist draft message to temporary localStorage on change
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setInputText(val);
    if (activeConversationId) {
      try {
        if (val.trim()) {
          localStorage.setItem(`${CHAT_UI_STORAGE_KEYS.DRAFT_MESSAGE_PREFIX}${activeConversationId}`, val);
        } else {
          localStorage.removeItem(`${CHAT_UI_STORAGE_KEYS.DRAFT_MESSAGE_PREFIX}${activeConversationId}`);
        }
      } catch {
        // ignore
      }
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending]);

  const toggleSidebarCollapse = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(CHAT_UI_STORAGE_KEYS.SIDEBAR_COLLAPSED, String(next));
      } catch {
        // ignore
      }
      return next;
    });
  };

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || isSending) return;
    const textToSend = inputText.trim();
    setInputText('');

    if (activeConversationId) {
      try {
        localStorage.removeItem(`${CHAT_UI_STORAGE_KEYS.DRAFT_MESSAGE_PREFIX}${activeConversationId}`);
      } catch {
        // ignore
      }
    }

    await sendMessage(textToSend);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleStartRename = () => {
    if (activeConversation) {
      setTempTitle(activeConversation.title);
      setIsEditingTitle(true);
    }
  };

  const handleSaveRename = async () => {
    if (activeConversation && tempTitle.trim()) {
      await renameConversation({ id: activeConversation.id, title: tempTitle.trim() });
    }
    setIsEditingTitle(false);
  };

  const quickPrompts = [
    'Create a study plan for my Machine Learning exam',
    'What bills do I have due this week?',
    'Summarize my spending and expenses for this month',
    'Set a reminder for DBMS group sync tomorrow at 7 PM',
    'Show my progress on summer internship applications',
  ];

  return (
    <div className="flex h-[calc(100vh-6.5rem)] rounded-xl border border-[#EAEAEA] bg-white shadow-xs overflow-hidden text-left relative">
      {/* Desktop Conversation History Sidebar */}
      <div className="hidden md:flex">
        <ConversationSidebar
          conversations={conversations}
          activeId={activeConversationId}
          onSelect={(id) => {
            selectConversation(id);
          }}
          onNewChat={() => createConversation()}
          onRename={(id, title) => renameConversation({ id, title })}
          onDelete={(id) => deleteConversation(id)}
          isCreating={isCreatingConversation}
          collapsed={sidebarCollapsed}
          onToggleCollapse={toggleSidebarCollapse}
        />
      </div>

      {/* Mobile History Drawer Overlay */}
      {mobileHistoryOpen && (
        <div className="md:hidden fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex">
          <div className="w-72 h-full bg-white flex flex-col shadow-xl animate-in slide-in-from-left duration-200">
            <div className="p-3 border-b border-[#EAEAEA] flex items-center justify-between">
              <span className="text-xs font-semibold text-[#111111]">Chat History</span>
              <button
                onClick={() => setMobileHistoryOpen(false)}
                className="p-1 rounded text-[#8A8A8A] hover:text-[#111111] hover:bg-[#F7F7F7] cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              <ConversationSidebar
                conversations={conversations}
                activeId={activeConversationId}
                onSelect={(id) => {
                  selectConversation(id);
                  setMobileHistoryOpen(false);
                }}
                onNewChat={() => {
                  createConversation();
                  setMobileHistoryOpen(false);
                }}
                onRename={(id, title) => renameConversation({ id, title })}
                onDelete={(id) => deleteConversation(id)}
                isCreating={isCreatingConversation}
                className="w-full border-r-0"
              />
            </div>
          </div>
          <div className="flex-1" onClick={() => setMobileHistoryOpen(false)} />
        </div>
      )}

      {/* Main Chat Conversation Pane */}
      <div className="flex-1 flex flex-col min-w-0 bg-white">
        {/* Chat Pane Header */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#EAEAEA] bg-[#FAFAFA]/70">
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            {/* Mobile Sidebar Toggle */}
            <button
              onClick={() => setMobileHistoryOpen(true)}
              className="md:hidden p-1.5 rounded-md hover:bg-[#EAEAEA] text-[#666666] shrink-0 cursor-pointer"
              title="Open Chat History"
            >
              <Menu className="w-4 h-4" />
            </button>

            {/* Desktop Sidebar Toggle Icon */}
            <button
              onClick={toggleSidebarCollapse}
              className="hidden md:flex p-1.5 rounded-md hover:bg-[#EAEAEA] text-[#666666] shrink-0 transition-colors cursor-pointer"
              title={sidebarCollapsed ? 'Expand History Sidebar' : 'Collapse History Sidebar'}
            >
              {sidebarCollapsed ? <PanelLeft className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
            </button>

            {/* Active Conversation Title & Inline Rename */}
            <div className="min-w-0 flex-1">
              {isEditingTitle ? (
                <div className="flex items-center gap-1.5 max-w-sm">
                  <input
                    type="text"
                    value={tempTitle}
                    onChange={(e) => setTempTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveRename();
                      if (e.key === 'Escape') setIsEditingTitle(false);
                    }}
                    autoFocus
                    className="w-full px-2 py-0.5 text-xs font-semibold text-[#111111] bg-white border border-black rounded"
                  />
                  <button
                    onClick={handleSaveRename}
                    className="p-1 text-emerald-600 hover:text-emerald-700 cursor-pointer"
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setIsEditingTitle(false)}
                    className="p-1 text-[#8A8A8A] hover:text-[#111111] cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2 group cursor-pointer" onClick={handleStartRename}>
                  <h2 className="text-xs sm:text-sm font-semibold text-[#111111] truncate">
                    {activeConversation?.title || 'Personal AI Assistant'}
                  </h2>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleStartRename();
                    }}
                    className="opacity-0 group-hover:opacity-100 p-0.5 text-[#8A8A8A] hover:text-[#111111] transition-opacity cursor-pointer"
                    title="Rename conversation"
                  >
                    <Edit2 className="w-3 h-3" />
                  </button>
                </div>
              )}
              <p className="text-[10px] text-[#8A8A8A] hidden sm:block">
                Autonomous agent session · Synchronized with personal workspace
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-1 shrink-0">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => clearHistory()}
              leftIcon={<Trash2 className="w-3.5 h-3.5" />}
              className="text-xs text-[#8A8A8A] hover:text-[#111111] h-7 px-2"
            >
              Clear
            </Button>
          </div>
        </div>

        {/* Message Scroll Area */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {isLoadingMessages ? (
            <div className="flex flex-col items-center justify-center h-64 text-center space-y-2 text-[#8A8A8A] text-xs">
              <div className="w-6 h-6 border-2 border-[#111111] border-t-transparent rounded-full animate-spin" />
              <span>Loading conversation history...</span>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-72 text-center space-y-4 max-w-md mx-auto">
              <div className="w-12 h-12 rounded-2xl bg-[#0B0D14] border border-[#1F2437] flex items-center justify-center shadow-sm">
                <Sparkles className="w-6 h-6 text-cyan-400" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[#111111]">
                  How can AgentOS assist your life and studies today?
                </h3>
                <p className="text-xs text-[#666666] mt-1">
                  Ask me to plan exam preparation, review upcoming bills, track expenses, schedule appointments, or check your goals.
                </p>
              </div>

              {/* Starter Suggestions */}
              <div className="w-full grid grid-cols-1 gap-2 pt-2">
                {quickPrompts.slice(0, 3).map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setInputText(prompt);
                      textareaRef.current?.focus();
                    }}
                    className="p-2.5 rounded-lg border border-[#EAEAEA] bg-[#FAFAFA] text-left text-xs text-[#333333] hover:border-black hover:bg-white transition-all cursor-pointer"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <ChatMessageItem
                key={msg.id}
                message={msg}
                onActionDecision={(messageId, decision) => handleActionDecision({ messageId, decision })}
                onRetry={(messageId) => retryMessage(messageId)}
                isDeciding={isDeciding}
              />
            ))
          )}

          {isSending && (
            <div className="py-2 max-w-3xl mx-auto">
              <TypingIndicator />
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Suggestion Pills */}
        <div className="px-4 py-2 flex items-center gap-1.5 overflow-x-auto no-scrollbar border-t border-[#F2F2F2] bg-[#FAFAFA]/50">
          {quickPrompts.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => {
                setInputText(prompt);
                textareaRef.current?.focus();
              }}
              className="px-2.5 py-1 rounded-full text-[11px] font-medium text-[#666666] bg-white border border-[#EAEAEA] hover:border-black hover:text-[#111111] transition-colors whitespace-nowrap shrink-0 cursor-pointer shadow-2xs"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Input Bar Form */}
        <form onSubmit={handleSend} className="p-3 bg-white border-t border-[#EAEAEA]">
          <div className="relative flex items-end rounded-xl border border-[#EAEAEA] bg-white p-2 shadow-xs focus-within:border-black focus-within:ring-1 focus-within:ring-black transition-all">
            <textarea
              ref={textareaRef}
              rows={1}
              placeholder="Ask anything about your studies, schedule, bills, or goals..."
              value={inputText}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              disabled={isSending}
              className="flex-1 bg-transparent px-2 py-1 text-xs sm:text-sm text-[#111111] placeholder:text-[#8A8A8A] focus:outline-none resize-none max-h-32 min-h-[36px]"
            />
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={!inputText.trim() || isSending}
              isLoading={isSending}
              className="h-8 px-3 rounded-lg shrink-0"
            >
              <Send className="w-3.5 h-3.5" />
            </Button>
          </div>
          <div className="flex items-center justify-between px-1 pt-1.5 text-[10px] text-[#8A8A8A]">
            <span>Press Enter to send · Shift + Enter for new line</span>
            <span>AgentOS v2.4</span>
          </div>
        </form>
      </div>
    </div>
  );
};
