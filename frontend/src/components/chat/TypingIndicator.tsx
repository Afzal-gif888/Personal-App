import React from 'react';
import { Sparkles } from 'lucide-react';

export const TypingIndicator: React.FC = () => {
  return (
    <div className="flex items-center gap-2 p-3 rounded-lg bg-[#F7F7F7] border border-[#EAEAEA] max-w-xs text-left">
      <Sparkles className="w-4 h-4 text-emerald-600 animate-spin" />
      <span className="text-xs text-[#666666] font-medium">AgentOS is reasoning...</span>
    </div>
  );
};
