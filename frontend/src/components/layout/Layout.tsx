import { Sidebar } from './Sidebar'
import type { Page } from '../../types'

interface LayoutProps {
  currentPage: Page
  onNavigate: (page: Page) => void
  children: React.ReactNode
}

export function Layout({ currentPage, onNavigate, children }: LayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-warm-50">
      <Sidebar currentPage={currentPage} onNavigate={onNavigate} />
      <main className="flex-1 overflow-hidden flex flex-col min-w-0">
        {children}
      </main>
    </div>
  )
}
