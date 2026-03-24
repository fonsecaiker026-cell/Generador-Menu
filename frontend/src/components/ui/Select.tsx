import * as SelectPrimitive from '@radix-ui/react-select'
import { ChevronDown, Check } from 'lucide-react'
import { clsx } from 'clsx'

interface Option {
  value: string
  label: string
}

interface SelectProps {
  value: string
  onChange: (value: string) => void
  options: Option[]
  placeholder?: string
  label?: string
  className?: string
  disabled?: boolean
}

export function Select({ value, onChange, options, placeholder, label, className, disabled }: SelectProps) {
  return (
    <div className={clsx('flex flex-col gap-1', className)}>
      {label && <label className="text-xs font-medium text-warm-600 uppercase tracking-wide">{label}</label>}
      <SelectPrimitive.Root value={value} onValueChange={onChange} disabled={disabled}>
        <SelectPrimitive.Trigger
          className={clsx(
            'inline-flex items-center justify-between gap-2 h-9 px-3 text-sm',
            'bg-white border border-warm-300 rounded-lg text-warm-800',
            'hover:border-warm-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'transition-colors',
          )}
        >
          <SelectPrimitive.Value placeholder={placeholder ?? 'Seleccionar…'} />
          <SelectPrimitive.Icon>
            <ChevronDown className="w-4 h-4 text-warm-400" />
          </SelectPrimitive.Icon>
        </SelectPrimitive.Trigger>

        <SelectPrimitive.Portal>
          <SelectPrimitive.Content
            className="z-50 min-w-[180px] bg-white border border-warm-200 rounded-lg shadow-elevated overflow-hidden animate-fade-in"
            position="popper"
            sideOffset={4}
          >
            <SelectPrimitive.Viewport className="p-1 max-h-72 overflow-y-auto">
              {options.map((opt) => (
                <SelectPrimitive.Item
                  key={opt.value}
                  value={opt.value}
                  className={clsx(
                    'flex items-center gap-2 px-3 py-2 text-sm rounded-md cursor-pointer select-none outline-none',
                    'text-warm-800 data-[highlighted]:bg-warm-100 data-[highlighted]:text-warm-900',
                    'data-[state=checked]:text-brand-700 data-[state=checked]:font-medium',
                  )}
                >
                  <SelectPrimitive.ItemIndicator>
                    <Check className="w-3.5 h-3.5 text-brand-600" />
                  </SelectPrimitive.ItemIndicator>
                  <SelectPrimitive.ItemText>{opt.label}</SelectPrimitive.ItemText>
                </SelectPrimitive.Item>
              ))}
            </SelectPrimitive.Viewport>
          </SelectPrimitive.Content>
        </SelectPrimitive.Portal>
      </SelectPrimitive.Root>
    </div>
  )
}
