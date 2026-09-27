import React from 'react';
import { LogoIcon } from '../ui/Logo';

export const TypingIndicator: React.FC = () => (
  <div className="flex gap-3" role="status" aria-label="Assistant is working">
    <LogoIcon size={28} className="mt-0.5" />
    <div className="flex items-center gap-2 h-7">
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
  </div>
);
