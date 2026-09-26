import React, { useState } from 'react';
import { Sparkles, Copy, Check, ChevronDown, ChevronUp, User, RotateCcw, AlertCircle } from 'lucide-react';
import type { ChatMessage as ChatMessageType } from '../../types';
import { ActionCard } from './ActionCard';
import { LogoIcon } from '../ui/Logo';
import { cn } from '../../utils/cn';

export interface ChatMessageProps {
  message: ChatMessageType;
  onActionDecision: (messageId: string, decision: 'approved' | 'rejected') => void;
  onRetry?: (messageId: string) => void;
  isDeciding?: boolean;
}

export const ChatMessageItem: React.FC<ChatMessageProps> = ({
  message,
  onActionDecision,
  onRetry,
  isDeciding = false,
}) => {
  const [copied, setCopied] = useState(false);
  const [showSteps, setShowSteps] = useState(false);

  const role = message.role || message.sender || 'assistant';
  const isUser = role === 'user';
  const textContent = message.content || message.text || '';
  const timeDisplay = message.timestamp || (message.created_at
    ? new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit' }).format(new Date(message.created_at))
    : '');

  const actionCard = message.metadata?.actionCard || message.actionCard;
  const steps = message.metadata?.steps || message.steps || [];
  const isError = message.isError || message.metadata?.status === 'error';

  const handleCopy = () => {
    navigator.clipboard.writeText(textContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={cn('flex gap-2 sm:gap-3 text-left w-full max-w-3xl mx-auto py-1.5 sm:py-2 group')}>
      {/* Sender Avatar */}
      <div
        className={cn(
          'w-6 h-6 sm:w-7 sm:h-7 rounded-md flex items-center justify-center shrink-0 border text-xs font-semibold mt-0.5',
          isUser
            ? 'bg-black text-white border-black'
            : 'bg-transparent border-transparent'
        )}
      >
        {isUser ? (
          <User className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
        ) : (
          <>
            <LogoIcon size={24} className="sm:hidden" />
            <LogoIcon size={28} className="hidden sm:block" />
          </>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 space-y-1.5 min-w-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 sm:gap-2">
            <span className="text-[11px] sm:text-xs font-semibold text-[#111111]">
              {isUser ? 'You' : 'AgentOS Assistant'}
            </span>
            <span className="text-[9px] sm:text-[10px] text-[#8A8A8A]">{timeDisplay}</span>
          </div>

          {/* Actions: Always visible on mobile, hover on desktop */}
          <div className="flex items-center gap-1 opacity-70 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
            {/* Copy Button */}
            <button
              onClick={handleCopy}
              className="text-[#8A8A8A] hover:text-[#111111] p-1 rounded hover:bg-[#F7F7F7] active:bg-[#EAEAEA] transition-colors cursor-pointer"
              title="Copy message"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            </button>

            {/* Retry Button on Error */}
            {isError && onRetry && (
              <button
                onClick={() => onRetry(message.id)}
                className="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50 active:bg-red-100 cursor-pointer flex items-center gap-1 text-[10px]"
                title="Retry sending"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Retry</span>
              </button>
            )}
          </div>
        </div>

        {/* Text Message Bubble */}
        <div
          className={cn(
            'text-xs sm:text-sm leading-relaxed rounded-lg p-2.5 sm:p-3 border whitespace-pre-wrap break-words',
            isUser
              ? 'bg-black text-white border-black inline-block ml-auto'
              : isError
              ? 'bg-red-50 text-red-900 border-red-200'
              : 'bg-[#F7F7F7]/80 text-[#111111] border-[#EAEAEA]'
          )}
        >
          {isError && (
            <div className="flex items-center gap-1.5 text-xs text-red-600 font-medium mb-1">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>Failed to process request</span>
            </div>
          )}
          {textContent}
        </div>

        {/* Execution Steps Collapsible Accordion */}
        {!isUser && steps.length > 0 && (
          <div className="mt-1.5 sm:mt-2">
            <button
              onClick={() => setShowSteps(!showSteps)}
              className="inline-flex items-center gap-1 text-[10px] sm:text-[11px] text-[#666666] hover:text-[#111111] py-1 transition-colors cursor-pointer"
            >
              <Sparkles className="w-3 h-3 text-emerald-600" />
              <span>{showSteps ? 'Hide steps' : `View ${steps.length} reasoning steps`}</span>
              {showSteps ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>

            {showSteps && (
              <div className="mt-1 rounded-md border border-[#EAEAEA] bg-white p-2 sm:p-2.5 space-y-1 text-[10px] sm:text-[11px] animate-in fade-in duration-150">
                {steps.map((step) => (
                  <div key={step.id} className="flex items-center justify-between text-[#666666] gap-2">
                    <span className="flex items-center gap-1.5 truncate">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                      <span className="truncate">{step.title}</span>
                    </span>
                    <span className="text-[9px] sm:text-[10px] text-[#8A8A8A] shrink-0">{step.timestamp}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Special Action Card */}
        {actionCard && (
          <ActionCard
            card={actionCard}
            messageId={message.id}
            onDecision={onActionDecision}
            isPending={isDeciding}
          />
        )}
      </div>
    </div>
  );
};
