import React from 'react'
import { clsx } from 'clsx'
import { Loader2 } from 'lucide-react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  icon?: React.ReactNode
  iconRight?: React.ReactNode
}

const variantClasses: Record<Variant, string> = {
  primary:
    'bg-brand-700 text-white hover:bg-brand-800 active:bg-brand-900 shadow-soft border border-brand-800',
  secondary:
    'bg-white text-warm-800 hover:bg-warm-100 active:bg-warm-200 border border-warm-300 shadow-soft',
  ghost:
    'bg-transparent text-warm-700 hover:bg-warm-100 active:bg-warm-200 border border-transparent',
  danger:
    'bg-red-600 text-white hover:bg-red-700 active:bg-red-800 shadow-soft border border-red-700',
  success:
    'bg-green-700 text-white hover:bg-green-800 active:bg-green-900 shadow-soft border border-green-800',
}

const sizeClasses: Record<Size, string> = {
  sm: 'h-7 px-2.5 text-xs gap-1.5',
  md: 'h-9 px-3.5 text-sm gap-2',
  lg: 'h-11 px-5 text-base gap-2',
}

export function Button({
  variant = 'secondary',
  size = 'md',
  loading = false,
  icon,
  iconRight,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={clsx(
        'inline-flex items-center justify-center font-medium rounded-lg transition-colors duration-150 select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed',
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
    >
      {loading ? (
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
      ) : (
        icon && <span className="flex-shrink-0">{icon}</span>
      )}
      {children}
      {iconRight && !loading && <span className="flex-shrink-0">{iconRight}</span>}
    </button>
  )
}
