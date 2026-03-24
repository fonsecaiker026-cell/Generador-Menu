import { apiClient, withFallback, delay } from './client'
import {
  getMockWeek,
  setMockWeek,
  MOCK_MENU_ROWS,
  MOCK_WEEK_META,
  MOCK_DISHES,
} from '../mocks/data'
import type { WeekData, Override, MenuRow } from '../types'
import { format, addDays, startOfWeek } from 'date-fns'
import { es } from 'date-fns/locale'

function ensureMonday(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00')
  const monday = startOfWeek(d, { weekStartsOn: 1 })
  return format(monday, 'yyyy-MM-dd')
}

function generateId(): number {
  return Date.now()
}

// Build a fresh set of rows for any week (using rotating mock dishes)
function buildWeekRows(weekStart: string): MenuRow[] {
  const base = MOCK_MENU_ROWS
  const targetMonday = new Date(weekStart + 'T12:00:00')
  const sourceMonday = new Date('2026-03-09T12:00:00')
  const diffDays = Math.round((targetMonday.getTime() - sourceMonday.getTime()) / 86400000)

  return base.map((r) => {
    const sourceDate = new Date(r.menu_date + 'T12:00:00')
    const newDate = addDays(sourceDate, diffDays)
    return { ...r, menu_date: format(newDate, 'yyyy-MM-dd') }
  })
}

export interface WeekSummary {
  week_start_date: string
  finalized: boolean
}

export async function fetchWeekList(): Promise<WeekSummary[]> {
  return withFallback(
    async () => {
      const { data } = await apiClient.get<WeekSummary[]>('/weeks')
      return data
    },
    async () => {
      await delay(100)
      return []
    },
  )
}

export async function fetchWeek(weekStart: string): Promise<WeekData> {
  const monday = ensureMonday(weekStart)
  return withFallback(
    async () => {
      const { data } = await apiClient.get<WeekData>(`/weeks/${monday}`)
      return data
    },
    async () => {
      await delay(200)
      return getMockWeek(monday)
    },
  )
}

export async function generateWeek(weekStart: string): Promise<WeekData> {
  const monday = ensureMonday(weekStart)
  return withFallback(
    async () => {
      await apiClient.post(`/weeks/${monday}/generate`)
      const { data } = await apiClient.get<WeekData>(`/weeks/${monday}`)
      return data
    },
    async () => {
      await delay(700)
      const rows = buildWeekRows(monday)
      const week = {
        id: generateId(),
        week_start_date: monday,
        generated_at: new Date().toISOString(),
        finalized: false,
        notes: null,
      }
      const data: WeekData = { week, rows }
      setMockWeek(monday, data)
      return data
    },
  )
}

export async function regenerateWeek(weekStart: string): Promise<WeekData> {
  const monday = ensureMonday(weekStart)
  return withFallback(
    async () => {
      await apiClient.post(`/weeks/${monday}/regenerate`)
      const { data } = await apiClient.get<WeekData>(`/weeks/${monday}`)
      return data
    },
    async () => {
      await delay(800)
      const current = getMockWeek(monday)
      // Simulate some dish changes
      const rows = buildWeekRows(monday).map((r) => {
        if (Math.random() < 0.3 && !r.is_forced) {
          const sameCourse = MOCK_DISHES.filter(
            (d) => d.course_group === r.course_group && d.active && d.id !== r.dish_id,
          )
          if (sameCourse.length > 0) {
            const alt = sameCourse[Math.floor(Math.random() * sameCourse.length)]
            return {
              ...r,
              dish_id: alt.id,
              dish_name: alt.name,
              protein: alt.protein,
              style_tag: alt.style_tag,
              was_exception: false,
              exception_reason: null,
            }
          }
        }
        return r
      })
      const data: WeekData = {
        week: {
          ...(current.week ?? {
            id: generateId(),
            week_start_date: monday,
            finalized: false,
            notes: null,
          }),
          generated_at: new Date().toISOString(),
        } as WeekData['week'],
        rows,
      }
      setMockWeek(monday, data as WeekData)
      return data as WeekData
    },
  )
}

export async function finalizeWeek(
  weekStart: string,
  finalized: boolean,
  notes?: string,
): Promise<string[]> {
  const monday = ensureMonday(weekStart)
  return withFallback(
    async () => {
      const { data } = await apiClient.post<{ ok: boolean; warnings: string[] }>(
        `/weeks/${monday}/finalize`,
        { finalized, notes },
      )
      return data.warnings ?? []
    },
    async () => {
      await delay(300)
      const current = getMockWeek(monday)
      if (current.week) {
        setMockWeek(monday, {
          ...current,
          week: { ...current.week, finalized, notes: notes ?? current.week.notes },
        })
      }
      return []
    },
  )
}

export async function setOverride(override: Override): Promise<void> {
  return withFallback(
    async () => {
      await apiClient.post('/overrides', override)
    },
    async () => {
      await delay(200)
      // Stored in mock — apply_override_now will handle the visual update
    },
  )
}

export async function removeOverride(menuDate: string, slot: string, weekStart: string): Promise<WeekData> {
  const monday = ensureMonday(weekStart)
  return withFallback(
    async () => {
      // 1. Delete the override
      await apiClient.delete(`/overrides/${menuDate}/${slot}`)
      // 2. Recompute slot (algorithm picks freely again, no forced dish)
      await apiClient.post(`/overrides/${menuDate}/${slot}/apply?week_start=${monday}`)
      // 3. Fetch updated week
      const { data } = await apiClient.get<WeekData>(`/weeks/${monday}`)
      return data
    },
    async () => {
      await delay(300)
      return getMockWeek(monday)
    },
  )
}

export interface ApplyOverrideResult {
  weekData: WeekData
  conflictsResolved: Array<{ menu_date: string; slot: string }>
}

export async function applyOverrideNow(
  weekStart: string,
  menuDate: string,
  slot: string,
  forcedDishId: number,
): Promise<ApplyOverrideResult> {
  const monday = ensureMonday(weekStart)
  return withFallback(
    async () => {
      // 1. Save the forced dish in the override table
      await apiClient.post('/overrides', { menu_date: menuDate, slot, forced_dish_id: forcedDishId, week_start: monday })
      // 2. Apply it immediately (recompute slot + auto-regenerate conflicts)
      const { data: applyData } = await apiClient.post<{ ok: boolean; conflicts_resolved: Array<{ menu_date: string; slot: string }> }>(
        `/overrides/${menuDate}/${slot}/apply?week_start=${monday}`,
      )
      // 3. Fetch updated week
      const { data: weekData } = await apiClient.get<WeekData>(`/weeks/${monday}`)
      return { weekData, conflictsResolved: applyData.conflicts_resolved ?? [] }
    },
    async () => {
      await delay(400)
      const current = getMockWeek(monday)
      const dish = MOCK_DISHES.find((d) => d.id === forcedDishId)
      if (!dish) return { weekData: current, conflictsResolved: [] }

      const updatedRows = current.rows.map((r) => {
        if (r.menu_date === menuDate && r.slot === slot) {
          return {
            ...r,
            dish_id: dish.id,
            dish_name: dish.name,
            protein: dish.protein,
            style_tag: dish.style_tag,
            is_forced: true,
          }
        }
        return r
      })
      const updated = { ...current, rows: updatedRows }
      setMockWeek(monday, updated)
      return { weekData: updated, conflictsResolved: [] }
    },
  )
}

export async function clearForcedOverrides(weekStart: string): Promise<WeekData> {
  const monday = ensureMonday(weekStart)
  return withFallback(
    async () => {
      await apiClient.post(`/weeks/${monday}/clear-overrides`)
      const { data } = await apiClient.get<WeekData>(`/weeks/${monday}`)
      return data
    },
    async () => {
      await delay(500)
      const current = getMockWeek(monday)
      const updatedRows = current.rows.map((r) => ({
        ...r,
        is_forced: ['entrada_comal', 'arroz', 'chamorro', 'paella', 'nuggets', 'pancita'].includes(r.slot)
          ? r.is_forced
          : false,
      }))
      const updated = { ...current, rows: updatedRows }
      setMockWeek(monday, updated)
      return updated
    },
  )
}

export async function regenerateDay(weekStart: string, menuDate: string): Promise<WeekData> {
  const monday = ensureMonday(weekStart)
  return withFallback(
    async () => {
      const { data } = await apiClient.post<WeekData>(`/weeks/${monday}/days/${menuDate}/regenerate`)
      return data
    },
    async () => {
      await delay(500)
      const current = getMockWeek(monday)
      if ((current.closed_dates ?? []).includes(menuDate)) {
        throw new Error('El día está cerrado. Reábrelo antes de regenerarlo.')
      }

      const replacementRows = buildWeekRows(monday)
        .filter((r) => r.menu_date === menuDate)
        .map((r) => ({ ...r, explanation: `${r.explanation ?? ''}`.trim() || 'Regenerado (mock).' }))

      const updated: WeekData = {
        ...current,
        rows: [
          ...current.rows.filter((r) => r.menu_date !== menuDate),
          ...replacementRows,
        ].sort((a, b) => a.menu_date.localeCompare(b.menu_date) || a.slot.localeCompare(b.slot)),
      }
      setMockWeek(monday, updated)
      return updated
    },
  )
}

export async function closeDay(weekStart: string, menuDate: string): Promise<WeekData> {
  const monday = ensureMonday(weekStart)
  return withFallback(
    async () => {
      const { data } = await apiClient.delete<WeekData>(`/weeks/${monday}/days/${menuDate}`)
      return data
    },
    async () => {
      await delay(300)
      const current = getMockWeek(monday)
      const updated: WeekData = {
        ...current,
        rows: current.rows.filter((r) => r.menu_date !== menuDate),
        closed_dates: [...(current.closed_dates ?? []), menuDate],
      }
      setMockWeek(monday, updated)
      return updated
    },
  )
}
