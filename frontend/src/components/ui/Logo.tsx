import React from 'react';
import { cn } from '../../utils/cn';

interface LogoProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  withText?: boolean;
  subtext?: string;
  className?: string;
}

const SIZE_MAP = { xs: 20, sm: 28, md: 32, lg: 40, xl: 48 };

export const LogoIcon: React.FC<{ size?: number; className?: string }> = ({ size = 28, className }) => (
  <svg
    viewBox="0 0 32 32"
    width={size}
    height={size}
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={cn('shrink-0', className)}
    aria-hidden="true"
  >
    <rect width="32" height="32" rx="8" fill="var(--color-accent)" />
    <path d="M12 23V9.5h4.75a4.25 4.25 0 0 1 0 8.5H12" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const Logo: React.FC<LogoProps> = ({ size = 'md', withText = false, subtext, className }) => {
  if (!withText) return <LogoIcon size={SIZE_MAP[size]} className={className} />;

  return (
    <div className={cn('flex items-center gap-2.5 min-w-0', className)}>
      <LogoIcon size={SIZE_MAP[size]} />
      <div className="flex flex-col min-w-0 leading-tight">
        <span className="font-semibold text-sm text-fg truncate">It's Personal</span>
        {subtext && <span className="text-xs text-fg-subtle truncate">{subtext}</span>}
      </div>
    </div>
  );
};
