// ─── Domain types ────────────────────────────────────────────

export type CourseGroup =
  | 'sopa'
  | 'crema'
  | 'pasta'
  | 'entrada'
  | 'fuerte'
  | 'complemento'
  | 'ensalada'
  | 'arroz'
  | 'especial'

export type Protein =
  | 'res'
  | 'pollo'
  | 'cerdo'
  | 'pescado'
  | 'camaron'
  | 'atun'
  | 'none'

export interface Dish {
  id: number
  name: string
  course_group: CourseGroup
  protein: Protein
  style_tag: string | null
  sauce_tag: string | null
  active: boolean
  last_used?: string | null
  tags?: string[]
}

export interface MenuRow {
  menu_date: string     // yyyy-mm-dd
  slot: string
  dish_id: number
  dish_name: string
  course_group: CourseGroup
  protein: Protein
  style_tag: string | null
  is_forced: boolean
  was_exception: boolean
  exception_reason: string | null
  explanation: string | null
}

export interface WeekMeta {
  id: number
  week_start_date: string
  generated_at: string | null
  finalized: boolean
  notes: string | null
}

export interface WeekData {
  week: WeekMeta | null
  rows: MenuRow[]
  closed_dates?: string[]
}

// ─── Override types ───────────────────────────────────────────

export interface Override {
  menu_date: string
  slot: string
  forced_dish_id?: number | null
  blocked_dish_id?: number | null
  note?: string | null
}

// ─── Report types ─────────────────────────────────────────────

export interface WeekReportSlot {
  slot: string
  dish: string
  protein: Protein
  sauce_tag: string | null
  is_forced: boolean
  was_exception: boolean
  exception_reason: string | null
}

export interface WeekReportDay {
  date: string
  day_name: string
  slots: WeekReportSlot[]
}

export interface WeekReport {
  week_start: string
  week_id: number
  days: WeekReportDay[]
  sauces_used: string[]
  proteins_by_day: Record<string, Record<string, number>>
  exceptions: Array<{
    date: string
    slot: string
    reason: string | null
    dish: string
  }>
  warnings: string[]
  score: number
  totals: {
    dishes: number
    with_sauce_tag: number
    exceptions: number
    forced_overrides: number
    sauces_unique: number
  }
}

export interface ShoppingSummaryEntry {
  date: string
  slot: string
  dish: string
}

export interface ShoppingSummary {
  week_start: string
  by_protein: Record<Protein, ShoppingSummaryEntry[]>
  counts: Record<string, number>
  daily_breakdown: Record<string, Record<string, number>>
}

export interface CatalogHealthDish {
  id: number
  name: string
  course_group: CourseGroup
  protein: Protein
  uses?: number
  last_used?: string
  days_ago?: number
}

export interface CatalogHealth {
  generated_at: string
  since_days: number
  total_active: number
  never_used: CatalogHealthDish[]
  dormant: CatalogHealthDish[]
  overused: CatalogHealthDish[]
  by_group: Record<string, { total: number; never: number; dormant: number; overused: number }>
}

// ─── UI helper types ──────────────────────────────────────────

export type Page = 'menu' | 'catalog' | 'reports'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  type: ToastType
  message: string
}
