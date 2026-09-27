import React from 'react';
import { cn } from '../../utils/cn';

export const Skeleton: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className, ...props }) => (
  <div className={cn('animate-pulse rounded-md bg-hover', className)} {...props} />
);
