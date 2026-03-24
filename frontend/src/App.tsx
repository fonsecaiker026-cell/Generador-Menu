import { useState } from 'react'
import { Layout } from './components/layout/Layout'
import { MenuPage } from './pages/MenuPage'
import { CatalogPage } from './pages/CatalogPage'
import { ReportsPage } from './pages/ReportsPage'
import { ToastProvider } from './context/ToastContext'
import type { Page } from './types'

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>('menu')
  const [catalogQuery, setCatalogQuery] = useState('')

  const goToCatalog = (query: string = '') => {
    setCatalogQuery(query)
    setCurrentPage('catalog')
  }

  const renderPage = () => {
    switch (currentPage) {
      case 'menu':
        return <MenuPage />
      case 'catalog':
        return <CatalogPage initialQuery={catalogQuery} onQueryConsumed={() => setCatalogQuery('')} />
      case 'reports':
        return <ReportsPage onGoToCatalog={goToCatalog} />
    }
  }

  return (
    <ToastProvider>
      <Layout currentPage={currentPage} onNavigate={setCurrentPage}>
        {renderPage()}
      </Layout>
    </ToastProvider>
  )
}
