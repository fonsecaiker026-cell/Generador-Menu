import { clsx } from 'clsx'

type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info' | 'purple' | 'amber' | 'muted'

interface BadgeProps {
  variant?: BadgeVariant
  size?: 'sm' | 'md'
  children: React.ReactNode
  className?: string
}

const variantClasses: Record<BadgeVariant, string> = {
  default: 'bg-warm-100 text-warm-700 border-warm-200',
  success: 'bg-green-50 text-green-700 border-green-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  error: 'bg-red-50 text-red-700 border-red-200',
  info: 'bg-blue-50 text-blue-700 border-blue-200',
  purple: 'bg-purple-50 text-purple-700 border-purple-200',
  amber: 'bg-amber-100 text-amber-800 border-amber-300',
  muted: 'bg-warm-50 text-warm-400 border-warm-200',
}

const sizeClasses = {
  sm: 'px-1.5 py-0.5 text-[10px] font-medium tracking-wide',
  md: 'px-2 py-0.5 text-xs font-medium',
}

export function Badge({ variant = 'default', size = 'md', children, className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full border uppercase leading-none',
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
    >
      {children}
    </span>
  )
}
