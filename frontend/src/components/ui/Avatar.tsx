import React, { useState } from 'react';
import { cn } from '../../utils/cn';

export interface AvatarProps {
  src?: string;
  name: string;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  className?: string;
}

const SIZES = {
  xs: 'size-6 text-2xs',
  sm: 'size-8 text-xs',
  md: 'size-9 text-sm',
  lg: 'size-14 text-lg',
};

export const Avatar: React.FC<AvatarProps> = ({ src, name, size = 'md', className }) => {
  const [failed, setFailed] = useState(false);
  const initials =
    name
      .split(' ')
      .filter(Boolean)
      .map((n) => n[0])
      .join('')
      .substring(0, 2)
      .toUpperCase() || 'U';

  return (
    <span
      className={cn(
        'relative inline-flex items-center justify-center rounded-full bg-accent-subtle text-accent-fg font-semibold overflow-hidden shrink-0 ring-1 ring-accent-line',
        SIZES[size],
        className
      )}
    >
      {src && !failed ? (
        <img src={src} alt={name} className="size-full object-cover" onError={() => setFailed(true)} />
      ) : (
        <span aria-hidden="true">{initials}</span>
      )}
    </span>
  );
};
