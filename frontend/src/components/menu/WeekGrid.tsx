import { DayColumn } from './DayColumn'
import type { MenuRow, WeekMeta } from '../../types'
import { format, addDays, startOfWeek } from 'date-fns'

interface WeekGridProps {
  weekStart: string
  rows: MenuRow[]
  week: WeekMeta | null
  onEditSlot: (row: MenuRow) => void
  onDeleteDay: (menuDate: string) => void
  onRegenerateDay: (menuDate: string) => void
  closedDates?: string[]
}

function getWeekDays(weekStart: string): string[] {
  const monday = new Date(weekStart + 'T12:00:00')
  return Array.from({ length: 6 }, (_, i) => format(addDays(monday, i), 'yyyy-MM-dd'))
}

function getTodayStr(): string {
  return format(new Date(), 'yyyy-MM-dd')
}

export function WeekGrid({ weekStart, rows, week, onEditSlot, onDeleteDay, onRegenerateDay, closedDates = [] }: WeekGridProps) {
  const days = getWeekDays(weekStart)
  const today = getTodayStr()
  const isFinalized = week?.finalized ?? false
  const closedSet = new Set(closedDates)

  // Group rows by date
  const rowsByDate = new Map<string, MenuRow[]>()
  for (const row of rows) {
    const existing = rowsByDate.get(row.menu_date) ?? []
    existing.push(row)
    rowsByDate.set(row.menu_date, existing)
  }

  return (
    <div className="flex-1 overflow-x-auto overflow-y-hidden">
      <div className="flex h-full min-w-max">
        {days.map((dateStr) => (
          <DayColumn
            key={dateStr}
            date={dateStr}
            rows={rowsByDate.get(dateStr) ?? []}
            onEdit={onEditSlot}
            onDeleteDay={onDeleteDay}
            onRegenerateDay={onRegenerateDay}
            isFinalized={isFinalized}
            isToday={dateStr === today}
            isClosed={closedSet.has(dateStr)}
          />
        ))}
      </div>
    </div>
  )
}
