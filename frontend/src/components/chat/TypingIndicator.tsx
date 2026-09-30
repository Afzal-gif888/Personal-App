import React from 'react';

export const TypingIndicator: React.FC = () => (
  <div className="flex items-center gap-2 h-7" role="status" aria-label="Assistant is working">
    <span className="flex gap-1">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="size-1.5 rounded-full bg-fg-faint animate-bounce"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </span>
    <span className="text-sm text-fg-subtle">Checking your workspace…</span>
  </div>
);
