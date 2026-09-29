import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { PanelLeft, Eraser, Activity, BookOpen, Receipt, Wallet, Bell, Pencil, Loader2 } from 'lucide-react';
import { useChat } from '../hooks/useChat';
import { ChatMessageItem } from '../components/chat/ChatMessage';
import { TypingIndicator } from '../components/chat/TypingIndicator';
import { ConversationSidebar } from '../components/chat/ConversationSidebar';
import { Composer, type ComposerHandle } from '../components/chat/Composer';
import { Drawer } from '../components/ui/Drawer';
import { Button } from '../components/ui/Button';
import { Tooltip } from '../components/ui/Tooltip';

const STARTERS = [
  { icon: BookOpen, label: 'Study', prompt: 'Create a study plan for my Machine Learning exam' },
  { icon: Receipt, label: 'Bills', prompt: 'What bills do I have due this week?' },
  { icon: Wallet, label: 'Spending', prompt: 'Summarise my expenses for this month' },
  { icon: Bell, label: 'Reminder', prompt: 'Remind me about the DBMS group sync tomorrow at 7 PM' },
];

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

  const [historyOpen, setHistoryOpen] = useState(false);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [draftTitle, setDraftTitle] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<ComposerHandle>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, isSending]);

  const startRename = () => {
    if (!activeConversation) return;
    setDraftTitle(activeConversation.title);
    setIsEditingTitle(true);
  };

  const saveRename = async () => {
    if (activeConversation && draftTitle.trim() && draftTitle.trim() !== activeConversation.title) {
      await renameConversation({ id: activeConversation.id, title: draftTitle.trim() });
    }
    setIsEditingTitle(false);
  };

  const sidebarProps = {
    conversations,
    activeId: activeConversationId,
    onRename: (id: string, title: string) => renameConversation({ id, title }),
    onDelete: (id: string) => deleteConversation(id),
    isCreating: isCreatingConversation,
  };

  const isEmpty = !isLoadingMessages && messages.length === 0;

  return (
    <div className="flex h-[calc(100dvh-7rem)] md:h-[calc(100dvh-3.5rem)] min-h-0 bg-surface">
      <ConversationSidebar
        {...sidebarProps}
        className="hidden xl:flex"
        onSelect={selectConversation}
        onNewChat={() => createConversation()}
      />

      <Drawer isOpen={historyOpen} onClose={() => setHistoryOpen(false)} title={<span className="text-sm font-semibold">History</span>} bodyClassName="p-0">
        <ConversationSidebar
          {...sidebarProps}
          className="w-full border-r-0 [&>div:first-child]:hidden"
          onSelect={(id) => {
            selectConversation(id);
            setHistoryOpen(false);
          }}
          onNewChat={() => {
            createConversation();
            setHistoryOpen(false);
          }}
        />
      </Drawer>

      <section className="flex-1 flex flex-col min-w-0 bg-canvas">
        {/* Conversation header */}
        <div className="flex items-center gap-2 h-12 px-3 sm:px-4 border-b border-line bg-surface shrink-0">
          <Button
            variant="ghost"
            size="sm"
            iconOnly
            className="xl:hidden"
            onClick={() => setHistoryOpen(true)}
            aria-label="Show conversation history"
          >
            <PanelLeft className="size-4" />
          </Button>

          <div className="min-w-0 flex-1">
            {isEditingTitle ? (
              <input
                autoFocus
                value={draftTitle}
                onChange={(e) => setDraftTitle(e.target.value)}
                onBlur={saveRename}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') saveRename();
                  if (e.key === 'Escape') setIsEditingTitle(false);
                }}
                aria-label="Conversation title"
                className="w-full max-w-md h-8 px-2 text-sm font-medium rounded-md border border-accent shadow-focus bg-surface text-fg focus:outline-none"
              />
            ) : (
              <button onClick={startRename} className="group flex items-center gap-2 max-w-full text-left" disabled={!activeConversation}>
                <h1 className="text-sm font-semibold text-fg truncate">{activeConversation?.title || 'New conversation'}</h1>
                {activeConversation && (
                  <Pencil className="size-3.5 text-fg-faint opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                )}
              </button>
            )}
          </div>

          <Tooltip content="Agent activity" position="bottom">
            <Link
              to="/agent-runs"
              aria-label="Agent activity"
              className="inline-flex items-center justify-center size-8 rounded-md text-fg-subtle hover:text-fg hover:bg-hover"
            >
              <Activity className="size-4" />
            </Link>
          </Tooltip>
          <Tooltip content="Clear messages" position="bottom">
            <Button
              variant="ghost"
              size="sm"
              iconOnly
              onClick={() => clearHistory()}
              disabled={messages.length === 0}
              aria-label="Clear messages"
            >
              <Eraser className="size-4" />
            </Button>
          </Tooltip>
        </div>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {isLoadingMessages ? (
            <div className="flex items-center justify-center h-full gap-2 text-sm text-fg-subtle">
              <Loader2 className="size-4 animate-spin" />
              Loading conversation…
            </div>
          ) : isEmpty ? (
            <div className="flex flex-col items-center justify-center min-h-full px-4 py-10">
              <div className="w-full max-w-2xl text-center">
                <h2 className="text-xl font-semibold tracking-tight text-fg">What can I help you with?</h2>
                <p className="mt-2 text-sm text-fg-subtle">
                  I can read your tasks, calendar, bills and goals, and propose changes for you to approve.
                </p>
                <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
                  {STARTERS.map(({ icon: Icon, label, prompt }) => (
                    <button
                      key={prompt}
                      onClick={() => composerRef.current?.setText(prompt)}
                      className="flex items-start gap-3 p-4 text-left rounded-xl border border-line bg-surface shadow-xs hover:border-line-strong hover:bg-subtle/60 transition-colors"
                    >
                      <Icon className="size-4 mt-0.5 text-fg-subtle shrink-0" />
                      <span>
                        <span className="block text-xs font-medium text-fg-subtle">{label}</span>
                        <span className="block text-sm text-fg mt-0.5">{prompt}</span>
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-6">
              {messages.map((msg) => (
                <ChatMessageItem
                  key={msg.id}
                  message={msg}
                  onActionDecision={(approvalId, decision) => handleActionDecision({ approvalId, decision })}
                  onRetry={(messageId) => retryMessage(messageId)}
                  isDeciding={isDeciding}
                />
              ))}
              {isSending && <TypingIndicator />}
            </div>
          )}
        </div>

        {/* Composer */}
        <div className="shrink-0 px-4 sm:px-6 pt-2 pb-4 bg-canvas">
          <div className="max-w-3xl mx-auto">
            <Composer
              key={activeConversationId || 'new'}
              ref={composerRef}
              conversationId={activeConversationId}
              disabled={isSending}
              onSend={(text) => sendMessage(text)}
            />
          </div>
        </div>
      </section>
    </div>
  );
};
