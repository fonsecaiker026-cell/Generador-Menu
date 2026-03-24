import React, { createContext, useContext, useState, useCallback } from 'react'
import { CheckCircle, AlertCircle, AlertTriangle, Info, X } from 'lucide-react'
import type { Toast, ToastType } from '../types'

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void
}

const ToastContext = createContext<ToastContextValue>({ showToast: () => {} })

export function useToast() {
  return useContext(ToastContext)
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  const icons: Record<ToastType, React.ReactNode> = {
    success: <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0" />,
    error: <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />,
    warning: <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />,
    info: <Info className="w-4 h-4 text-blue-600 flex-shrink-0" />,
  }

  const styles: Record<ToastType, string> = {
    success: 'border-green-200 bg-green-50',
    error: 'border-red-200 bg-red-50',
    warning: 'border-amber-200 bg-amber-50',
    info: 'border-blue-200 bg-blue-50',
  }

  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 rounded-lg border shadow-elevated animate-slide-up max-w-sm ${styles[toast.type]}`}
    >
      {icons[toast.type]}
      <p className="text-sm text-warm-900 flex-1">{toast.message}</p>
      <button
        onClick={onClose}
        className="text-warm-400 hover:text-warm-700 transition-colors flex-shrink-0 mt-0.5"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const showToast = useCallback((message: string, type: ToastType = 'info') => {
    const id = Math.random().toString(36).slice(2)
    setToasts((prev) => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4500)
  }, [])

  const removeToast = (id: string) => setToasts((prev) => prev.filter((t) => t.id !== id))

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-6 right-6 flex flex-col gap-2 z-50">
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onClose={() => removeToast(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}
