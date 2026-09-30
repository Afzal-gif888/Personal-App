import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Copy, Check, ChevronRight, RotateCcw, AlertCircle, CircleCheck } from 'lucide-react';
import type { ChatMessage as ChatMessageType } from '../../types';
import { ActionCard } from './ActionCard';
import { cn } from '../../utils/cn';

export interface ChatMessageProps {
  message: ChatMessageType;
  onActionDecision: (approvalId: string, decision: 'approved' | 'rejected') => void;
  onRetry?: (messageId: string) => void;
  isDeciding?: boolean;
}

/** Renders **bold** segments from the assistant's plain-text replies. */
function renderInline(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? (
      <strong key={i} className="font-semibold text-fg">
        {part.slice(2, -2)}
      </strong>
    ) : (
      <React.Fragment key={i}>{part}</React.Fragment>
    )
  );
}

export const ChatMessageItem: React.FC<ChatMessageProps> = ({ message, onActionDecision, onRetry, isDeciding = false }) => {
  const [copied, setCopied] = useState(false);
  const [showSteps, setShowSteps] = useState(false);

  const isUser = message.role === 'user';
  const text = message.content;
  const time = message.createdAt
    ? new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit' }).format(new Date(message.createdAt))
    : '';

  const actions = message.metadata?.actions ?? [];
  const steps = message.metadata?.steps ?? [];
  const isError = message.metadata?.status === 'error';

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] sm:max-w-[75%]">
          <div className="rounded-2xl rounded-br-md bg-accent text-white px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words">
            {text}
          </div>
          <p className="mt-1 text-right text-xs text-fg-faint">{time}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="group">
      <div className="min-w-0">
        {isError && (
          <p className="flex items-center gap-1.5 text-sm text-danger mb-1">
            <AlertCircle className="size-4" />
            {message.metadata?.error || "The request couldn't be completed."}
          </p>
        )}
        <div className="text-sm text-fg-muted leading-relaxed whitespace-pre-wrap break-words">{renderInline(text)}</div>

        {/* Just the reply: time and actions sit quietly underneath, like the user's own messages. */}
        <div className="mt-1 flex items-center gap-1 h-7">
          <span className="text-xs text-fg-faint">{time}</span>
          <div className="flex items-center gap-0.5 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-md text-fg-faint hover:text-fg hover:bg-hover"
              aria-label="Copy message"
            >
              {copied ? <Check className="size-3.5 text-success" /> : <Copy className="size-3.5" />}
            </button>
            {isError && onRetry && (
              <button
                onClick={() => onRetry(message.id)}
                className="inline-flex items-center gap-1 px-1.5 py-1 rounded-md text-xs text-danger hover:bg-danger-subtle"
              >
                <RotateCcw className="size-3.5" />
                Retry
              </button>
            )}
          </div>
        </div>

        {steps.length > 0 && (
          <div className="mt-3">
            <button
              onClick={() => setShowSteps((v) => !v)}
              aria-expanded={showSteps}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-fg-subtle hover:text-fg"
            >
              <ChevronRight className={cn('size-3.5 transition-transform', showSteps && 'rotate-90')} />
              Agent run · {steps.length} steps
            </button>
            {showSteps && (
              <div className="mt-2 rounded-lg border border-line bg-subtle/50 px-3 py-2.5 animate-fade-in">
                <ol className="space-y-1.5">
                  {steps.map((step) => (
                    <li key={step.id} className="flex items-center gap-2 text-xs text-fg-muted">
                      <CircleCheck className="size-3.5 text-success shrink-0" />
                      <span className="truncate">{step.title}</span>
                    </li>
                  ))}
                </ol>
                <Link to={message.agentRunId ? `/agent-runs/${message.agentRunId}` : '/agent-runs'} className="inline-block mt-2.5 text-xs font-medium text-accent hover:text-accent-hover">
                  View in Agent activity
                </Link>
              </div>
            )}
          </div>
        )}

        {actions.map((card) => (
          <ActionCard key={card.approvalId} card={card} onDecision={onActionDecision} isPending={isDeciding} />
        ))}
      </div>
    </div>
  );
};
