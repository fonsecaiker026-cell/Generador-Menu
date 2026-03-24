import { apiClient, withFallback, delay } from './client'
import { MOCK_WEEK_REPORT, MOCK_CATALOG_HEALTH } from '../mocks/data'
import type { WeekReport, CatalogHealth } from '../types'

export async function fetchWeekReport(weekStart: string): Promise<WeekReport> {
  return withFallback(
    async () => {
      const { data } = await apiClient.get<WeekReport>(`/weeks/${weekStart}/report`)
      return data
    },
    async () => {
      await delay(200)
      return { ...MOCK_WEEK_REPORT, week_start: weekStart }
    },
  )
}

export async function fetchCatalogHealth(
  sinceDays = 60,
  maxUsesWarn = 11,
): Promise<CatalogHealth> {
  return withFallback(
    async () => {
      const { data } = await apiClient.get<CatalogHealth>('/reports/catalog-health', {
        params: { since_days: sinceDays, max_uses_warn: maxUsesWarn },
      })
      return data
    },
    async () => {
      await delay(250)
      return MOCK_CATALOG_HEALTH
    },
  )
}

export function exportPdfUrl(weekStart: string): string {
  return `/api/weeks/${weekStart}/pdf`
}

export function exportCsvUrl(weekStart: string): string {
  return `/api/weeks/${weekStart}/csv`
}
