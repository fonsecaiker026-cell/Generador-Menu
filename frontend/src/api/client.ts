import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 8000,
  headers: { 'Content-Type': 'application/json' },
})

export let isMockMode = false

export async function withFallback<T>(
  apiFn: () => Promise<T>,
  mockFn: () => T | Promise<T>,
): Promise<T> {
  if (isMockMode) {
    try {
      const data = await apiFn()
      isMockMode = false
      console.info('[API] Backend reachable again - leaving mock mode.')
      return data
    } catch (err) {
      // If the backend responded (even with an error), it's reachable — stay out of mock mode
      if (axios.isAxiosError(err) && err.response) {
        isMockMode = false
        throw err
      }
      return mockFn()
    }
  }

  try {
    return await apiFn()
  } catch (err) {
    // Only activate mock mode for network failures (no response), not HTTP error responses
    if (axios.isAxiosError(err) && err.response) {
      throw err
    }
    isMockMode = true
    console.info('[API] Backend not available - using mock data.')
    return mockFn()
  }
}

export function delay(ms = 350): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

export function getApiError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((d: any) => d.msg ?? String(d)).join(', ')
  }
  if (err instanceof Error) return err.message
  return 'Error desconocido'
}
