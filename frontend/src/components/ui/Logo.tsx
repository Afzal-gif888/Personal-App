import React from 'react';
import { cn } from '../../utils/cn';

interface LogoProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  withText?: boolean;
  subtext?: string;
  className?: string;
}

const SIZE_MAP = { xs: 20, sm: 28, md: 32, lg: 40, xl: 48 };

/** The app mark on a white tile, so its navy strokes stay visible in dark mode too. */
export const LogoIcon: React.FC<{ size?: number; className?: string }> = ({ size = 28, className }) => (
  <span
    className={cn('inline-flex shrink-0 items-center justify-center rounded-lg bg-white ring-1 ring-black/5', className)}
    style={{ width: size, height: size, padding: Math.max(1, Math.round(size * 0.06)) }}
    aria-hidden="true"
  >
    <img src={size > 48 ? '/logo.png' : '/logo-96.png'} alt="" className="size-full object-contain" draggable={false} />
  </span>
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
