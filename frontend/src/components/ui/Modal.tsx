import * as Dialog from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { clsx } from 'clsx'

interface ModalProps {
  open: boolean
  onClose: () => void
  title?: React.ReactNode
  description?: string
  children: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
  footer?: React.ReactNode
}

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
}

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  size = 'md',
  footer,
}: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 backdrop-blur-[2px] z-40 animate-fade-in" />
        <Dialog.Content
          className={clsx(
            'fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50',
            'w-[calc(100vw-2rem)] bg-white rounded-xl shadow-modal animate-scale-in',
            'flex flex-col overflow-hidden max-h-[calc(100vh-4rem)]',
            sizeClasses[size],
          )}
        >
          {/* Header */}
          {(title || description) && (
            <div className="px-6 pt-5 pb-4 border-b border-warm-200 flex-shrink-0">
              {title && (
                <Dialog.Title className="text-base font-semibold text-warm-900">
                  {title}
                </Dialog.Title>
              )}
              {description && (
                <Dialog.Description className="text-sm text-warm-500 mt-1">
                  {description}
                </Dialog.Description>
              )}
            </div>
          )}

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>

          {/* Footer */}
          {footer && (
            <div className="px-6 py-4 border-t border-warm-200 flex-shrink-0 flex items-center justify-end gap-2">
              {footer}
            </div>
          )}

          {/* Close button */}
          <Dialog.Close
            className="absolute top-4 right-4 text-warm-400 hover:text-warm-700 transition-colors rounded-lg p-1 hover:bg-warm-100"
            onClick={onClose}
          >
            <X className="w-4 h-4" />
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

interface ConfirmDialogProps {
  open: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  description: string
  confirmLabel?: string
  variant?: 'danger' | 'primary'
  loading?: boolean
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = 'Confirmar',
  variant = 'primary',
  loading = false,
}: ConfirmDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 backdrop-blur-[2px] z-40 animate-fade-in" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[calc(100vw-2rem)] max-w-md bg-white rounded-xl shadow-modal animate-scale-in p-6">
          <Dialog.Title className="text-base font-semibold text-warm-900">{title}</Dialog.Title>
          <Dialog.Description className="text-sm text-warm-600 mt-2">{description}</Dialog.Description>
          <div className="flex justify-end gap-2 mt-6">
            <button
              onClick={onClose}
              className="h-9 px-4 text-sm font-medium text-warm-700 hover:bg-warm-100 rounded-lg transition-colors border border-warm-300"
            >
              Cancelar
            </button>
            <button
              onClick={onConfirm}
              disabled={loading}
              className={clsx(
                'h-9 px-4 text-sm font-medium text-white rounded-lg transition-colors disabled:opacity-60',
                variant === 'danger' ? 'bg-red-600 hover:bg-red-700' : 'bg-brand-700 hover:bg-brand-800',
              )}
            >
              {loading ? 'Procesando…' : confirmLabel}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
