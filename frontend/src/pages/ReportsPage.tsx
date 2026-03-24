import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Activity, AlertTriangle, Clock, Search, TrendingDown, TrendingUp } from 'lucide-react'
import { Badge } from '../components/ui/Badge'
import { Select } from '../components/ui/Select'
import { useToast } from '../context/ToastContext'
import { fetchCatalogHealth } from '../api/reports'
import type { CatalogHealth, CatalogHealthDish } from '../types'
import { clsx } from 'clsx'

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center h-48 text-warm-400">
      <div className="text-center">
        <div className="w-6 h-6 border-2 border-brand-200 border-t-brand-600 rounded-full animate-spin mx-auto mb-2" />
        <p className="text-sm">Cargando…</p>
      </div>
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-48">
      <div className="text-center">
        <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto mb-2" />
        <p className="text-sm text-warm-500">{message}</p>
      </div>
    </div>
  )
}

function DishList({
  title,
  icon,
  items,
  variant,
  emptyMessage,
  onGoToCatalog,
  rightText,
}: {
  title: string
  icon: ReactNode
  items: CatalogHealthDish[]
  variant: 'info' | 'warning' | 'error'
  emptyMessage: string
  onGoToCatalog?: (query: string) => void
  rightText?: (d: CatalogHealthDish) => string
}) {
  const styles =
    variant === 'info'
      ? {
          box: 'bg-blue-50 border-blue-100 hover:bg-blue-100',
          text: 'text-blue-900',
          meta: 'text-blue-600',
        }
      : variant === 'warning'
        ? {
            box: 'bg-amber-50 border-amber-100 hover:bg-amber-100',
            text: 'text-amber-900',
            meta: 'text-amber-600',
          }
        : {
            box: 'bg-red-50 border-red-100 hover:bg-red-100',
            text: 'text-red-900',
            meta: 'text-red-600',
          }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-warm-800 flex items-center gap-2">
        {icon}
        {title} ({items.length})
      </h3>
      {items.length === 0 ? (
        <div className="border border-warm-200 rounded-lg p-3 text-xs text-warm-500 bg-white">{emptyMessage}</div>
      ) : (
        <div className="space-y-1 max-h-[480px] overflow-y-auto pr-1">
          {items.map((d) => (
            <button
              key={d.id}
              onClick={() => onGoToCatalog?.(d.name)}
              className={clsx(
                'w-full flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors text-left',
                styles.box,
              )}
              title="Ver en catálogo"
            >
              <span className={clsx('text-xs font-medium flex-1', styles.text)}>{d.name}</span>
              {rightText && <span className={clsx('text-[10px] font-bold', styles.meta)}>{rightText(d)}</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export function ReportsPage({ onGoToCatalog }: { onGoToCatalog?: (query: string) => void }) {
  const [data, setData] = useState<CatalogHealth | null>(null)
  const [loading, setLoading] = useState(true)
  const [sinceDays, setSinceDays] = useState('60')
  const [query, setQuery] = useState('')
  const { showToast } = useToast()

  const load = (days: number) => {
    setLoading(true)
    fetchCatalogHealth(days)
      .then(setData)
      .catch(() => showToast('Error al cargar salud del catálogo', 'error'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load(60)
  }, [])

  const q = query.trim().toLowerCase()
  const neverUsed = useMemo(
    () => (data?.never_used ?? []).filter((d) => d.name.toLowerCase().includes(q)),
    [data, q],
  )
  const dormant = useMemo(
    () => (data?.dormant ?? []).filter((d) => d.name.toLowerCase().includes(q)),
    [data, q],
  )
  const overused = useMemo(
    () => (data?.overused ?? []).filter((d) => d.name.toLowerCase().includes(q)),
    [data, q],
  )

  if (loading) return <LoadingSpinner />
  if (!data) return <ErrorState message="Error cargando datos." />

  const dormant90 = dormant.filter((d) => Number(d.days_ago ?? 0) >= 90).length
  const heavyOverused = overused.filter((d) => Number(d.uses ?? 0) >= 20).length

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <header className="flex-shrink-0 bg-white border-b border-warm-200 px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold text-warm-900">Salud de Catálogo</h1>
            <p className="text-sm text-warm-500 mt-0.5">
              Enfoque en rotación real: dormidos, nunca usados y sobreusados
            </p>
          </div>

          <div className="flex items-end gap-3">
            <Select
              label="Ventana dormidos"
              value={sinceDays}
              onChange={(v) => {
                setSinceDays(v)
                load(parseInt(v))
              }}
              options={[
                { value: '30', label: '30 días' },
                { value: '45', label: '45 días' },
                { value: '60', label: '60 días' },
                { value: '90', label: '90 días' },
              ]}
            />
            <div>
              <label className="block text-xs text-warm-500 mb-1">Buscar platillo</label>
              <div className="flex items-center gap-2 bg-white border border-warm-300 rounded-lg px-2 h-10 min-w-[260px]">
                <Search className="w-4 h-4 text-warm-400" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ej. milanesa, crema, molcajete..."
                  className="w-full text-sm bg-transparent outline-none text-warm-800 placeholder:text-warm-400"
                />
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="grid grid-cols-4 gap-3">
          {[
            {
              label: 'Total activos',
              value: data.total_active,
              icon: <Activity className="w-4 h-4 text-green-600" />,
              color: 'text-green-700',
            },
            {
              label: 'Nunca usados',
              value: neverUsed.length,
              icon: <Clock className="w-4 h-4 text-blue-500" />,
              color: 'text-blue-700',
            },
            {
              label: 'Dormidos',
              value: dormant.length,
              icon: <TrendingDown className="w-4 h-4 text-amber-500" />,
              color: 'text-amber-700',
            },
            {
              label: 'Sobreusados',
              value: overused.length,
              icon: <TrendingUp className="w-4 h-4 text-red-500" />,
              color: 'text-red-700',
            },
          ].map((s) => (
            <div key={s.label} className="bg-white border border-warm-200 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                {s.icon}
                <span className="text-xs text-warm-500">{s.label}</span>
              </div>
              <p className={clsx('text-2xl font-bold', s.color)}>{s.value}</p>
            </div>
          ))}
        </div>

        <div className="bg-white border border-warm-200 rounded-lg p-4">
          <h2 className="text-sm font-semibold text-warm-800 mb-2">Acciones sugeridas</h2>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant={dormant90 > 0 ? 'warning' : 'default'} size="sm">
              {dormant90} dormidos de 90+ días
            </Badge>
            <Badge variant={heavyOverused > 0 ? 'error' : 'default'} size="sm">
              {heavyOverused} sobreusados de 20+ usos
            </Badge>
            <Badge variant={neverUsed.length > 0 ? 'info' : 'default'} size="sm">
              {neverUsed.length} candidatos para primera salida
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-6">
          <DishList
            title="Nunca usados"
            icon={<Clock className="w-4 h-4 text-blue-500" />}
            items={neverUsed}
            variant="info"
            emptyMessage="No hay resultados con este filtro."
            onGoToCatalog={onGoToCatalog}
          />
          <DishList
            title="Dormidos"
            icon={<TrendingDown className="w-4 h-4 text-amber-500" />}
            items={dormant}
            variant="warning"
            emptyMessage="No hay resultados con este filtro."
            onGoToCatalog={onGoToCatalog}
            rightText={(d) => `${d.days_ago ?? 0}d`}
          />
          <DishList
            title="Sobreusados"
            icon={<TrendingUp className="w-4 h-4 text-red-500" />}
            items={overused}
            variant="error"
            emptyMessage="No hay resultados con este filtro."
            onGoToCatalog={onGoToCatalog}
            rightText={(d) => `${d.uses ?? 0} usos`}
          />
        </div>
      </div>
    </div>
  )
}
