import React from 'react';
import type { ButtonHTMLAttributes } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../utils/cn';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive';
export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  /** Square button that only contains an icon. Requires an aria-label. */
  iconOnly?: boolean;
}

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    'bg-accent text-white border border-accent shadow-xs hover:bg-accent-hover hover:border-accent-hover',
  secondary:
    'bg-surface text-fg border border-line-strong shadow-xs hover:bg-subtle',
  outline:
    'bg-surface text-fg border border-line-strong shadow-xs hover:bg-subtle',
  ghost:
    'bg-transparent text-fg-muted border border-transparent hover:bg-hover hover:text-fg',
  destructive:
    'bg-danger-solid text-white border border-danger-solid shadow-xs hover:bg-danger hover:border-danger',
};

const SIZES: Record<ButtonSize, string> = {
  xs: 'h-7 px-2 text-xs gap-1 rounded-md',
  sm: 'h-8 px-3 text-sm gap-1.5 rounded-md',
  md: 'h-9 px-3.5 text-sm gap-2 rounded-lg',
  lg: 'h-10 px-4 text-sm gap-2 rounded-lg',
};

const ICON_SIZES: Record<ButtonSize, string> = {
  xs: 'h-7 w-7 rounded-md',
  sm: 'h-8 w-8 rounded-md',
  md: 'h-9 w-9 rounded-lg',
  lg: 'h-10 w-10 rounded-lg',
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      iconOnly = false,
      disabled,
      leftIcon,
      rightIcon,
      type = 'button',
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || isLoading}
        className={cn(
          'inline-flex items-center justify-center font-medium whitespace-nowrap transition-colors select-none',
          'focus-visible:outline-none focus-visible:shadow-focus',
          'disabled:opacity-50 disabled:pointer-events-none [&_svg]:shrink-0',
          VARIANTS[variant],
          iconOnly ? ICON_SIZES[size] : SIZES[size],
          className
        )}
        {...props}
      >
        {isLoading ? <Loader2 className="size-4 animate-spin" /> : leftIcon}
        {iconOnly ? (!isLoading && children) : children && <span className="truncate">{children}</span>}
        {!isLoading && rightIcon}
      </button>
    );
  }
);

Button.displayName = 'Button';
