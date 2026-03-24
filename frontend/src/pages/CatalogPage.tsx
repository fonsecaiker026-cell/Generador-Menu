import { useState, useEffect, useCallback } from 'react'
import { Search, Plus, Pencil, EyeOff, Eye, X, ChevronUp, ChevronDown, Filter } from 'lucide-react'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Modal } from '../components/ui/Modal'
import { Select } from '../components/ui/Select'
import { useToast } from '../context/ToastContext'
import type { Dish } from '../types'
import { fetchDishes, createDish, updateDish, setDishActive } from '../api/dishes'
import { PROTEIN_DOT } from '../components/menu/constants'
import { clsx } from 'clsx'

// ─── Dish type system ─────────────────────────────────────────

interface DishTypeConfig {
  id: string
  label: string
  sublabel?: string
  course_group: string
  fixed_protein?: string       // Protein is fixed (no picker shown)
  exclude_proteins?: string[]  // Proteins hidden from picker
  fixed_style_tag?: string     // Always use this style_tag (e.g. monday_molcajete)
  style_tag_prefix?: string    // style_tag = prefix_slug(name)
  auto_tags?: string[]         // Tags always applied for this tipo (e.g. monday_molcajete)
  allow_priority_tags?: boolean // Backward-compatible flag: enables both Friday and Saturday priority
  priority_tags?: Array<'only_fri' | 'only_sat'> // Allowed day-priority tags for this type
  allow_complemento_tag?: boolean // Show also_complemento checkbox
}

const DISH_TYPES: DishTypeConfig[] = [
  // Sopas
  { id: 'sopa',          label: 'Sopa',                sublabel: 'Lunes a viernes',            course_group: 'sopa',           exclude_proteins: ['pollo'], priority_tags: ['only_fri'] },
  { id: 'sopa_pollo',    label: 'Sopa de Pollo',       sublabel: 'Solo sábado',                course_group: 'sopa',           fixed_protein: 'pollo', auto_tags: ['only_sat'] },
  { id: 'crema',         label: 'Crema',                                                         course_group: 'crema',          priority_tags: ['only_fri', 'only_sat'] },
  { id: 'pasta',         label: 'Pasta',                                                         course_group: 'pasta',          priority_tags: ['only_fri', 'only_sat'] },
  // Entradas
  { id: 'entrada',       label: 'Entrada',                                                       course_group: 'entrada_no_comal', priority_tags: ['only_fri', 'only_sat'] },
  // Ensalada
  { id: 'ensalada',      label: 'Ensalada',                                                      course_group: 'ensalada',       priority_tags: ['only_fri', 'only_sat'] },
  // Platos fuertes
  { id: 'fuerte_res',    label: 'Plato Fuerte — Res',                                           course_group: 'fuerte', fixed_protein: 'res',     allow_priority_tags: true, allow_complemento_tag: true },
  { id: 'fuerte_pollo',  label: 'Plato Fuerte — Pollo',                                         course_group: 'fuerte', fixed_protein: 'pollo',   allow_priority_tags: true, allow_complemento_tag: true },
  { id: 'fuerte_cerdo',  label: 'Plato Fuerte — Cerdo',                                         course_group: 'fuerte', fixed_protein: 'cerdo',   allow_priority_tags: true, allow_complemento_tag: true },
  { id: 'fuerte_pescado',label: 'Plato Fuerte — Pescado',                                       course_group: 'fuerte', fixed_protein: 'pescado', allow_priority_tags: true, allow_complemento_tag: true },
  { id: 'fuerte_camaron',label: 'Plato Fuerte — Camarón',                                       course_group: 'fuerte', fixed_protein: 'camaron', allow_priority_tags: true, allow_complemento_tag: true },
  { id: 'molcajete',     label: 'Molcajete',           sublabel: 'Solo lunes',                  course_group: 'fuerte', exclude_proteins: ['none'], fixed_style_tag: 'monday_molcajete', auto_tags: ['monday_molcajete'] },
  // Complementos
  { id: 'complemento',   label: 'Complemento',         sublabel: 'Todos los días',              course_group: 'complemento',    allow_priority_tags: true },
  { id: 'enchiladas',    label: 'Enchiladas',          sublabel: 'Complemento + slot sábado',   course_group: 'complemento',    style_tag_prefix: 'enchiladas', auto_tags: ['sat_enchiladas'] },
]

function slugify(s: string): string {
  return s.toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '')
    .slice(0, 60)
}

function genStyleTag(tipo: DishTypeConfig, name: string): string {
  if (tipo.fixed_style_tag) return tipo.fixed_style_tag
  if (tipo.style_tag_prefix) return `${tipo.style_tag_prefix}_${slugify(name)}`
  return slugify(name)
}

function detectTipoId(dish: Dish): string {
  const cg = dish.course_group as string
  const p  = dish.protein as string
  const st = dish.style_tag ?? ''
  if (cg === 'fuerte') {
    if (st.includes('molcajete')) return 'molcajete'
    const map: Record<string, string> = {
      res: 'fuerte_res', pollo: 'fuerte_pollo', cerdo: 'fuerte_cerdo',
      pescado: 'fuerte_pescado', camaron: 'fuerte_camaron', marisco: 'fuerte_pescado',
    }
    return map[p] ?? 'fuerte_res'
  }
  if (cg === 'sopa') return p === 'pollo' ? 'sopa_pollo' : 'sopa'
  if (cg === 'crema') return 'crema'
  if (cg === 'pasta') return 'pasta'
  if (cg === 'entrada_no_comal') return 'entrada'
  if (cg === 'ensalada') return 'ensalada'
  if (cg === 'enchiladas') return 'enchiladas'
  if (cg === 'complemento') {
    if (st.startsWith('enchiladas_') || st.includes('enchilada')) return 'enchiladas'
    return 'complemento'
  }
  return 'complemento'
}

function isChamorroFixedDish(dish: Dish): boolean {
  const st = (dish.style_tag ?? '').toLowerCase()
  const tags = (dish.tags ?? []).map((t) => t.toLowerCase())
  return st.includes('chamorro') || tags.includes('friday_chamorro')
}

function tipoLabel(dish: Dish): { label: string; sublabel?: string } {
  const tipo = DISH_TYPES.find(t => t.id === detectTipoId(dish))
  return { label: tipo?.label ?? dish.course_group, sublabel: tipo?.sublabel }
}

function priorityTagsForCatalog(dish: Dish): Array<'only_fri' | 'only_sat'> {
  const tags = new Set((dish.tags ?? []).map((t) => t.toLowerCase()))
  const result: Array<'only_fri' | 'only_sat'> = []
  if (tags.has('only_fri')) result.push('only_fri')
  if (tags.has('only_sat')) result.push('only_sat')
  return result
}

function priorityLabel(dish: Dish): string | null {
  const tags = new Set((dish.tags ?? []).map((t) => t.toLowerCase()))
  const days: string[] = []
  if (tags.has('only_fri')) days.push('Viernes')
  if (tags.has('only_sat')) days.push('Sábado')
  return days.length ? `Sale: ${days.join(' / ')}` : null
}

// ─── Protein options ──────────────────────────────────────────

const ALL_PROTEINS = [
  { value: 'none',    label: 'Sin proteína' },
  { value: 'res',     label: 'Res' },
  { value: 'pollo',   label: 'Pollo' },
  { value: 'cerdo',   label: 'Cerdo' },
  { value: 'pescado', label: 'Pescado' },
  { value: 'camaron', label: 'Camarón' },
]

// ─── Filter options ───────────────────────────────────────────

const FILTER_TIPO_OPTIONS = [
  { value: 'ALL',              label: 'Todos los tipos',      course_group: 'ALL' },
  { value: 'fuerte',           label: 'Platos Fuertes',       course_group: 'fuerte' },
  { value: 'sopa',             label: 'Sopas',                course_group: 'sopa' },
  { value: 'crema',            label: 'Cremas',               course_group: 'crema' },
  { value: 'pasta',            label: 'Pastas',               course_group: 'pasta' },
  { value: 'entrada_no_comal', label: 'Entradas',             course_group: 'entrada_no_comal' },
  { value: 'ensalada',         label: 'Ensaladas',            course_group: 'ensalada' },
  { value: 'complemento',      label: 'Complementos',         course_group: 'complemento' },
]

const ACTIVE_OPTIONS = [
  { value: 'ALL',      label: 'Activos e inactivos' },
  { value: 'ACTIVE',   label: 'Solo activos' },
  { value: 'INACTIVE', label: 'Solo inactivos' },
]

// ─── Form ─────────────────────────────────────────────────────

interface FormState {
  name: string
  tipoId: string
  protein: string
  sauce_tag: string
  only_fri: boolean
  only_sat: boolean
  also_complemento: boolean
  active: boolean
}

function emptyForm(): FormState {
  return { name: '', tipoId: 'fuerte_res', protein: 'res', sauce_tag: '', only_fri: false, only_sat: false, also_complemento: false, active: true }
}

function dishToForm(dish: Dish): FormState {
  const tags = dish.tags ?? []
  return {
    name: dish.name,
    tipoId: detectTipoId(dish),
    protein: dish.protein as string,
    sauce_tag: dish.sauce_tag ?? '',
    only_fri: tags.includes('only_fri'),
    only_sat: tags.includes('only_sat'),
    also_complemento: tags.includes('also_complemento'),
    active: dish.active,
  }
}

function formToPayload(form: FormState) {
  const tipo = DISH_TYPES.find(t => t.id === form.tipoId)!
  const protein = tipo.fixed_protein ?? form.protein
  const style_tag = genStyleTag(tipo, form.name)
  const supportsFridayPriority = tipo.priority_tags?.includes('only_fri') ?? !!tipo.allow_priority_tags
  const supportsSaturdayPriority = tipo.priority_tags?.includes('only_sat') ?? !!tipo.allow_priority_tags

  // Build tags: auto_tags from tipo + user-selected flags
  const tags: string[] = [...(tipo.auto_tags ?? [])]
  if (form.only_fri && supportsFridayPriority) tags.push('only_fri')
  if (form.only_sat && supportsSaturdayPriority) tags.push('only_sat')
  if (form.also_complemento && tipo.allow_complemento_tag) tags.push('also_complemento')

  return {
    name: form.name.trim(),
    course_group: tipo.course_group,
    protein,
    style_tag,
    sauce_tag: form.sauce_tag.trim() || null,
    active: form.active,
    tags,
  }
}

interface DishFormModalProps {
  dish: Dish | null
  open: boolean
  onClose: () => void
  onSave: (payload: ReturnType<typeof formToPayload>) => Promise<void>
}

function DishFormModal({ dish, open, onClose, onSave }: DishFormModalProps) {
  const [form, setForm] = useState<FormState>(emptyForm())
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (open) {
      setForm(dish ? dishToForm(dish) : emptyForm())
      setError('')
    }
  }, [open, dish])

  const tipo = DISH_TYPES.find(t => t.id === form.tipoId)!
  const supportsFridayPriority = tipo.priority_tags?.includes('only_fri') ?? !!tipo.allow_priority_tags
  const supportsSaturdayPriority = tipo.priority_tags?.includes('only_sat') ?? !!tipo.allow_priority_tags

  // When tipo changes, sync protein + reset incompatible flags
  const handleTipoChange = (id: string) => {
    const t = DISH_TYPES.find(d => d.id === id)!
    setForm(p => ({
      ...p,
      tipoId: id,
      protein: t.fixed_protein ?? (t.exclude_proteins?.includes(p.protein) ? 'none' : p.protein),
      // Reset priority flags that don't apply to the new tipo
      only_fri: (t.priority_tags?.includes('only_fri') ?? !!t.allow_priority_tags) ? p.only_fri : false,
      only_sat: (t.priority_tags?.includes('only_sat') ?? !!t.allow_priority_tags) ? p.only_sat : false,
      also_complemento: t.allow_complemento_tag ? p.also_complemento : false,
    }))
  }

  const proteinOptions = tipo.fixed_protein
    ? undefined
    : ALL_PROTEINS.filter(o => !tipo.exclude_proteins?.includes(o.value))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) { setError('El nombre es requerido.'); return }
    setSaving(true)
    try {
      await onSave(formToPayload(form))
      onClose()
    } catch (err: any) {
      setError(err?.message ?? 'Error al guardar.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="md"
      title={dish ? 'Editar platillo' : 'Nuevo platillo'}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button variant="primary" onClick={handleSubmit} loading={saving}>
            {dish ? 'Guardar cambios' : 'Crear platillo'}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Name */}
        <div>
          <label className="block text-xs font-medium text-warm-600 uppercase tracking-wide mb-1">
            Nombre *
          </label>
          <input
            value={form.name}
            onChange={(e) => setForm(p => ({ ...p, name: e.target.value }))}
            placeholder="Ej: Pollo al Chipotle con Papas"
            className="w-full h-9 px-3 text-sm bg-white border border-warm-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent text-warm-900 placeholder:text-warm-400"
          />
        </div>

        {/* Tipo */}
        <div>
          <label className="block text-xs font-medium text-warm-600 uppercase tracking-wide mb-1">
            Tipo de platillo
          </label>
          <select
            value={form.tipoId}
            onChange={(e) => handleTipoChange(e.target.value)}
            className="w-full h-9 px-3 text-sm bg-white border border-warm-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent text-warm-900"
          >
            {DISH_TYPES.map(t => (
              <option key={t.id} value={t.id}>
                {t.label}{t.sublabel ? ` — ${t.sublabel}` : ''}
              </option>
            ))}
          </select>
          {tipo.sublabel && (
            <p className="mt-1 text-xs text-warm-500">{
              tipo.id === 'sopa_pollo' ? 'Esta sopa solo sale en el menú del sábado.' :
              tipo.id === 'molcajete'  ? 'El molcajete solo aparece los lunes. La proteína que elijas determina cuál plato fuerte se elimina ese día.' :
              tipo.id === 'enchiladas' ? 'Aparece como complemento cualquier día y también en el slot de enchiladas del sábado.' :
              tipo.sublabel
            }</p>
          )}
        </div>

        {/* Protein — only when not fixed */}
        {proteinOptions && (
          <Select
            label={tipo.id === 'molcajete' ? 'Proteína * (determina qué plato fuerte se quita el lunes)' : 'Proteína principal'}
            value={form.protein}
            onChange={(v) => setForm(p => ({ ...p, protein: v }))}
            options={proteinOptions}
          />
        )}

        {/* Sauce tag */}
        <div>
          <label className="block text-xs font-medium text-warm-600 uppercase tracking-wide mb-1">
            Salsa / estilo de cocción
            <span className="ml-1 text-warm-400 font-normal normal-case">(opcional)</span>
          </label>
          <input
            value={form.sauce_tag}
            onChange={(e) => setForm(p => ({ ...p, sauce_tag: e.target.value }))}
            placeholder="ej: salsa_chipotle, mole_verde, al_ajillo"
            className="w-full h-9 px-3 text-sm bg-white border border-warm-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent text-warm-900 placeholder:text-warm-400"
          />
          <p className="mt-1 text-[11px] text-warm-400">
            Agrupa platillos con la misma salsa para evitar repetirla en la misma semana.
          </p>
        </div>

        {/* Special day priority / tags */}
        {((supportsFridayPriority || supportsSaturdayPriority) || tipo.allow_complemento_tag) && (
          <div>
            <label className="block text-xs font-medium text-warm-600 uppercase tracking-wide mb-2">
              Día especial
            </label>
            <div className="space-y-2">
              {(supportsFridayPriority || supportsSaturdayPriority) && (
                <>
                  {supportsFridayPriority && (
                  <label className="flex items-start gap-2.5 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={form.only_fri}
                      onChange={(e) => setForm(p => ({ ...p, only_fri: e.target.checked, only_sat: false }))}
                      className="mt-0.5 h-4 w-4 rounded border-warm-300 text-brand-600 focus:ring-brand-500"
                    />
                    <div>
                      <p className="text-sm font-medium text-warm-800 group-hover:text-warm-900">Prioridad viernes</p>
                      <p className="text-[11px] text-warm-500">Se elige primero los viernes. Solo puede salir ese día.</p>
                    </div>
                  </label>
                  )}
                  {supportsSaturdayPriority && (
                  <label className="flex items-start gap-2.5 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={form.only_sat}
                      onChange={(e) => setForm(p => ({ ...p, only_sat: e.target.checked, only_fri: false }))}
                      className="mt-0.5 h-4 w-4 rounded border-warm-300 text-brand-600 focus:ring-brand-500"
                    />
                    <div>
                      <p className="text-sm font-medium text-warm-800 group-hover:text-warm-900">Prioridad sábado</p>
                      <p className="text-[11px] text-warm-500">Se elige primero los sábados. Solo puede salir ese día.</p>
                    </div>
                  </label>
                  )}
                </>
              )}
              {tipo.allow_complemento_tag && (
                <label className="flex items-start gap-2.5 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={form.also_complemento}
                    onChange={(e) => setForm(p => ({ ...p, also_complemento: e.target.checked }))}
                    className="mt-0.5 h-4 w-4 rounded border-warm-300 text-brand-600 focus:ring-brand-500"
                  />
                  <div>
                    <p className="text-sm font-medium text-warm-800 group-hover:text-warm-900">También como complemento</p>
                    <p className="text-[11px] text-warm-500">También aparece disponible en el slot de complemento.</p>
                  </div>
                </label>
              )}
            </div>
          </div>
        )}

        {/* Active */}
        <div className="flex items-center gap-3 pt-1">
          <button
            type="button"
            onClick={() => setForm(p => ({ ...p, active: !p.active }))}
            className={clsx(
              'relative inline-flex h-5 w-9 items-center rounded-full transition-colors flex-shrink-0',
              form.active ? 'bg-brand-600' : 'bg-warm-300',
            )}
          >
            <span className={clsx(
              'inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform',
              form.active ? 'translate-x-4' : 'translate-x-0.5',
            )} />
          </button>
          <label className="text-sm text-warm-700">
            {form.active ? 'Activo — aparece en el generador de menú' : 'Inactivo — no se asigna al menú'}
          </label>
        </div>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
        )}
      </form>
    </Modal>
  )
}

// ─── Main page ────────────────────────────────────────────────

type SortField = 'name' | 'course_group' | 'protein' | 'last_used'
type SortDir   = 'asc' | 'desc'

function formatLastUsedCatalog(last_used: string | null | undefined): { label: string; color: string } {
  if (!last_used) return { label: 'Nunca', color: 'text-warm-400' }
  const today = new Date()
  const used = new Date(last_used + 'T12:00:00')
  const days = Math.max(0, Math.floor((today.getTime() - used.getTime()) / 86400000))
  if (days <= 7)  return { label: `hace ${days}d`,  color: 'text-red-500 font-medium' }
  if (days <= 21) return { label: `hace ${days}d`,  color: 'text-amber-500' }
  if (days <= 60) return { label: `hace ${days}d`,  color: 'text-warm-500' }
  return { label: `hace ${days}d`, color: 'text-warm-400' }
}

interface CatalogPageProps {
  initialQuery?: string
  onQueryConsumed?: () => void
}

export function CatalogPage({ initialQuery = '', onQueryConsumed }: CatalogPageProps) {
  const { showToast } = useToast()
  const [dishes, setDishes] = useState<Dish[]>([])
  const [loading, setLoading] = useState(true)

  // Filters
  const [query,       setQuery]       = useState(initialQuery)
  const [filterTipo,  setFilterTipo]  = useState('ALL')
  const [activeFilter, setActiveFilter] = useState<'ALL' | 'ACTIVE' | 'INACTIVE'>('ACTIVE')

  // Apply external initialQuery when it changes (e.g. navigating from Reports)
  useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery)
      setActiveFilter('ALL')
      onQueryConsumed?.()
    }
  }, [initialQuery])

  // Sort
  const [sortField, setSortField] = useState<SortField>('name')
  const [sortDir,   setSortDir]   = useState<SortDir>('asc')

  // Modal
  const [modalOpen,   setModalOpen]   = useState(false)
  const [editingDish, setEditingDish] = useState<Dish | null>(null)
  const [togglingId,  setTogglingId]  = useState<number | null>(null)

  const filterConfig = FILTER_TIPO_OPTIONS.find(o => o.value === filterTipo)!

  const loadDishes = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchDishes({
        name_query:    query,
        course_group:  filterConfig.course_group,
        active_filter: activeFilter,
      })
      setDishes(data)
    } catch {
      showToast('Error al cargar catálogo', 'error')
    } finally {
      setLoading(false)
    }
  }, [query, filterConfig, activeFilter, showToast])

  useEffect(() => {
    const t = setTimeout(loadDishes, 200)
    return () => clearTimeout(t)
  }, [loadDishes])

  const handleSort = (field: SortField) => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortField(field); setSortDir('asc') }
  }

  const sorted = [...dishes].sort((a, b) => {
    if (sortField === 'last_used') {
      const va = a.last_used ?? ''
      const vb = b.last_used ?? ''
      return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va)
    }
    const va = (a[sortField] as string) ?? ''
    const vb = (b[sortField] as string) ?? ''
    return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va)
  })

  const handleSave = async (payload: ReturnType<typeof formToPayload>) => {
    if (editingDish && isChamorroFixedDish(editingDish)) {
      showToast('Chamorro es un slot fijo y no se modifica desde catálogo', 'info')
      return
    }
    if (editingDish) {
      const updated = await updateDish(editingDish.id, payload)
      setDishes(prev => prev.map(d => d.id === updated.id ? updated : d))
      showToast('Platillo actualizado', 'success')
    } else {
      const created = await createDish(payload)
      setDishes(prev => [...prev, created])
      showToast('Platillo creado', 'success')
    }
  }

  const handleToggleActive = async (dish: Dish) => {
    setTogglingId(dish.id)
    try {
      await setDishActive(dish.id, !dish.active)
      setDishes(prev => prev.map(d => d.id === dish.id ? { ...d, active: !d.active } : d))
      showToast(dish.active ? 'Platillo desactivado' : 'Platillo activado', dish.active ? 'info' : 'success')
    } catch {
      showToast('Error al cambiar estado', 'error')
    } finally {
      setTogglingId(null)
    }
  }

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ChevronUp className="w-3 h-3 text-warm-300" />
    return sortDir === 'asc'
      ? <ChevronUp className="w-3 h-3 text-brand-600" />
      : <ChevronDown className="w-3 h-3 text-brand-600" />
  }

  const hasFilters = query || filterTipo !== 'ALL' || activeFilter !== 'ACTIVE'

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 bg-white border-b border-warm-200 px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold text-warm-900">Catálogo de platillos</h1>
            <p className="text-sm text-warm-500 mt-0.5">
              {dishes.length} platillo{dishes.length !== 1 ? 's' : ''} encontrado{dishes.length !== 1 ? 's' : ''}
            </p>
          </div>
          <Button
            variant="primary"
            icon={<Plus className="w-4 h-4" />}
            onClick={() => { setEditingDish(null); setModalOpen(true) }}
          >
            Nuevo platillo
          </Button>
        </div>

        {/* Filters */}
        <div className="mt-4 flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[200px] max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-warm-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar por nombre…"
              className="w-full h-9 pl-9 pr-8 text-sm bg-white border border-warm-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent text-warm-900 placeholder:text-warm-400"
            />
            {query && (
              <button onClick={() => setQuery('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-warm-400 hover:text-warm-700">
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          <Select
            value={filterTipo}
            onChange={setFilterTipo}
            options={FILTER_TIPO_OPTIONS}
            className="w-52"
          />
          <Select
            value={activeFilter}
            onChange={(v) => setActiveFilter(v as 'ALL' | 'ACTIVE' | 'INACTIVE')}
            options={ACTIVE_OPTIONS}
            className="w-44"
          />
          {hasFilters && (
            <Button
              variant="ghost"
              size="sm"
              icon={<X className="w-3.5 h-3.5" />}
              onClick={() => { setQuery(''); setFilterTipo('ALL'); setActiveFilter('ACTIVE') }}
            >
              Limpiar
            </Button>
          )}
        </div>
      </header>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="flex items-center justify-center h-48 text-warm-400">
            <div className="text-center">
              <div className="w-6 h-6 border-2 border-brand-200 border-t-brand-600 rounded-full animate-spin mx-auto mb-2" />
              <p className="text-sm">Cargando…</p>
            </div>
          </div>
        ) : sorted.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-warm-400">
            <Filter className="w-8 h-8 mb-2 text-warm-300" />
            <p className="text-sm font-medium">Sin resultados</p>
            <p className="text-xs mt-1">Ajusta los filtros de búsqueda</p>
          </div>
        ) : (
          <table className="w-full text-sm border-collapse">
            <thead className="bg-warm-50 sticky top-0 z-10">
              <tr>
                <th className="px-4 py-3 text-left">
                  <button onClick={() => handleSort('name')}
                    className="flex items-center gap-1 text-xs font-semibold text-warm-600 uppercase tracking-wide hover:text-warm-900">
                    Platillo <SortIcon field="name" />
                  </button>
                </th>
                <th className="px-4 py-3 text-left">
                  <button onClick={() => handleSort('course_group')}
                    className="flex items-center gap-1 text-xs font-semibold text-warm-600 uppercase tracking-wide hover:text-warm-900">
                    Tipo <SortIcon field="course_group" />
                  </button>
                </th>
                <th className="px-4 py-3 text-left">
                  <button onClick={() => handleSort('protein')}
                    className="flex items-center gap-1 text-xs font-semibold text-warm-600 uppercase tracking-wide hover:text-warm-900">
                    Proteína <SortIcon field="protein" />
                  </button>
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-warm-600 uppercase tracking-wide">Salsa / estilo</th>
                <th className="px-4 py-3 text-left">
                  <button onClick={() => handleSort('last_used')}
                    className="flex items-center gap-1 text-xs font-semibold text-warm-600 uppercase tracking-wide hover:text-warm-900">
                    Último uso <SortIcon field="last_used" />
                  </button>
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-warm-600 uppercase tracking-wide">Estado</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-warm-600 uppercase tracking-wide">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-warm-100">
              {sorted.map((dish) => {
                const { label, sublabel } = tipoLabel(dish)
                const priorityTags = priorityTagsForCatalog(dish)
                const isChamorroFixed = isChamorroFixedDish(dish)
                return (
                  <tr key={dish.id} className={clsx('transition-colors group', dish.active ? 'hover:bg-warm-50' : 'opacity-60 hover:bg-warm-50')}>
                    <td className="px-4 py-3">
                      <span className="font-medium text-warm-900">{dish.name}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant="default" size="sm">{label}</Badge>
                        {sublabel && (
                          <span className="text-[10px] text-warm-400">{sublabel}</span>
                        )}
                        {priorityTags.map((tag) => (
                          <span
                            key={tag}
                            className={clsx(
                              'text-[10px] font-medium rounded px-1.5 py-0.5 border',
                              tag === 'only_fri'
                                ? 'text-rose-700 bg-rose-50 border-rose-200'
                                : 'text-amber-700 bg-amber-50 border-amber-200',
                            )}
                          >
                            {tag === 'only_fri' ? 'Prioridad viernes' : 'Prioridad sábado'}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {dish.protein !== 'none' && (
                        <div className="flex items-center gap-1.5">
                          <div className={clsx('w-2 h-2 rounded-full flex-shrink-0', PROTEIN_DOT[dish.protein])} />
                          <span className="text-warm-700 text-sm capitalize">{dish.protein}</span>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {dish.sauce_tag
                        ? <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-100">{dish.sauce_tag}</span>
                        : <span className="text-warm-300 text-xs">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      {(() => {
                        const { label, color } = formatLastUsedCatalog(dish.last_used)
                        return <span className={`text-xs ${color}`}>{label}</span>
                      })()}
                    </td>
                    <td className="px-4 py-3">
                      {dish.active
                        ? <Badge variant="success" size="sm">Activo</Badge>
                        : <Badge variant="muted"   size="sm">Inactivo</Badge>}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          disabled={isChamorroFixed}
                          onClick={() => { setEditingDish(dish); setModalOpen(true) }}
                          className="h-7 w-7 flex items-center justify-center rounded-md hover:bg-warm-200 text-warm-500 hover:text-warm-900 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                          title={isChamorroFixed ? 'Chamorro fijo (no editable)' : 'Editar'}
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleToggleActive(dish)}
                          disabled={togglingId === dish.id}
                          className="h-7 w-7 flex items-center justify-center rounded-md hover:bg-warm-200 text-warm-500 hover:text-warm-900 transition-colors disabled:opacity-50"
                          title={dish.active ? 'Desactivar' : 'Activar'}
                        >
                          {dish.active ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      <DishFormModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        dish={editingDish}
        onSave={handleSave}
      />
    </div>
  )
}
