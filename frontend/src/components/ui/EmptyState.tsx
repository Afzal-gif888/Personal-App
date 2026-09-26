import React from 'react';
import { FolderOpen } from 'lucide-react';
import { Button } from './Button';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = <FolderOpen className="w-8 h-8 text-[#8A8A8A]" />,
  title,
  description,
  actionLabel,
  onAction,
  className,
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center rounded-lg border border-dashed border-[#EAEAEA] bg-[#F7F7F7]/50 ${className || ''}`}>
      <div className="flex items-center justify-center w-12 h-12 rounded-full bg-white border border-[#EAEAEA] shadow-2xs mb-3">
        {icon}
      </div>
      <h3 className="text-sm font-semibold text-[#111111] mb-1">{title}</h3>
      <p className="text-xs text-[#666666] max-w-sm mb-4 leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <Button variant="primary" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
