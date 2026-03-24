import { clsx } from 'clsx'
import { RefreshCw, Trash2 } from 'lucide-react'
import type { MenuRow } from '../../types'
import { SlotCard } from './SlotCard'
import { SECTION_SLOTS, ALL_SECTION_NAMES } from './constants'

const SECTION_LABELS: Record<string, string> = {
  Entradas: 'Entradas',
  'Sopas & Cremas': 'Sopas & Cremas',
  'Arroz & Ensalada': 'Arroz & Ensalada',
  'Platos Fuertes': 'Platos Fuertes',
  'Especiales & Complementos': 'Especiales',
}

const WEEKDAY_NAMES = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado']

interface DayColumnProps {
  date: string
  rows: MenuRow[]
  onEdit: (row: MenuRow) => void
  onDeleteDay: (menuDate: string) => void
  onRegenerateDay: (menuDate: string) => void
  isFinalized: boolean
  isToday?: boolean
  isClosed?: boolean
}

function parseLocalDate(s: string): Date {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function DayColumn({
  date,
  rows,
  onEdit,
  onDeleteDay,
  onRegenerateDay,
  isFinalized,
  isToday,
  isClosed = false,
}: DayColumnProps) {
  const d = parseLocalDate(date)
  const weekdayIndex = (d.getDay() + 6) % 7
  const weekdayName = WEEKDAY_NAMES[weekdayIndex] ?? d.toLocaleDateString('es-MX', { weekday: 'long' })
  const dayNum = d.getDate()
  const monthShort = d.toLocaleDateString('es-MX', { month: 'short' })
  const isSat = weekdayIndex === 5

  const sectionSlots = isSat
    ? {
        ...SECTION_SLOTS,
        'Sopas & Cremas': ['sopa', 'crema', 'pancita', 'sopa_pollo'],
        'Arroz & Ensalada': ['pasta', 'ensalada_A', 'ensalada_B', 'ensalada_C'],
      }
    : SECTION_SLOTS

  const rowsBySlot = new Map(rows.map((r) => [r.slot, r]))

  const sections = ALL_SECTION_NAMES.map((sectionName) => {
    const slotKeys = sectionSlots[sectionName]
    const sectionRows = slotKeys
      .map((slot) => rowsBySlot.get(slot))
      .filter(Boolean) as MenuRow[]
    return { name: sectionName, rows: sectionRows }
  }).filter((s) => s.rows.length > 0)

  const exceptionCount = rows.filter((r) => r.was_exception).length
  const forcedCount = rows.filter((r) => r.is_forced && !['entrada_comal', 'arroz', 'chamorro', 'paella', 'nuggets', 'pancita'].includes(r.slot)).length

  return (
    <div
      className={clsx(
        'flex flex-col flex-shrink-0 w-52 bg-white border-r border-warm-200 last:border-r-0 overflow-hidden',
        isSat && 'bg-warm-50/50',
      )}
    >
      <div
        className={clsx(
          'px-3 py-3 border-b border-warm-200 flex-shrink-0',
          isToday ? 'bg-brand-700' : isSat ? 'bg-warm-100' : 'bg-white',
        )}
      >
        <div className="flex items-center justify-between">
          <div>
            <p
              className={clsx(
                'text-xs font-semibold uppercase tracking-widest leading-none',
                isToday ? 'text-brand-100' : 'text-warm-500',
              )}
            >
              {weekdayName}
            </p>
            <p
              className={clsx(
                'text-xl font-bold leading-tight mt-0.5',
                isToday ? 'text-white' : 'text-warm-900',
              )}
            >
              {dayNum}
              <span className={clsx('text-sm font-normal ml-1', isToday ? 'text-brand-200' : 'text-warm-400')}>
                {monthShort}
              </span>
            </p>
          </div>

          <div className="flex flex-col gap-1 items-end">
            {!isFinalized && !isClosed && rows.length > 0 && (
              <>
                <button
                  onClick={() => onRegenerateDay(date)}
                  className={clsx(
                    'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium border transition-colors',
                    isToday
                      ? 'bg-white/10 border-white/20 text-white hover:bg-white/20'
                      : 'bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100',
                  )}
                  title="Regenerar solo este dia"
                >
                  <RefreshCw className="w-3 h-3" />
                  Regenerar dia
                </button>
                <button
                  onClick={() => onDeleteDay(date)}
                  className={clsx(
                    'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium border transition-colors',
                    isToday
                      ? 'bg-white/10 border-white/20 text-white hover:bg-white/20'
                      : 'bg-red-50 border-red-200 text-red-700 hover:bg-red-100',
                  )}
                  title="Cerrar dia por festivo o puente"
                >
                  <Trash2 className="w-3 h-3" />
                  Cerrar dia
                </button>
              </>
            )}
            {isClosed && (
              <span className="inline-flex items-center px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded text-[10px] font-medium text-slate-600">
                Cerrado
              </span>
            )}
            {forcedCount > 0 && (
              <span className="inline-flex items-center px-1.5 py-0.5 bg-amber-100 border border-amber-200 rounded text-[10px] font-medium text-amber-700">
                {forcedCount} forzado{forcedCount > 1 ? 's' : ''}
              </span>
            )}
            {exceptionCount > 0 && (
              <span className="inline-flex items-center px-1.5 py-0.5 bg-orange-100 border border-orange-200 rounded text-[10px] font-medium text-orange-700">
                {exceptionCount} excep.
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-3">
        {rows.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-warm-300 text-xs text-center px-4">
            {isClosed ? (
              <>Dia cerrado.</>
            ) : (
              <>
                Sin platillos.
                <br />
                Genera el menu.
              </>
            )}
          </div>
        ) : (
          sections.map((section) => (
            <div key={section.name}>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-warm-400 px-1 mb-1.5">
                {SECTION_LABELS[section.name] ?? section.name}
              </p>
              <div className="space-y-1.5">
                {section.rows.map((row) => (
                  <SlotCard
                    key={row.slot}
                    row={row}
                    onEdit={onEdit}
                    isFinalized={isFinalized}
                  />
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
