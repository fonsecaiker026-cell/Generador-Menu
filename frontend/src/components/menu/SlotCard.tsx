import { Lock, AlertTriangle, Pencil, Pin } from 'lucide-react'
import { clsx } from 'clsx'
import type { MenuRow } from '../../types'
import { SLOT_LABELS, PROTEIN_DOT, FIXED_SLOTS } from './constants'

interface SlotCardProps {
  row: MenuRow
  onEdit?: (row: MenuRow) => void
  isFinalized?: boolean
}

export function SlotCard({ row, onEdit, isFinalized }: SlotCardProps) {
  const isFixed = FIXED_SLOTS.has(row.slot)
  const isEditable = !isFixed && !isFinalized
  const label = SLOT_LABELS[row.slot] ?? row.slot

  const handleClick = () => {
    if (isEditable && onEdit) onEdit(row)
  }

  const displayDishName =
    row.slot === 'arroz'
      ? 'Arroz al gusto (platano, huevo o mole)'
      : row.slot === 'nuggets'
      ? 'Nuggets de pollo con papas'
      : row.slot === 'pancita'
      ? 'Pancita de res en caldo'
      : row.slot === 'paella'
      ? 'Paella'
      : row.dish_name

  return (
    <div
      onClick={handleClick}
      className={clsx(
        'group relative flex items-start gap-2.5 px-3 py-2.5 rounded-lg border transition-all duration-150',
        // Base styles
        isFixed && 'bg-warm-50 border-warm-200 cursor-default',
        !isFixed && row.is_forced && !isFinalized && 'bg-amber-50 border-amber-200 cursor-pointer hover:border-amber-400 hover:shadow-soft',
        !isFixed && row.was_exception && !row.is_forced && 'bg-orange-50 border-orange-200 cursor-pointer hover:border-orange-400 hover:shadow-soft',
        !isFixed && !row.is_forced && !row.was_exception && !isFinalized && 'bg-white border-warm-200 cursor-pointer hover:border-warm-300 hover:shadow-soft',
        !isFixed && !row.is_forced && !row.was_exception && isFinalized && 'bg-white border-warm-200 cursor-default',
      )}
    >
      {/* Protein dot */}
      <div className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5', PROTEIN_DOT[row.protein] ?? 'bg-warm-300')} />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-1">
          <span className={clsx('text-[11px] font-medium uppercase tracking-wide leading-none',
            isFixed ? 'text-warm-400' : 'text-warm-500',
          )}>
            {label}
          </span>
          {/* Status icons */}
          <div className="flex items-center gap-1 flex-shrink-0">
            {isFixed && <Lock className="w-2.5 h-2.5 text-warm-300" />}
            {row.is_forced && !isFixed && <Pin className="w-2.5 h-2.5 text-amber-500" />}
            {row.was_exception && <AlertTriangle className="w-2.5 h-2.5 text-orange-500" />}
          </div>
        </div>
        <p className={clsx('text-sm leading-snug mt-0.5 text-balance',
          isFixed ? 'text-warm-500 font-normal' : 'text-warm-900 font-medium',
        )}>
          {displayDishName}
        </p>
        {row.was_exception && row.exception_reason && (
          <p className="text-[10px] text-orange-600 mt-1 leading-tight">
            ⚡ {row.exception_reason.split(':')[0]}
          </p>
        )}
      </div>

      {/* Edit hint on hover */}
      {isEditable && (
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Pencil className="w-3 h-3 text-warm-400" />
        </div>
      )}
    </div>
  )
}
