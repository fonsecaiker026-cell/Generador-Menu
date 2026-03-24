import { useState, useCallback, useEffect } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  Zap,
  RefreshCw,
  CheckCircle,
  Unlock,
  FileText,
  Trash2,
  AlertTriangle,
  Calendar,
} from 'lucide-react'
import { format, addWeeks, subWeeks, startOfWeek } from 'date-fns'
import { es } from 'date-fns/locale'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { WeekGrid } from '../components/menu/WeekGrid'
import { SlotEditModal } from '../components/menu/SlotEditModal'
import { ConfirmDialog } from '../components/ui/Modal'
import { useToast } from '../context/ToastContext'
import type { WeekData, MenuRow } from '../types'
import {
  fetchWeek,
  fetchWeekList,
  generateWeek,
  regenerateDay,
  regenerateWeek,
  finalizeWeek,
  applyOverrideNow,
  removeOverride,
  closeDay,
  clearForcedOverrides,
  type WeekSummary,
} from '../api/menu'
import { isMockMode, getApiError } from '../api/client'

function getMonday(date: Date): Date {
  return startOfWeek(date, { weekStartsOn: 1 })
}

function formatWeekLabel(weekStart: string): string {
  const d = new Date(weekStart + 'T12:00:00')
  const end = new Date(d)
  end.setDate(end.getDate() + 5)
  const startFmt = format(d, "d 'de' MMMM", { locale: es })
  const endFmt = format(end, "d 'de' MMMM yyyy", { locale: es })
  return `${startFmt} – ${endFmt}`
}

function getCurrentWeekStart(): string {
  const monday = getMonday(new Date())
  return format(monday, 'yyyy-MM-dd')
}

export function MenuPage() {
  const { showToast } = useToast()

  // Week navigation
  const [weekStart, setWeekStart] = useState(getCurrentWeekStart)
  const [weekData, setWeekData] = useState<WeekData | null>(null)
  const [loadingWeek, setLoadingWeek] = useState(false)
  const [weekList, setWeekList] = useState<WeekSummary[]>([])

  // Edit
  const [editingRow, setEditingRow] = useState<MenuRow | null>(null)

  // Actions
  const [generating, setGenerating] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [finalizing, setFinalizing] = useState(false)

  // Confirms
  const [showRegenerateConfirm, setShowRegenerateConfirm] = useState(false)
  const [showFinalizeConfirm, setShowFinalizeConfirm] = useState(false)
  const [showUnfinalizeConfirm, setShowUnfinalizeConfirm] = useState(false)
  const [showClearConfirm, setShowClearConfirm] = useState(false)
  const [dayToRegenerate, setDayToRegenerate] = useState<string | null>(null)
  const [dayToClose, setDayToClose] = useState<string | null>(null)

  // Load week data
  const loadWeek = useCallback(async (ws: string) => {
    setLoadingWeek(true)
    try {
      const data = await fetchWeek(ws)
      setWeekData(data)
    } catch (err) {
      showToast('Error al cargar la semana: ' + getApiError(err), 'error')
    } finally {
      setLoadingWeek(false)
    }
  }, [showToast])

  const loadWeekList = useCallback(async () => {
    try {
      const list = await fetchWeekList()
      setWeekList(list)
    } catch {
      // No crítico — la navegación de semanas sigue funcionando
    }
  }, [])

  // Load on first render
  useEffect(() => {
    loadWeek(weekStart)
    loadWeekList()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Navigation
  const goToPrevWeek = () => {
    const d = new Date(weekStart + 'T12:00:00')
    const prev = format(subWeeks(d, 1), 'yyyy-MM-dd')
    setWeekStart(prev)
    loadWeek(prev)
  }

  const goToNextWeek = () => {
    const d = new Date(weekStart + 'T12:00:00')
    const next = format(addWeeks(d, 1), 'yyyy-MM-dd')
    setWeekStart(next)
    loadWeek(next)
  }

  const goToCurrentWeek = () => {
    const now = getMonday(new Date())
    const ws = format(now, 'yyyy-MM-dd')
    setWeekStart(ws)
    loadWeek(ws)
  }

  // Actions
  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const data = await generateWeek(weekStart)
      setWeekData(data)
      loadWeekList()
      showToast('Semana generada exitosamente', 'success')
    } catch (err) {
      showToast('Error al generar: ' + getApiError(err), 'error')
    } finally {
      setGenerating(false)
    }
  }

  const handleRegenerate = async () => {
    setShowRegenerateConfirm(false)
    setRegenerating(true)
    try {
      const data = await regenerateWeek(weekStart)
      setWeekData(data)
      showToast('Semana regenerada', 'success')
    } catch (err) {
      showToast('Error al regenerar: ' + getApiError(err), 'error')
    } finally {
      setRegenerating(false)
    }
  }

  const handleFinalize = async () => {
    setShowFinalizeConfirm(false)
    setFinalizing(true)
    try {
      const warnings = await finalizeWeek(weekStart, true)
      setWeekData((prev) =>
        prev ? { ...prev, week: prev.week ? { ...prev.week, finalized: true } : null } : null,
      )
      loadWeekList()
      showToast('Semana finalizada', 'success')
    } catch (err) {
      showToast(getApiError(err), 'error')
    } finally {
      setFinalizing(false)
    }
  }

  const handleUnfinalize = async () => {
    setShowUnfinalizeConfirm(false)
    setFinalizing(true)
    try {
      await finalizeWeek(weekStart, false)
      setWeekData((prev) =>
        prev ? { ...prev, week: prev.week ? { ...prev.week, finalized: false } : null } : null,
      )
      loadWeekList()
      showToast('Semana reabierta', 'info')
    } catch (err) {
      showToast('Error: ' + getApiError(err), 'error')
    } finally {
      setFinalizing(false)
    }
  }

  const handleClearOverrides = async () => {
    setShowClearConfirm(false)
    try {
      const data = await clearForcedOverrides(weekStart)
      setWeekData(data)
      showToast('Overrides eliminados', 'info')
    } catch (err) {
      showToast('Error: ' + getApiError(err), 'error')
    }
  }

  const handleRegenerateDay = async () => {
    if (!dayToRegenerate) return
    const targetDate = dayToRegenerate
    setDayToRegenerate(null)
    setRegenerating(true)
    try {
      const data = await regenerateDay(weekStart, targetDate)
      setWeekData(data)
      showToast('Dia regenerado', 'success')
    } catch (err) {
      showToast('Error al regenerar el dia: ' + getApiError(err), 'error')
    } finally {
      setRegenerating(false)
    }
  }

  const handleCloseDay = async () => {
    if (!dayToClose) return
    const targetDate = dayToClose
    setDayToClose(null)
    try {
      const data = await closeDay(weekStart, targetDate)
      setWeekData(data)
      showToast('Día cerrado. Ya no cuenta en historial.', 'info')
    } catch (err) {
      showToast('Error: ' + getApiError(err), 'error')
    }
  }

  // Override: apply immediately
  const handleApplyOverride = async (menuDate: string, slot: string, forcedDishId: number) => {
    try {
      const { weekData, conflictsResolved } = await applyOverrideNow(weekStart, menuDate, slot, forcedDishId)
      setWeekData(weekData)
      if (conflictsResolved.length > 0) {
        showToast(`Override aplicado. ${conflictsResolved.length} slot${conflictsResolved.length > 1 ? 's regenerados' : ' regenerado'} por conflicto.`, 'success')
      } else {
        showToast('Override aplicado', 'success')
      }
    } catch (err) {
      showToast('Error al aplicar override: ' + getApiError(err), 'error')
      throw err // Re-lanza para que el modal sepa que falló y no se cierre
    }
  }

  // Remove override — recomputes slot immediately, no regeneration needed
  const handleRemoveOverride = async (menuDate: string, slot: string) => {
    try {
      const data = await removeOverride(menuDate, slot, weekStart)
      setWeekData(data)
      showToast('Override eliminado', 'info')
    } catch (err) {
      showToast('Error al quitar override: ' + getApiError(err), 'error')
      throw err // Re-lanza para que el modal sepa que falló y no se cierre
    }
  }

  // Export (mock)
  const handleExportPDF = () => {
    if (!isFinalized) {
      showToast('Primero finaliza la semana para exportar PDF', 'info')
      return
    }
    if (isMockMode) {
      showToast('PDF disponible con el backend conectado', 'info')
    } else {
      window.open(`/api/weeks/${weekStart}/pdf`, '_blank')
    }
  }

  const week = weekData?.week ?? null
  const rows = weekData?.rows ?? []
  const hasMenu = !!week && rows.length > 0
  const isFinalized = week?.finalized ?? false
  const exceptionCount = rows.filter((r) => r.was_exception).length
  const forcedCount = rows.filter(
    (r) => r.is_forced && !['entrada_comal', 'arroz', 'chamorro', 'paella', 'nuggets', 'pancita'].includes(r.slot),
  ).length

  const weekDates = new Set(weekList.map((w) => w.week_start_date))
  const finalizedDates = new Set(weekList.filter((w) => w.finalized).map((w) => w.week_start_date))
  const prevWeekDate = format(subWeeks(new Date(weekStart + 'T12:00:00'), 1), 'yyyy-MM-dd')
  const nextWeekDate = format(addWeeks(new Date(weekStart + 'T12:00:00'), 1), 'yyyy-MM-dd')
  const prevHasMenu = weekDates.has(prevWeekDate)
  const prevIsFinalized = finalizedDates.has(prevWeekDate)
  const nextHasMenu = weekDates.has(nextWeekDate)
  const nextIsFinalized = finalizedDates.has(nextWeekDate)

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 bg-white border-b border-warm-200 px-6 py-4">
        {/* Mock badge */}
        {isMockMode && (
          <div className="flex items-center gap-2 mb-3 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-lg w-fit">
            <AlertTriangle className="w-3.5 h-3.5 text-blue-500" />
            <span className="text-xs text-blue-700 font-medium">Modo demo — datos de muestra</span>
          </div>
        )}

        <div className="flex items-center justify-between gap-4 flex-wrap">
          {/* Week navigation */}
          <div className="flex items-center gap-3">
            <div className="flex items-center">
              <button
                onClick={goToPrevWeek}
                title={prevHasMenu ? (prevIsFinalized ? 'Semana anterior — finalizada' : 'Semana anterior — borrador') : 'Semana anterior — sin menú'}
                className="relative h-8 w-8 flex items-center justify-center rounded-l-lg border border-warm-300 hover:bg-warm-100 text-warm-600 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                {prevHasMenu && (
                  <span className={`absolute bottom-0.5 right-0.5 w-1.5 h-1.5 rounded-full ${prevIsFinalized ? 'bg-emerald-500' : 'bg-amber-400'}`} />
                )}
              </button>
              <button
                onClick={goToCurrentWeek}
                title="Ir a esta semana"
                className="h-8 px-2 flex items-center gap-1.5 border-t border-b border-warm-300 hover:bg-warm-100 text-warm-600 text-xs transition-colors"
              >
                <Calendar className="w-3.5 h-3.5" />
                Hoy
              </button>
              <button
                onClick={goToNextWeek}
                title={nextHasMenu ? (nextIsFinalized ? 'Semana siguiente — finalizada' : 'Semana siguiente — borrador') : 'Semana siguiente — sin menú'}
                className="relative h-8 w-8 flex items-center justify-center rounded-r-lg border border-warm-300 hover:bg-warm-100 text-warm-600 transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
                {nextHasMenu && (
                  <span className={`absolute bottom-0.5 right-0.5 w-1.5 h-1.5 rounded-full ${nextIsFinalized ? 'bg-emerald-500' : 'bg-amber-400'}`} />
                )}
              </button>
            </div>

            <div>
              <p className="text-lg font-semibold text-warm-900 leading-tight">
                {formatWeekLabel(weekStart)}
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                {week ? (
                  <>
                    {isFinalized ? (
                      <Badge variant="success">Finalizada</Badge>
                    ) : (
                      <Badge variant="warning">Borrador</Badge>
                    )}
                    {week.generated_at && (
                      <span className="text-xs text-warm-400">
                        Generado {new Date(week.generated_at).toLocaleDateString('es-MX', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                      </span>
                    )}
                  </>
                ) : loadingWeek ? (
                  <span className="text-xs text-warm-400">Cargando…</span>
                ) : (
                  <Badge variant="muted">Sin menú</Badge>
                )}
                {exceptionCount > 0 && (
                  <Badge variant="warning">{exceptionCount} excepción{exceptionCount > 1 ? 'es' : ''}</Badge>
                )}
                {forcedCount > 0 && (
                  <Badge variant="amber">{forcedCount} forzado{forcedCount > 1 ? 's' : ''}</Badge>
                )}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 flex-wrap">
            {hasMenu && !isFinalized && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  icon={<Trash2 className="w-3.5 h-3.5" />}
                  onClick={() => setShowClearConfirm(true)}
                  className="text-warm-500"
                >
                  Limpiar overrides
                </Button>
                <Button
                  variant="secondary"
                  icon={<RefreshCw className="w-4 h-4" />}
                  onClick={() => setShowRegenerateConfirm(true)}
                  loading={regenerating}
                >
                  Regenerar
                </Button>
                <Button
                  variant="success"
                  icon={<CheckCircle className="w-4 h-4" />}
                  onClick={() => setShowFinalizeConfirm(true)}
                  loading={finalizing}
                >
                  Finalizar
                </Button>
              </>
            )}

            {hasMenu && isFinalized && (
              <Button
                variant="secondary"
                icon={<Unlock className="w-4 h-4" />}
                onClick={() => setShowUnfinalizeConfirm(true)}
              >
                Reabrir
              </Button>
            )}

            {hasMenu && (
              <Button
                variant="ghost"
                size="sm"
                icon={<FileText className="w-3.5 h-3.5" />}
                onClick={handleExportPDF}
                disabled={!isFinalized}
              >
                PDF
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* Grid area */}
      {loadingWeek ? (
        <div className="flex-1 flex items-center justify-center text-warm-400">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-brand-200 border-t-brand-600 rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm">Cargando semana…</p>
          </div>
        </div>
      ) : !hasMenu ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-sm px-6">
            <div className="w-14 h-14 rounded-2xl bg-warm-100 flex items-center justify-center mx-auto mb-4">
              <Calendar className="w-7 h-7 text-warm-400" />
            </div>
            <h3 className="text-base font-semibold text-warm-800 mb-1">Sin menú esta semana</h3>
            <p className="text-sm text-warm-500 mb-6">
              Aún no se ha generado el menú para{' '}
              <span className="font-medium text-warm-700">{formatWeekLabel(weekStart)}</span>.
            </p>
            <Button
              variant="primary"
              size="lg"
              icon={<Zap className="w-5 h-5" />}
              onClick={handleGenerate}
              loading={generating}
            >
              Generar menú
            </Button>
          </div>
        </div>
      ) : (
        <WeekGrid
          weekStart={weekStart}
          rows={rows}
          week={week}
          onEditSlot={setEditingRow}
          onDeleteDay={setDayToClose}
          onRegenerateDay={setDayToRegenerate}
          closedDates={weekData?.closed_dates ?? []}
        />
      )}

      {/* Legend */}
      {hasMenu && (
        <div className="flex-shrink-0 px-4 py-2 bg-white border-t border-warm-200 flex items-center gap-5 text-[11px] text-warm-500">
          <span className="font-medium text-warm-600">Leyenda:</span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded border border-warm-200 bg-warm-50 flex-shrink-0 inline-block" /> Fijo
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded border border-amber-300 bg-amber-50 flex-shrink-0 inline-block" /> Forzado
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded border border-orange-300 bg-orange-50 flex-shrink-0 inline-block" /> Excepción
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded border border-warm-200 bg-white flex-shrink-0 inline-block" /> Normal
          </span>
          {!isFinalized && (
            <span className="text-warm-400">· Haz clic en un platillo para editarlo</span>
          )}
        </div>
      )}

      {/* Slot edit modal */}
      <SlotEditModal
        row={editingRow}
        weekStart={weekStart}
        weekRows={rows}
        onClose={() => setEditingRow(null)}
        onApply={handleApplyOverride}
        onRemoveOverride={handleRemoveOverride}
      />

      {/* Confirm dialogs */}
      <ConfirmDialog
        open={showRegenerateConfirm}
        onClose={() => setShowRegenerateConfirm(false)}
        onConfirm={handleRegenerate}
        title="Regenerar semana"
        description="Se regenerará toda la semana con nuevos platillos (respetando overrides forzados). ¿Continuar?"
        confirmLabel="Regenerar"
        loading={regenerating}
      />
      <ConfirmDialog
        open={!!dayToRegenerate}
        onClose={() => setDayToRegenerate(null)}
        onConfirm={handleRegenerateDay}
        title="Regenerar dia"
        description="Se regenerara solo este dia. El resto de la semana se conservara; si el dia es ancla de ensalada semanal, solo se sincronizara su dia espejo."
        confirmLabel="Regenerar dia"
        loading={regenerating}
      />
      <ConfirmDialog
        open={showFinalizeConfirm}
        onClose={() => setShowFinalizeConfirm(false)}
        onConfirm={handleFinalize}
        title="Finalizar semana"
        description="La semana quedará bloqueada para edición. Podrás reabrirla si es necesario."
        confirmLabel="Finalizar"
        variant="primary"
      />
      <ConfirmDialog
        open={showUnfinalizeConfirm}
        onClose={() => setShowUnfinalizeConfirm(false)}
        onConfirm={handleUnfinalize}
        title="Reabrir semana"
        description="La semana volverá a modo borrador y podrás editar los platillos."
        confirmLabel="Reabrir"
      />
      <ConfirmDialog
        open={showClearConfirm}
        onClose={() => setShowClearConfirm(false)}
        onConfirm={handleClearOverrides}
        title="Limpiar overrides forzados"
        description={`Se eliminarán los ${forcedCount} platillo${forcedCount !== 1 ? 's' : ''} forzado${forcedCount !== 1 ? 's' : ''} manualmente de esta semana. Los slots afectados se recalcularán con el algoritmo de rotación.`}
        confirmLabel="Sí, limpiar"
        variant="danger"
      />
      <ConfirmDialog
        open={!!dayToClose}
        onClose={() => setDayToClose(null)}
        onConfirm={handleCloseDay}
        title="Cerrar día"
        description="Se eliminarán todos los platillos de ese día, dejarán de contar como usados en historial y futuras regeneraciones respetarán el cierre."
        confirmLabel="Sí, cerrar día"
        variant="danger"
      />
    </div>
  )
}
