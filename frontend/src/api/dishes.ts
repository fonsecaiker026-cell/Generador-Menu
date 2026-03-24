import { apiClient, withFallback, delay, getApiError } from './client'
import { mockStore } from '../mocks/data'
import type { Dish } from '../types'

export interface DishFilters {
  name_query?: string
  course_group?: string
  protein?: string
  active_filter?: 'ALL' | 'ACTIVE' | 'INACTIVE'
}

export async function fetchDishes(filters: DishFilters = {}): Promise<Dish[]> {
  return withFallback(
    async () => {
      const { data } = await apiClient.get<Dish[]>('/dishes', { params: filters })
      return data
    },
    async () => {
      await delay(150)
      let dishes = mockStore.dishes

      if (filters.name_query) {
        const q = filters.name_query.toLowerCase()
        dishes = dishes.filter((d) => d.name.toLowerCase().includes(q))
      }
      if (filters.course_group && filters.course_group !== 'ALL') {
        dishes = dishes.filter((d) => d.course_group === filters.course_group)
      }
      if (filters.protein && filters.protein !== 'ALL') {
        dishes = dishes.filter((d) => d.protein === filters.protein)
      }
      if (filters.active_filter === 'ACTIVE') {
        dishes = dishes.filter((d) => d.active)
      } else if (filters.active_filter === 'INACTIVE') {
        dishes = dishes.filter((d) => !d.active)
      }
      return [...dishes]
    },
  )
}

export async function fetchAllDishesWithLastUsed(): Promise<Dish[]> {
  return withFallback(
    async () => {
      const { data } = await apiClient.get<Dish[]>('/dishes/with-last-used')
      return data
    },
    async () => {
      await delay(150)
      return mockStore.dishes
        .filter((d) => d.active)
        .map((d) => ({ ...d, last_used: null }))
    },
  )
}

export async function fetchDishesBySlot(
  slot: string,
  referenceDate?: string,
  currentMenuDate?: string,
  currentSlot?: string,
): Promise<Dish[]> {
  return withFallback(
    async () => {
      const params: Record<string, string> = { slot }
      if (referenceDate) params.reference_date = referenceDate
      if (currentMenuDate) params.current_menu_date = currentMenuDate
      if (currentSlot) params.current_slot = currentSlot
      const { data } = await apiClient.get<Dish[]>('/dishes/by-slot', { params })
      return data
    },
    async () => {
      await delay(150)
      // Fallback: filter mock dishes by course_group/protein based on slot
      const SLOT_MAP: Record<string, { course_group: string; protein?: string }> = {
        entrada_no_comal: { course_group: 'entrada_no_comal' },
        sopa:             { course_group: 'sopa' },
        crema:            { course_group: 'crema' },
        pasta:            { course_group: 'pasta' },
        ensalada_A:       { course_group: 'ensalada' },
        ensalada_B:       { course_group: 'ensalada' },
        ensalada_C:       { course_group: 'ensalada' },
        molcajete:        { course_group: 'fuerte' },
        fuerte_res:       { course_group: 'fuerte', protein: 'res' },
        fuerte_pollo:     { course_group: 'fuerte', protein: 'pollo' },
        fuerte_cerdo:     { course_group: 'fuerte', protein: 'cerdo' },
        fuerte_pescado:   { course_group: 'fuerte', protein: 'pescado' },
        fuerte_camaron:   { course_group: 'fuerte', protein: 'camaron' },
        chamorro:         { course_group: 'fuerte', protein: 'cerdo' },
        complemento:      { course_group: 'complemento' },
        pescado_al_gusto: { course_group: 'fuerte', protein: 'pescado' },
        camaron_al_gusto: { course_group: 'fuerte', protein: 'camaron' },
        enchiladas:       { course_group: 'especial' },
        sopa_pollo:       { course_group: 'sopa', protein: 'pollo' },
      }
      const f = SLOT_MAP[slot]
      if (!f) return []
      let dishes = mockStore.dishes.filter((d) => d.active && d.course_group === f.course_group)
      if (f.protein) {
        dishes = dishes.filter((d) => d.protein === f.protein)
      }
      return dishes.map((d) => ({ ...d, last_used: null }))
    },
  )
}

export interface UpsertDishPayload {
  name: string
  course_group: string
  protein: string
  style_tag?: string | null
  sauce_tag?: string | null
  active?: boolean
  tags?: string[]
}

export async function createDish(payload: UpsertDishPayload): Promise<Dish> {
  try {
    const { data } = await apiClient.post<Dish>('/dishes', payload)
    return data
  } catch (err) {
    throw new Error(getApiError(err))
  }
}

export async function updateDish(id: number, payload: Partial<UpsertDishPayload>): Promise<Dish> {
  try {
    const { data } = await apiClient.put<Dish>(`/dishes/${id}`, payload)
    return data
  } catch (err) {
    throw new Error(getApiError(err))
  }
}

export async function setDishActive(id: number, active: boolean): Promise<void> {
  try {
    await apiClient.patch(`/dishes/${id}/active`, { active })
  } catch (err) {
    throw new Error(getApiError(err))
  }
}
