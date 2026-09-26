import React from 'react';
import type { ButtonHTMLAttributes } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      disabled,
      leftIcon,
      rightIcon,
      type = 'button',
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-black disabled:opacity-50 disabled:pointer-events-none rounded-md text-xs sm:text-sm tracking-tight cursor-pointer';

    const variants = {
      primary: 'bg-black text-white hover:bg-neutral-800 active:bg-neutral-900 border border-transparent shadow-xs',
      secondary: 'bg-[#F7F7F7] text-[#111111] hover:bg-[#F3F3F3] active:bg-[#EAEAEA] border border-[#EAEAEA]',
      outline: 'bg-white text-[#111111] border border-[#EAEAEA] hover:bg-[#F7F7F7] active:bg-[#F3F3F3]',
      ghost: 'bg-transparent text-[#666666] hover:text-[#111111] hover:bg-[#F7F7F7]',
      destructive: 'bg-red-600 text-white hover:bg-red-700 active:bg-red-800 border border-transparent',
    };

    const sizes = {
      sm: 'h-8 px-3 text-xs gap-1.5',
      md: 'h-9 px-4 text-xs sm:text-sm gap-2',
      lg: 'h-10 px-5 text-sm gap-2',
    };

    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin text-current shrink-0" />
        ) : (
          leftIcon && <span className="shrink-0">{leftIcon}</span>
        )}
        <span>{children}</span>
        {!isLoading && rightIcon && <span className="shrink-0">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';
