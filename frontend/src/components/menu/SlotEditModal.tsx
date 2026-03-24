import { useState, useEffect, useRef } from 'react'
import { Search, X, Pin, Trash2, Save, Star } from 'lucide-react'
import { Modal } from '../ui/Modal'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import type { MenuRow, Dish } from '../../types'
import { SLOT_LABELS, PROTEIN_LABELS, PROTEIN_DOT, FIXED_SLOTS, COURSE_GROUP_LABELS } from './constants'
import { fetchDishesBySlot } from '../../api/dishes'
import { clsx } from 'clsx'

function priorityTagForDate(menuDate: string, slot?: string): string | null {
  if (slot === 'enchiladas') return null
  const [y, m, d] = menuDate.split('-').map(Number)
  const wd = new Date(y, m - 1, d).getDay() // 0=Sun,1=Mon...5=Fri,6=Sat
  if (wd === 5) return 'only_fri'
  if (wd === 6) return 'only_sat'
  return null
}

function isDishPriority(dish: Dish, priorityTag: string | null): boolean {
  return !!priorityTag && (dish.tags ?? []).includes(priorityTag)
}

interface SlotEditModalProps {
  row: MenuRow | null
  weekStart: string
  weekRows: MenuRow[]
  onClose: () => void
  onApply: (menuDate: string, slot: string, forcedDishId: number) => Promise<void>
  onRemoveOverride: (menuDate: string, slot: string) => Promise<void>
}

function parseLocalYMD(ymd: string): Date {
  const [y, m, d] = ymd.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function startOfLocalDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}

function formatLastUsed(last_used: string | null | undefined): { label: string; color: string } {
  if (!last_used) return { label: 'Nunca usado', color: 'text-blue-500 font-medium' }

  const today = startOfLocalDay(new Date())
  const used = startOfLocalDay(parseLocalYMD(last_used))
  const msPerDay = 1000 * 60 * 60 * 24
  const days = Math.max(0, Math.floor((today.getTime() - used.getTime()) / msPerDay))

  if (days <= 7)  return { label: `hace ${days}d`, color: 'text-red-500 font-medium' }
  if (days <= 21) return { label: `hace ${days}d`, color: 'text-amber-500' }
  if (days <= 60) return { label: `hace ${days}d`, color: 'text-warm-500' }
  return { label: `hace ${days}d`, color: 'text-warm-400' }
}

function formatCourseGroupLabel(courseGroup: string): string {
  return COURSE_GROUP_LABELS[courseGroup] ?? courseGroup.replace(/_/g, ' ')
}
export function SlotEditModal({ row, weekStart, weekRows, onClose, onApply, onRemoveOverride }: SlotEditModalProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [allDishes, setAllDishes] = useState<Dish[]>([])
  const [slotDishes, setSlotDishes] = useState<Dish[]>([]) // all slot dishes incl. taken (for last_used lookup)
  const [filtered, setFiltered] = useState<Dish[]>([])
  const [selectedDish, setSelectedDish] = useState<Dish | null>(null)
  const [applying, setApplying] = useState(false)
  const [removing, setRemoving] = useState(false)
  const [loading, setLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // Dish IDs already used anywhere in this week (including current slot)
  const takenIds = new Set(weekRows.map((r) => r.dish_id))

  const priorityTag = row ? priorityTagForDate(row.menu_date, row.slot) : null

  useEffect(() => {
    if (!row) return
    setLoading(true)
    setSearchQuery('')
    setSelectedDish(null)
    fetchDishesBySlot(row.slot, row.menu_date, row.menu_date, row.slot).then((dishes) => {
      setSlotDishes(dishes)
      // Exclude dishes already used in the current week (including current dish)
      const available = dishes.filter((d) => !takenIds.has(d.id))
      // Sort: priority dishes for this day first (only_fri on Fri, only_sat on Sat)
      const tag = priorityTagForDate(row.menu_date, row.slot)
      if (tag) {
        available.sort((a, b) => {
          const pa = isDishPriority(a, tag) ? 0 : 1
          const pb = isDishPriority(b, tag) ? 0 : 1
          return pa - pb
          // within each group the API order (last_used oldest-first) is preserved
        })
      }
      setAllDishes(available)
      setLoading(false)
    })
    setTimeout(() => inputRef.current?.focus(), 100)
  }, [row, weekRows])

  useEffect(() => {
    if (!searchQuery.trim()) {
      setFiltered(allDishes)
      return
    }
    const q = searchQuery.toLowerCase()
    setFiltered(
      allDishes.filter(
        (d) =>
          d.name.toLowerCase().includes(q) ||
          formatCourseGroupLabel(d.course_group).toLowerCase().includes(q) ||
          d.protein.toLowerCase().includes(q),
      ),
    )
  }, [searchQuery, allDishes])

  const handleApply = async () => {
    if (!row || !selectedDish) return
    setApplying(true)
    try {
      await onApply(row.menu_date, row.slot, selectedDish.id)
      onClose()
    } finally {
      setApplying(false)
    }
  }

  const handleRemove = async () => {
    if (!row) return
    setRemoving(true)
    try {
      await onRemoveOverride(row.menu_date, row.slot)
      onClose()
    } finally {
      setRemoving(false)
    }
  }

  if (!row) return null

  const slotLabel = SLOT_LABELS[row.slot] ?? row.slot
  const isFixed = FIXED_SLOTS.has(row.slot)

  // Current dish - look in slotDishes (includes taken dishes) for last_used
  const currentDishData = slotDishes.find((d) => d.id === row.dish_id)
  const currentLastUsed = formatLastUsed(currentDishData?.last_used)

  return (
    <Modal
      open={!!row}
      onClose={onClose}
      size="lg"
      title={
        <span className="flex items-center gap-2">
          <span className="text-warm-400 text-sm font-normal">{slotLabel}</span>
          <span className="text-warm-300">·</span>
          <span>{row.menu_date}</span>
        </span>
      }
      description="Todos los platillos disponibles, ordenados por los que llevan más tiempo sin salir."
      footer={
        <>
          {row.is_forced && !isFixed && (
            <Button
              variant="ghost"
              size="sm"
              icon={<Trash2 className="w-3.5 h-3.5" />}
              loading={removing}
              onClick={handleRemove}
              className="mr-auto text-red-600 hover:bg-red-50"
            >
              Quitar override
            </Button>
          )}
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            icon={<Save className="w-4 h-4" />}
            onClick={handleApply}
            loading={applying}
            disabled={!selectedDish}
          >
            Aplicar ahora
          </Button>
        </>
      }
    >
      {/* Current dish */}
      <div className="mb-5">
        <p className="text-xs font-medium text-warm-500 uppercase tracking-wide mb-2">Platillo actual</p>
        <div className="flex items-center gap-3 px-3 py-3 bg-warm-50 rounded-lg border border-warm-200">
          <div className={clsx('w-2 h-2 rounded-full flex-shrink-0', PROTEIN_DOT[row.protein])} />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-warm-900">{row.dish_name}</p>
            <p className="text-xs text-warm-500">{PROTEIN_LABELS[row.protein]}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {!loading && (
              <span className={clsx('text-xs', currentLastUsed.color)}>
                {currentLastUsed.label}
              </span>
            )}
            {row.is_forced && <Badge variant="amber">Forzado</Badge>}
            {row.was_exception && <Badge variant="warning">Excepción</Badge>}
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="mb-3">
        <p className="text-xs font-medium text-warm-500 uppercase tracking-wide mb-2">
          Reemplazar con
          {!loading && (
            <span className="ml-2 font-normal normal-case text-warm-400">
              ({filtered.length}{filtered.length !== allDishes.length ? ` de ${allDishes.length}` : ''} disponibles)
            </span>
          )}
        </p>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-warm-400" />
          <input
            ref={inputRef}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Buscar por nombre, grupo o proteína..."
            className="w-full h-9 pl-9 pr-4 text-sm bg-white border border-warm-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent text-warm-900 placeholder:text-warm-400"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-warm-400 hover:text-warm-700"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Dish list */}
      <div className="border border-warm-200 rounded-lg overflow-hidden">
        <div className="max-h-80 overflow-y-auto">
          {loading && (
            <div className="px-4 py-6 text-center text-sm text-warm-400">Cargando platillos...</div>
          )}
          {!loading && filtered.length === 0 && (
            <div className="px-4 py-6 text-center text-sm text-warm-400">
              {searchQuery ? `Sin resultados para "${searchQuery}"` : 'No hay platillos disponibles.'}
            </div>
          )}
          {!loading && (() => {
            const priorityCount = priorityTag
              ? filtered.filter(d => isDishPriority(d, priorityTag)).length
              : 0
            return filtered.map((dish, idx) => {
              const isSelected = selectedDish?.id === dish.id
              const isCurrent = dish.id === row.dish_id
              const isPriority = isDishPriority(dish, priorityTag)
              const { label: lastUsedLabel, color: lastUsedColor } = formatLastUsed(dish.last_used)
              return (
                <div key={dish.id}>
                  {/* Section headers */}
                  {idx === 0 && priorityCount > 0 && (
                    <div className="px-3 py-1.5 bg-amber-50 border-b border-amber-100 flex items-center gap-1.5">
                      <Star className="w-3 h-3 text-amber-500 fill-amber-400" />
                      <p className="text-[10px] font-semibold text-amber-700 uppercase tracking-wide">
                        Prioridad {priorityTag === 'only_fri' ? 'viernes' : 'sábado'}
                      </p>
                    </div>
                  )}
                  {idx === priorityCount && priorityCount > 0 && (
                    <div className="px-3 py-1.5 bg-warm-50 border-b border-warm-200">
                      <p className="text-[10px] font-semibold text-warm-400 uppercase tracking-wide">Otros disponibles</p>
                    </div>
                  )}
                  <button
                    onClick={() => setSelectedDish(isSelected ? null : dish)}
                    className={clsx(
                      'w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors border-b border-warm-100 last:border-0',
                      isSelected
                        ? 'bg-brand-50 border-brand-100'
                        : isCurrent
                        ? 'bg-warm-50'
                        : isPriority
                        ? 'hover:bg-amber-50'
                        : 'hover:bg-warm-50',
                    )}
                  >
                    <div className={clsx('w-2 h-2 rounded-full flex-shrink-0', PROTEIN_DOT[dish.protein])} />
                    <div className="flex-1 min-w-0">
                      <p className={clsx(
                        'text-sm leading-tight',
                        isSelected ? 'text-brand-800 font-semibold' : isCurrent ? 'text-warm-600' : 'text-warm-800 font-medium',
                      )}>
                        {dish.name}
                        {isCurrent && <span className="ml-2 text-[10px] text-warm-400 font-normal">(actual)</span>}
                      </p>
                      <p className="text-[11px] text-warm-400 mt-0.5">
                        {formatCourseGroupLabel(dish.course_group)} · {PROTEIN_LABELS[dish.protein]}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {isPriority && !isSelected && (
                        <Star className="w-3 h-3 text-amber-500 fill-amber-400 flex-shrink-0" />
                      )}
                      <span className={clsx('text-[11px]', lastUsedColor)}>
                        {lastUsedLabel}
                      </span>
                      {isSelected && <Pin className="w-3.5 h-3.5 text-brand-600" />}
                    </div>
                  </button>
                </div>
              )
            })
          })()}
        </div>
      </div>

      {/* Selected preview */}
      {selectedDish && (
        <div className="mt-4 flex items-center gap-2 px-3 py-2 bg-brand-50 border border-brand-200 rounded-lg">
          <Pin className="w-3.5 h-3.5 text-brand-600 flex-shrink-0" />
          <p className="text-sm text-brand-800">
            <strong>{selectedDish.name}</strong> se forzará en este slot.
          </p>
        </div>
      )}
    </Modal>
  )
}


