import React, { useImperativeHandle, useRef, useState } from 'react';
import { ArrowUp } from 'lucide-react';
import { Button } from '../ui/Button';
import { CHAT_UI_STORAGE_KEYS } from '../../services/chatService';

export interface ComposerHandle {
  setText: (text: string) => void;
}

interface ComposerProps {
  conversationId: string;
  disabled?: boolean;
  onSend: (text: string) => void;
}

const draftKey = (id: string) => `${CHAT_UI_STORAGE_KEYS.DRAFT_MESSAGE_PREFIX}${id}`;

function readDraft(id: string) {
  try {
    return id ? localStorage.getItem(draftKey(id)) || '' : '';
  } catch {
    return '';
  }
}

function writeDraft(id: string, value: string) {
  if (!id) return;
  try {
    if (value.trim()) localStorage.setItem(draftKey(id), value);
    else localStorage.removeItem(draftKey(id));
  } catch {
    // storage unavailable — drafts are a convenience only
  }
}

/**
 * Message input. Mount with `key={conversationId}` so each conversation
 * restores its own draft from the initial state rather than an effect.
 */
export const Composer = React.forwardRef<ComposerHandle, ComposerProps>(({ conversationId, disabled, onSend }, ref) => {
  const [text, setText] = useState(() => readDraft(conversationId));
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const update = (value: string) => {
    setText(value);
    writeDraft(conversationId, value);
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
    }
  };

  useImperativeHandle(ref, () => ({
    setText: (value: string) => {
      update(value);
      textareaRef.current?.focus();
    },
  }));

  const submit = (e?: React.FormEvent) => {
    e?.preventDefault();
    const value = text.trim();
    if (!value || disabled) return;
    update('');
    onSend(value);
  };

  return (
    <form onSubmit={submit} className="w-full">
      <div className="rounded-xl border border-line-strong bg-surface shadow-sm transition-[border-color,box-shadow] focus-within:border-accent focus-within:shadow-focus">
        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={(e) => update(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder="Ask about your tasks, schedule, bills or goals…"
          aria-label="Message the assistant"
          className="block w-full resize-none bg-transparent px-4 pt-3 pb-1 text-sm text-fg placeholder:text-fg-faint focus:outline-none min-h-11 max-h-44"
        />
        <div className="flex items-center justify-between gap-3 px-3 pb-2.5">
          <span className="hidden sm:inline text-xs text-fg-faint">Enter to send · Shift + Enter for a new line</span>
          <Button
            type="submit"
            size="sm"
            iconOnly
            disabled={!text.trim() || disabled}
            isLoading={disabled}
            aria-label="Send message"
            className="ml-auto rounded-lg"
          >
            <ArrowUp className="size-4" />
          </Button>
        </div>
      </div>
      <p className="mt-2 text-center text-xs text-fg-faint">
        The assistant proposes changes — nothing is saved to your workspace until you approve it.
      </p>
    </form>
  );
});

Composer.displayName = 'Composer';
