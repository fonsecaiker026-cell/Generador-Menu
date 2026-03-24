import { UtensilsCrossed, BookOpen, BarChart3 } from 'lucide-react'
import { clsx } from 'clsx'
import type { Page } from '../../types'

interface SidebarProps {
  currentPage: Page
  onNavigate: (page: Page) => void
}

const NAV_ITEMS: { id: Page; label: string; icon: React.ReactNode; description: string }[] = [
  {
    id: 'menu',
    label: 'Menú Semanal',
    icon: <UtensilsCrossed className="w-5 h-5" />,
    description: 'Genera y edita el menú',
  },
  {
    id: 'catalog',
    label: 'Catálogo',
    icon: <BookOpen className="w-5 h-5" />,
    description: 'Platillos y recetas',
  },
  {
    id: 'reports',
    label: 'Reportes',
    icon: <BarChart3 className="w-5 h-5" />,
    description: 'Calidad del menú',
  },
]

export function Sidebar({ currentPage, onNavigate }: SidebarProps) {
  return (
    <aside className="w-60 flex-shrink-0 bg-warm-950 h-screen flex flex-col">
      {/* Logo */}
      <div className="px-5 py-6 border-b border-warm-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-700 flex items-center justify-center flex-shrink-0">
            <UtensilsCrossed className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-warm-50 leading-tight">Menú</p>
            <p className="text-xs text-warm-400 leading-tight">La Tradicional Hidalgo</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = currentPage === item.id
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={clsx(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors text-left',
                isActive
                  ? 'bg-brand-700 text-white'
                  : 'text-warm-400 hover:text-warm-100 hover:bg-warm-800',
              )}
            >
              <span className={clsx('flex-shrink-0', isActive ? 'text-white' : 'text-warm-500')}>
                {item.icon}
              </span>
              <div className="min-w-0">
                <p className="text-sm font-medium leading-tight">{item.label}</p>
                <p className={clsx('text-[11px] leading-tight mt-0.5', isActive ? 'text-brand-200' : 'text-warm-600')}>
                  {item.description}
                </p>
              </div>
            </button>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-warm-800">
        <p className="text-[11px] text-warm-600 leading-tight">v0.1.0</p>
        <p className="text-[10px] text-warm-700 mt-0.5">L–S · Rotación 20 días</p>
      </div>
    </aside>
  )
}
