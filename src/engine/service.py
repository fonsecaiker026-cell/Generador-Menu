# src/engine/service.py
from __future__ import annotations

import csv
import os
import random
import shutil
import tempfile
from dataclasses import dataclass
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from src import db as db_module
from src.db import get_conn
from src.engine.generator import (
    SALAD_ANCHOR_OFFSET,
    SALAD_DAYS_BY_SLOT,
    SALAD_SLOTS,
    generate_week as _generate_week,
    clear_day_items,
    dish_is_active,
    ensure_monday,
    parse_yyyy_mm_dd,
    recompute_day,
    recompute_slot,
    to_yyyy_mm_dd,
)
from src.engine.report import selection_diagnostics, strict_audit_week, summarize_simulation_runs, week_report
from src.engine.slots import slots_for_day

# -------------------------
# Modelos para retorno (UI)
# -------------------------
@dataclass
class MenuRow:
    menu_date: str
    slot: str
    dish_id: int
    dish_name: str
    course_group: str
    protein: str
    style_tag: Optional[str]
    is_forced: int
    was_exception: int
    exception_reason: Optional[str]
    explanation: Optional[str]


# -------------------------
# Constantes / Guardrails
# -------------------------
ARROZ_FIXED_ID = 1596
FINALIZE_MIN_STRICT_SCORE = 94
FINALIZE_SIM_WEEKS = 1
FINALIZE_SIM_REROLLS = 2
FINALIZE_SIM_MIN_AVG_SCORE = 92.0
FINALIZE_MIN_ACTIVE_DISHES_FOR_HARD_GATE = 80
GENERATION_MAX_ATTEMPTS = 4


def _current_operational_week_start() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _past_weeks_write_lock_enabled() -> bool:
    # Keep historical lock active in real usage but bypass it in pytest.
    return not bool(os.getenv("PYTEST_CURRENT_TEST"))


def _is_past_week_start(week_start: date) -> bool:
    return week_start < _current_operational_week_start()


def _raise_if_audit_has_errors(week_start_date: str, *, action: str) -> dict[str, Any]:
    audit = strict_audit_week(week_start_date)
    if audit.get("error"):
        raise RuntimeError(str(audit["error"]))
    errors = list(audit.get("errors") or [])
    if not errors:
        return audit

    preview = " | ".join(errors[:4])
    more = ""
    if len(errors) > 4:
        more = f" | ... y {len(errors) - 4} mas"
    raise RuntimeError(f"{action}: auditoria fallo. {preview}{more}")


def _active_dish_count() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM dish WHERE active=1").fetchone()
    return int(row["n"] or 0)


def _raise_if_finalization_quality_gate_fails(week_start_date: str, audit: dict[str, Any]) -> None:
    """Enforce additional quality gates before finalizing a week."""
    if _active_dish_count() < FINALIZE_MIN_ACTIVE_DISHES_FOR_HARD_GATE:
        return

    score = int(audit.get("score") or 0)
    if score < FINALIZE_MIN_STRICT_SCORE:
        raise RuntimeError(
            f"No se puede finalizar: score estricto={score} menor al minimo {FINALIZE_MIN_STRICT_SCORE}."
        )

    sim = simulate_generation_quality(
        week_start_date,
        weeks=FINALIZE_SIM_WEEKS,
        rerolls_per_week=FINALIZE_SIM_REROLLS,
    )
    summary = sim.get("summary") or {}
    failed_runs = int(summary.get("failed_runs") or 0)
    avg_score = float(summary.get("average_score") or 0.0)
    if failed_runs > 0:
        raise RuntimeError(
            f"No se puede finalizar: simulacion de estabilidad fallo ({failed_runs} corrida(s) fallida(s))."
        )
    if avg_score < FINALIZE_SIM_MIN_AVG_SCORE:
        raise RuntimeError(
            "No se puede finalizar: simulacion de estabilidad con score promedio "
            f"{avg_score:.2f}, minimo requerido {FINALIZE_SIM_MIN_AVG_SCORE:.2f}."
        )


@contextmanager
def _simulation_db_copy():
    """
    Run stress tests against a throwaway copy of the current DB.
    """
    db_module.bootstrap_db()
    source_db = Path(db_module.DB_PATH)
    tmpdir = Path(tempfile.mkdtemp(prefix="menu_restaurante_sim_"))
    sim_db = tmpdir / source_db.name
    shutil.copyfile(source_db, sim_db)

    original_db_path = db_module.DB_PATH
    db_module.DB_PATH = sim_db
    try:
        db_module.bootstrap_db()
        yield sim_db
    finally:
        db_module.DB_PATH = original_db_path
        try:
            db_module._BOOTSTRAPPED_DB_PATHS.discard(str(sim_db.resolve()))
        except Exception:
            pass
        shutil.rmtree(tmpdir, ignore_errors=True)


def _enforce_fixed_slots_for_week(conn, week_id: int) -> None:
    """
    Blindaje post-generaciÃ³n (capa service, antes de UI/PDF):
    - Arroz (L-V): siempre dish_id = ARROZ_FIXED_ID.
    - SÃ¡bado no tiene slot 'arroz' (por diseÃ±o de slots), asÃ­ que no toca sÃ¡bado.
    - Deja trazabilidad en was_exception/exception_reason/explanation si hubo correcciÃ³n.
    """
    rows = conn.execute(
        """
        SELECT id, dish_id, explanation
        FROM menu_item
        WHERE menu_week_id = ?
          AND slot = 'arroz'
          AND dish_id != ?
        """,
        (int(week_id), int(ARROZ_FIXED_ID)),
    ).fetchall()

    if not rows:
        return

    suffix = "Arroz es fijo por regla (L-V)."

    for r in rows:
        item_id = int(r["id"])
        old_id = int(r["dish_id"])
        old_exp = r["explanation"] or ""

        # Evita duplicar la leyenda si ya existe
        if suffix in old_exp:
            new_exp = old_exp
        else:
            new_exp = (old_exp + " | " + suffix).strip(" |")

        conn.execute(
            """
            UPDATE menu_item
            SET dish_id = ?,
                was_exception = 1,
                exception_reason = ?,
                explanation = ?
            WHERE id = ?
            """,
            (
                int(ARROZ_FIXED_ID),
                f"ARROZ_FIXED_GUARDRAIL: overwrote dish_id {old_id} -> {ARROZ_FIXED_ID}",
                new_exp,
                item_id,
            ),
        )


# -------------------------
# Helpers DB
# -------------------------
def _get_week_row(conn, week_start: date):
    return conn.execute(
        "SELECT id, week_start_date, generated_at, finalized, notes FROM menu_week WHERE week_start_date=?",
        (to_yyyy_mm_dd(week_start),),
    ).fetchone()


def _get_or_create_week_id(conn, week_start: date) -> int:
    """
    Asegura que exista menu_week; si no existe lo crea (sin generar items).
    """
    w = _get_week_row(conn, week_start)
    if w:
        return int(w["id"])

    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO menu_week(week_start_date, generated_at, finalized, notes)
        VALUES (?, ?, 0, NULL)
        """,
        (to_yyyy_mm_dd(week_start), now),
    )
    w2 = _get_week_row(conn, week_start)
    if not w2:
        raise RuntimeError("No se pudo crear menu_week (verifica DB/schema).")
    return int(w2["id"])


def _ensure_week_editable(conn, week_start: date) -> tuple[int, dict]:
    """
    Devuelve (week_id, week_row_dict). Lanza error si no existe o estÃ¡ finalizada.
    """
    w = _get_week_row(conn, week_start)
    if not w:
        raise RuntimeError("No existe un menÃº generado para esa semana.")
    if int(w["finalized"] or 0) == 1:
        raise RuntimeError("La semana estÃ¡ finalizada. ReÃ¡brela antes de hacer cambios.")
    return int(w["id"]), dict(w)


def _ensure_week_exists_and_editable(conn, week_start: date) -> tuple[int, dict]:
    """
    Garantiza existencia de menu_week y que sea editable.
    Ãštil para aplicar overrides aunque aÃºn no hayan generado la semana.
    """
    w = _get_week_row(conn, week_start)
    if w and int(w["finalized"] or 0) == 1:
        raise RuntimeError("La semana estÃ¡ finalizada. ReÃ¡brela antes de hacer cambios.")

    week_id = _get_or_create_week_id(conn, week_start)
    w2 = _get_week_row(conn, week_start)
    if not w2:
        raise RuntimeError("No se pudo leer menu_week despuÃ©s de asegurar existencia.")
    if int(w2["finalized"] or 0) == 1:
        raise RuntimeError("La semana estÃ¡ finalizada. ReÃ¡brela antes de hacer cambios.")
    return int(week_id), dict(w2)


def _validate_menu_date_in_week(week_start: date, day: date) -> None:
    if ensure_monday(day) != week_start:
        raise RuntimeError("La fecha no pertenece a la semana seleccionada.")
    if day.weekday() not in range(6):
        raise RuntimeError("Solo se pueden cerrar dias de lunes a sabado.")


def _closed_dates_for_week(conn, week_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT menu_date FROM menu_closed_day WHERE menu_week_id=? ORDER BY menu_date",
        (int(week_id),),
    ).fetchall()
    return [str(r["menu_date"]) for r in rows]


def _apply_closed_days(conn, week_id: int) -> None:
    for menu_date in _closed_dates_for_week(conn, int(week_id)):
        clear_day_items(conn, int(week_id), parse_yyyy_mm_dd(menu_date))


def _is_closed_day(conn, week_id: int, menu_date: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM menu_closed_day
        WHERE menu_week_id=? AND menu_date=?
        """,
        (int(week_id), str(menu_date)),
    ).fetchone()
    return bool(row)


def _sync_salad_mirror_if_anchor_day(conn, week_id: int, day: date) -> None:
    """
    If `day` is the anchor day for a weekly salad slot, copy the new anchor pick
    into its linked mirror day so the pair stays consistent without regenerating
    the whole week.
    """
    weekday = day.weekday()
    week_start = ensure_monday(day)
    day_str = to_yyyy_mm_dd(day)

    for slot in SALAD_SLOTS:
        if SALAD_ANCHOR_OFFSET[slot] != weekday:
            continue

        row = conn.execute(
            """
            SELECT dish_id, is_forced, was_exception, exception_reason, explanation
            FROM menu_item
            WHERE menu_week_id=? AND menu_date=? AND slot=?
            """,
            (int(week_id), day_str, slot),
        ).fetchone()
        if not row:
            continue

        for offset in SALAD_DAYS_BY_SLOT[slot]:
            mirror_day = week_start + timedelta(days=offset)
            mirror_str = to_yyyy_mm_dd(mirror_day)
            if mirror_str == day_str:
                continue
            if _is_closed_day(conn, week_id, mirror_str):
                continue
            conn.execute(
                """
                INSERT OR REPLACE INTO menu_item(
                    menu_week_id, menu_date, slot, dish_id,
                    is_forced, was_exception, exception_reason, explanation
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(week_id),
                    mirror_str,
                    slot,
                    int(row["dish_id"]),
                    int(row["is_forced"] or 0),
                    int(row["was_exception"] or 0),
                    row["exception_reason"],
                    row["explanation"],
                ),
            )


# -------------------------
# Ensaladas semanales (Lâ†”J, Mâ†”V, Xâ†”S)
# -------------------------
SALAD_SLOTS = {"ensalada_A", "ensalada_B", "ensalada_C"}


def _linked_salad_dates(menu_date: str, slot: str) -> list[str]:
    """
    Regresa las fechas (yyyy-mm-dd) que deben quedar sincronizadas para ese slot.
    - ensalada_A: lunes y jueves
    - ensalada_B: martes y viernes
    - ensalada_C: miÃ©rcoles y sÃ¡bado
    Si no es ensalada, regresa [menu_date].
    """
    if slot not in SALAD_SLOTS:
        return [menu_date]

    d = parse_yyyy_mm_dd(menu_date)
    week_start = ensure_monday(d)

    mapping = {
        "ensalada_A": [week_start + timedelta(days=0), week_start + timedelta(days=3)],
        "ensalada_B": [week_start + timedelta(days=1), week_start + timedelta(days=4)],
        "ensalada_C": [week_start + timedelta(days=2), week_start + timedelta(days=5)],
    }
    return [to_yyyy_mm_dd(x) for x in mapping[slot]]


# -------------------------
# API para UI / scripts
# -------------------------
def _generate_week_with_retries(
    week_start_date: str,
    *,
    exclude_week_id_for_rotation: Optional[int],
    action_label: str,
    deterministic_first_seed: Optional[str],
) -> int:
    """
    Generate/re-generate week with retries until strict audit passes.
    """
    last_error: Optional[Exception] = None
    for attempt in range(1, GENERATION_MAX_ATTEMPTS + 1):
        seed = deterministic_first_seed if attempt == 1 else datetime.now().isoformat(timespec="seconds")
        week_id = _generate_week(
            week_start_date,
            exclude_week_id_for_rotation=exclude_week_id_for_rotation,
            rng_seed=seed,
        )

        with get_conn() as conn:
            _enforce_fixed_slots_for_week(conn, int(week_id))
            _apply_closed_days(conn, int(week_id))
            conn.commit()

        try:
            _raise_if_audit_has_errors(week_start_date, action=f"{action_label} (intento {attempt})")
            return int(week_id)
        except RuntimeError as exc:
            last_error = exc

    if last_error:
        raise RuntimeError(
            f"{action_label}: no se pudo generar una semana valida en {GENERATION_MAX_ATTEMPTS} intentos. "
            f"Ultimo error: {last_error}"
        )
    raise RuntimeError(f"{action_label}: error inesperado al generar semana.")


def generate_week(week_start_date: str) -> int:
    """
    Genera una semana completa (modo normal/determinista).
    Aplica guardrails post-generaciÃ³n para slots fijos (ej: arroz).
    """
    return _generate_week_with_retries(
        week_start_date,
        exclude_week_id_for_rotation=None,
        action_label="Semana generada con errores",
        deterministic_first_seed=None,
    )


def regenerate_week(week_start_date: str) -> int:
    """
    Regenera la semana completa SIN contaminar rotaciÃ³n:
    ignora los items de esa misma semana al calcular ventanas de repeticiÃ³n.
    Aplica guardrails post-generaciÃ³n para slots fijos (ej: arroz).
    """
    week_start = ensure_monday(parse_yyyy_mm_dd(week_start_date))

    with get_conn() as conn:
        w = _get_week_row(conn, week_start)
        if w and int(w["finalized"] or 0) == 1:
            raise RuntimeError("La semana estÃ¡ finalizada. ReÃ¡brela antes de regenerar.")
        week_id = _get_or_create_week_id(conn, week_start)

    week_id2 = _generate_week_with_retries(
        to_yyyy_mm_dd(week_start),
        exclude_week_id_for_rotation=int(week_id),
        action_label="Semana regenerada con errores",
        deterministic_first_seed=datetime.now().isoformat(timespec="seconds"),
    )
    return int(week_id2)


def regenerate_day(week_start_date: str, menu_date: str) -> int:
    """
    Regenera solo un día de la semana sin tocar el resto.

    Notas:
    - Respeta overrides y reglas de slots fijos.
    - Si el día es ancla de una ensalada semanal, sincroniza únicamente su día espejo.
    - No permite regenerar días cerrados o semanas finalizadas.
    """
    week_start = ensure_monday(parse_yyyy_mm_dd(week_start_date))
    day = parse_yyyy_mm_dd(menu_date)
    _validate_menu_date_in_week(week_start, day)

    with get_conn() as conn:
        week_id, _ = _ensure_week_editable(conn, week_start)
        if _is_closed_day(conn, int(week_id), to_yyyy_mm_dd(day)):
            raise RuntimeError("El día está cerrado. Reábrelo antes de regenerarlo.")

        rng = random.Random(datetime.now().isoformat(timespec="seconds"))
        recompute_day(
            conn,
            int(week_id),
            day,
            rng,
            exclude_week_id_for_rotation=int(week_id),
        )
        _sync_salad_mirror_if_anchor_day(conn, int(week_id), day)
        conn.commit()

    return int(week_id)


def list_week(week_start_date: str) -> dict[str, Any]:
    """
    Devuelve:
    - week meta (id, week_start_date, generated_at, finalized, notes)
    - rows: lista de MenuRow para mostrar en UI
    """
    week_start = ensure_monday(parse_yyyy_mm_dd(week_start_date))

    with get_conn() as conn:
        w = _get_week_row(conn, week_start)
        if not w:
            return {"week": None, "rows": []}

        rows = conn.execute(
            """
            SELECT
                mi.menu_date, mi.slot, mi.dish_id,
                mi.is_forced, mi.was_exception, mi.exception_reason, mi.explanation,
                d.name AS dish_name, d.course_group, d.protein, d.style_tag
            FROM menu_item mi
            JOIN dish d ON d.id = mi.dish_id
            WHERE mi.menu_week_id = ?
            ORDER BY date(mi.menu_date), mi.slot
            """,
            (int(w["id"]),),
        ).fetchall()
        closed_dates = _closed_dates_for_week(conn, int(w["id"]))

    return {"week": dict(w), "rows": [MenuRow(**dict(r)) for r in rows], "closed_dates": closed_dates}


def get_week_diagnostics(week_start_date: str) -> dict[str, Any]:
    """
    Return per-slot diagnostics explaining why each dish was selected.
    """
    week_start = ensure_monday(parse_yyyy_mm_dd(week_start_date))
    return selection_diagnostics(to_yyyy_mm_dd(week_start))


def simulate_generation_quality(
    week_start_date: str,
    *,
    weeks: int = 8,
    rerolls_per_week: int = 2,
) -> dict[str, Any]:
    """
    Generate weeks against a disposable DB copy and summarize quality.

    This does not touch the production DB file.
    """
    if weeks <= 0:
        raise ValueError("weeks debe ser mayor a 0.")
    if rerolls_per_week <= 0:
        raise ValueError("rerolls_per_week debe ser mayor a 0.")

    start = ensure_monday(parse_yyyy_mm_dd(week_start_date))
    effective_start = start
    skipped_historical_weeks = 0
    if _past_weeks_write_lock_enabled() and _is_past_week_start(start):
        current_week = _current_operational_week_start()
        delta_days = (current_week - start).days
        skipped_historical_weeks = max(0, delta_days // 7)
        effective_start = current_week
    runs: list[dict[str, Any]] = []

    with _simulation_db_copy():
        for week_offset in range(weeks):
            current_week = effective_start + timedelta(days=7 * week_offset)
            current_week_str = to_yyyy_mm_dd(current_week)

            for attempt in range(rerolls_per_week):
                try:
                    if attempt == 0:
                        generate_week(current_week_str)
                    else:
                        regenerate_week(current_week_str)

                    audit = strict_audit_week(current_week_str)
                    report = week_report(current_week_str)
                    runs.append(
                        {
                            "week_start": current_week_str,
                            "attempt": attempt + 1,
                            "status": "ok",
                            "score": int(audit.get("score") or 0),
                            "error_count": len(audit.get("errors") or []),
                            "warning_count": len(audit.get("warnings") or []),
                            "exception_count": int(audit.get("totals", {}).get("exceptions", 0)),
                            "exceptions": list(report.get("exceptions") or []),
                        }
                    )
                except Exception as exc:
                    runs.append(
                        {
                            "week_start": current_week_str,
                            "attempt": attempt + 1,
                            "status": "failed",
                            "error": str(exc),
                            "exceptions": [],
                        }
                    )

    return {
        "week_start": to_yyyy_mm_dd(start),
        "effective_week_start": to_yyyy_mm_dd(effective_start),
        "skipped_historical_weeks": skipped_historical_weeks,
        "weeks": weeks,
        "rerolls_per_week": rerolls_per_week,
        "runs": runs,
        "summary": summarize_simulation_runs(runs),
    }


def clear_week(week_start_date: str) -> None:
    """
    Borra items de la semana (L-S) pero deja el registro menu_week.
    """
    week_start = ensure_monday(parse_yyyy_mm_dd(week_start_date))
    with get_conn() as conn:
        week_id = _get_or_create_week_id(conn, week_start)
        conn.execute("DELETE FROM menu_item WHERE menu_week_id=?", (int(week_id),))
        conn.commit()


def close_day(week_start_date: str, menu_date: str, *, reason: Optional[str] = None) -> None:
    """
    Marca un dia como cerrado dentro de la semana:
    - borra sus menu_item para que no cuenten como usados
    - borra overrides de ese dia
    - persiste el cierre para que futuras regeneraciones lo respeten
    """
    week_start = ensure_monday(parse_yyyy_mm_dd(week_start_date))
    day = parse_yyyy_mm_dd(menu_date)
    _validate_menu_date_in_week(week_start, day)

    with get_conn() as conn:
        week_id, _ = _ensure_week_editable(conn, week_start)
        conn.execute(
            """
            INSERT INTO menu_closed_day(menu_week_id, menu_date, reason)
            VALUES (?, ?, ?)
            ON CONFLICT(menu_week_id, menu_date) DO UPDATE SET reason=excluded.reason
            """,
            (int(week_id), to_yyyy_mm_dd(day), reason),
        )
        clear_day_items(conn, int(week_id), day)
        conn.execute("DELETE FROM menu_override WHERE menu_date=?", (to_yyyy_mm_dd(day),))
        conn.commit()


def set_override(
    menu_date: str,
    slot: str,
    *,
    forced_dish_id: Optional[int] = None,
    blocked_dish_id: Optional[int] = None,
    note: Optional[str] = None,
) -> None:
    """
    Crea/actualiza override.
    - Para ensaladas semanales, aplica a los dos dÃ­as vinculados.
    - No permite forced y blocked simultÃ¡neamente.
    """
    # Arroz es slot fijo (L-V) y NO admite overrides por regla del sistema.
    if slot == "arroz":
        raise ValueError("El slot 'arroz' es fijo (Arroz al gusto) y no admite overrides.")

    if forced_dish_id is None and blocked_dish_id is None and not note:
        raise ValueError("Debes mandar forced_dish_id y/o blocked_dish_id y/o note.")

    if forced_dish_id is not None and blocked_dish_id is not None:
        raise ValueError("No puedes forzar y bloquear al mismo tiempo en el mismo slot.")

    # Validar que el slot existe para ese dÃ­a (ensaladas usan anchor day)
    day = parse_yyyy_mm_dd(menu_date)
    _day_for_slot_check = day
    if slot in SALAD_SLOTS:
        week_start_check = ensure_monday(day)
        salad_anchor_offsets = {"ensalada_A": 0, "ensalada_B": 1, "ensalada_C": 2}
        _day_for_slot_check = week_start_check + timedelta(days=salad_anchor_offsets[slot])
    valid_slots = slots_for_day(_day_for_slot_check)
    if slot not in valid_slots:
        raise ValueError(
            f"El slot '{slot}' no es vÃ¡lido para el dÃ­a {menu_date} "
            f"({_day_for_slot_check.strftime('%A')})."
        )

    # Validar que forced_dish_id es un platillo activo
    if forced_dish_id is not None:
        with get_conn() as _conn:
            if not dish_is_active(_conn, forced_dish_id):
                raise ValueError(
                    f"El platillo con id={forced_dish_id} no existe o estÃ¡ inactivo."
                )
            if slot == "molcajete":
                row = _conn.execute(
                    """
                    SELECT d.protein,
                           EXISTS(
                               SELECT 1
                               FROM dish_tag t
                               WHERE t.dish_id = d.id AND t.tag = 'monday_molcajete'
                           ) AS has_tag
                    FROM dish d
                    WHERE d.id = ?
                    """,
                    (int(forced_dish_id),),
                ).fetchone()
                if not row:
                    raise ValueError(f"No existe dish_id={forced_dish_id}.")
                if str(row["protein"] or "none") == "none":
                    raise ValueError(
                        "Override invalido para molcajete: el platillo debe tener protein definida."
                    )
                if int(row["has_tag"] or 0) != 1:
                    raise ValueError(
                        "Override invalido para molcajete: el platillo debe tener tag monday_molcajete."
                    )

    targets = _linked_salad_dates(menu_date, slot)

    with get_conn() as conn:
        # asegura que exista semana editable (si todavÃ­a no han generado)
        day = parse_yyyy_mm_dd(menu_date)
        week_start = ensure_monday(day)
        _ensure_week_exists_and_editable(conn, week_start)

        for target_date in targets:
            existing = conn.execute(
                "SELECT id FROM menu_override WHERE menu_date=? AND slot=?",
                (target_date, slot),
            ).fetchone()

            if existing:
                conn.execute(
                    """
                    UPDATE menu_override
                    SET forced_dish_id=?,
                        blocked_dish_id=?,
                        note=?
                    WHERE menu_date=? AND slot=?
                    """,
                    (forced_dish_id, blocked_dish_id, note, target_date, slot),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO menu_override(menu_date, slot, forced_dish_id, blocked_dish_id, note)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (target_date, slot, forced_dish_id, blocked_dish_id, note),
                )

        conn.commit()


def clear_week_forced_overrides(week_start_date: str) -> list[tuple[str, str]]:
    """
    Elimina todos los overrides con forced_dish_id de la semana (lun-sÃ¡b).
    Devuelve lista de (menu_date, slot) afectados para que el llamador
    pueda recomputar esos slots vÃ­a apply_override_now.
    """
    week_start = ensure_monday(parse_yyyy_mm_dd(week_start_date))
    dates = [to_yyyy_mm_dd(week_start + timedelta(days=i)) for i in range(6)]
    placeholders = ",".join(["?"] * 6)

    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT menu_date, slot FROM menu_override "
            f"WHERE forced_dish_id IS NOT NULL AND menu_date IN ({placeholders})",
            dates,
        ).fetchall()
        affected = [(r["menu_date"], r["slot"]) for r in rows]

        conn.execute(
            f"DELETE FROM menu_override WHERE forced_dish_id IS NOT NULL AND menu_date IN ({placeholders})",
            dates,
        )
        conn.commit()

    return affected


def remove_override(menu_date: str, slot: str) -> None:
    """
    Borra override.
    - Para ensaladas semanales, borra tambiÃ©n el dÃ­a vinculado.
    """
    targets = _linked_salad_dates(menu_date, slot)

    with get_conn() as conn:
        day = parse_yyyy_mm_dd(menu_date)
        week_start = ensure_monday(day)
        _ensure_week_exists_and_editable(conn, week_start)

        for target_date in targets:
            conn.execute(
                "DELETE FROM menu_override WHERE menu_date=? AND slot=?",
                (target_date, slot),
            )
        conn.commit()


def apply_override_now(menu_date: str, slot: str) -> None:
    """
    Aplica inmediatamente el efecto del override en la semana.

    - No requiere presionar "Regenerar"
    - Respeta finalized
    - RNG determinista por semana para cambios parciales estables
    - Molcajete lunes: recalcula el dÃ­a completo
    - Ensaladas: NO se manejan aquÃ­; generator.recompute_slot() debe encargarse
      de la lÃ³gica semanal (dÃ­a ancla/dÃ­a espejo).
    """
    if slot == "arroz":
        raise ValueError("El slot 'arroz' es fijo (Arroz al gusto) y no admite overrides.")

    day = parse_yyyy_mm_dd(menu_date)
    week_start = ensure_monday(day)

    with get_conn() as conn:
        week_id, _w = _ensure_week_exists_and_editable(conn, week_start)
        rng = random.Random(to_yyyy_mm_dd(week_start))

        if slot == "molcajete" and day.weekday() == 0:
            recompute_day(conn, int(week_id), day, rng, exclude_week_id_for_rotation=None)
        else:
            recompute_slot(conn, int(week_id), day, slot, rng, exclude_week_id_for_rotation=None)

        conn.commit()


def reconcile_menu_for_catalog_change(dish_id: int) -> dict[str, Any]:
    """
    Recompute affected menu slots when a catalog dish changes.

    Finalized weeks are never modified.
    """
    dish_id = int(dish_id)
    affected_slots: list[dict[str, Any]] = []
    affected_days: list[dict[str, Any]] = []
    skipped_finalized: list[str] = []
    skipped_past: list[str] = []
    updated: list[str] = []
    seen_day_recompute: set[tuple[int, str]] = set()

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT
                mw.id AS week_id,
                mw.week_start_date,
                mw.finalized,
                mi.menu_date,
                mi.slot
            FROM menu_item mi
            JOIN menu_week mw ON mw.id = mi.menu_week_id
            WHERE mi.dish_id = ?
            ORDER BY mw.week_start_date, mi.menu_date, mi.slot
            """,
            (dish_id,),
        ).fetchall()

        for row in rows:
            week_start = str(row["week_start_date"])
            week_id = int(row["week_id"])
            menu_date = str(row["menu_date"])
            slot = str(row["slot"])
            if int(row["finalized"] or 0) == 1:
                skipped_finalized.append(week_start)
                continue
            if _past_weeks_write_lock_enabled() and _is_past_week_start(parse_yyyy_mm_dd(week_start)):
                skipped_past.append(week_start)
                continue

            rng = random.Random(week_start)
            day_key = (week_id, menu_date)
            day_date = parse_yyyy_mm_dd(menu_date)

            # Molcajete affects Monday structure; recompute full day.
            if slot == "molcajete":
                if day_key not in seen_day_recompute:
                    recompute_day(
                        conn,
                        week_id,
                        day_date,
                        rng,
                        exclude_week_id_for_rotation=None,
                    )
                    seen_day_recompute.add(day_key)
                    affected_days.append(
                        {
                            "week_id": week_id,
                            "week_start_date": week_start,
                            "menu_date": menu_date,
                        }
                    )
            else:
                # If the day was already recomputed (e.g. by molcajete), skip slot-level.
                if day_key in seen_day_recompute:
                    continue
                recompute_slot(
                    conn,
                    week_id,
                    day_date,
                    slot,
                    rng,
                    exclude_week_id_for_rotation=None,
                )
                affected_slots.append(
                    {
                        "week_id": week_id,
                        "week_start_date": week_start,
                        "menu_date": menu_date,
                        "slot": slot,
                    }
                )

            updated.append(week_start)

        conn.commit()

    updated_weeks = sorted(set(updated))
    skipped_weeks = sorted(set(skipped_finalized))
    skipped_past_weeks = sorted(set(skipped_past))
    return {
        "dish_id": dish_id,
        "affected_count": len(affected_slots) + len(affected_days),
        "affected_slots_count": len(affected_slots),
        "affected_days_count": len(affected_days),
        "affected_slots": affected_slots,
        "affected_days": affected_days,
        "updated_weeks": updated_weeks,
        "skipped_finalized_weeks": skipped_weeks,
        "skipped_past_weeks": skipped_past_weeks,
    }


def reconcile_molcajete_weeks_for_dish(dish_id: int) -> dict[str, Any]:
    """
    Backward-compatible alias retained for existing callers.
    """
    return reconcile_menu_for_catalog_change(dish_id)


# -------------------------
# Export PDF / CSV
# -------------------------
WEEKDAY_NAME = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

SECTION_ORDER = [
    "Entradas",
    "Sopas / Cremas / Pastas",
    "Arroz y Ensalada",
    "Platos fuertes",
    "Otros",
]

SLOT_ORDER = [
    "entrada_comal",
    "entrada_no_comal",
    "pancita",
    "sopa",
    "sopa_pollo",
    "crema",
    "pasta",
    "arroz",
    "ensalada_A",
    "ensalada_B",
    "ensalada_C",
    "molcajete",
    "fuerte_res",
    "fuerte_pollo",
    "fuerte_cerdo",
    "chamorro",
    "fuerte_pescado",
    "fuerte_camaron",
    "complemento",
    "paella",
    "pescado_al_gusto",
    "camaron_al_gusto",
    "nuggets",
    "enchiladas",
]


def _sort_key_slot(slot: str) -> int:
    return SLOT_ORDER.index(slot) if slot in SLOT_ORDER else 999


def _section_for_slot(slot: str, weekday: int) -> str:
    if slot in ("entrada_comal", "entrada_no_comal"):
        return "Entradas"
    if weekday == 5 and slot == "pasta":
        return "Arroz y Ensalada"
    if slot in ("sopa", "crema", "pasta", "pancita", "sopa_pollo"):
        return "Sopas / Cremas / Pastas"
    if slot in ("arroz", "ensalada_A", "ensalada_B", "ensalada_C"):
        return "Arroz y Ensalada"
    if slot in (
        "fuerte_res",
        "fuerte_pollo",
        "fuerte_cerdo",
        "fuerte_pescado",
        "fuerte_camaron",
        "complemento",
        "molcajete",
        "chamorro",
        "paella",
        "pescado_al_gusto",
        "camaron_al_gusto",
        "nuggets",
        "enchiladas",
    ):
        return "Platos fuertes"
    return "Otros"


def _pdf_section_title(section_key: str, weekday: int) -> str:
    """
    Ajusta el nombre de las secciones en el PDF según reglas de impresión.
    weekday: Monday=0 ... Saturday=5
    """
    if section_key == "Entradas":
        return "Entradas"

    if section_key == "Sopas / Cremas / Pastas":
        if weekday == 5:
            return "Sopa"
        return "Sopas & Cremas"

    if section_key == "Arroz y Ensalada":
        if weekday == 5:
            return "Pasta & Ensalada"
        return "Arroz & Ensalada"

    if section_key == "Platos fuertes":
        return "Platos Fuertes"

    return section_key


def export_week_pdf(week_start_date: str, out_path: str | Path) -> str:
    """
    PDF imprimible en UNA hoja (landscape), columnas por día (Lun-Sáb),
    con auto-ajuste de tipografía para que siempre quepa.
    """
    try:
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except Exception as e:
        raise RuntimeError("Falta dependencia para PDF. Instala: pip install reportlab") from e

    data = list_week(week_start_date)
    week = data.get("week")
    rows: list[MenuRow] = data.get("rows", [])
    if not week:
        raise RuntimeError("No existe un menú generado para esa semana.")

    week_start = ensure_monday(parse_yyyy_mm_dd(week_start_date))
    week_end = week_start + timedelta(days=5)

    out_path = str(out_path)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    by_day: dict[str, list[MenuRow]] = {}
    for r in rows:
        by_day.setdefault(r.menu_date, []).append(r)

    days = [week_start + timedelta(days=i) for i in range(6)]  # L-S

    def build_day_lines(d: date) -> list[str]:
        ds = to_yyyy_mm_dd(d)
        wd = d.weekday()
        day_rows = by_day.get(ds, [])

        lines: list[str] = []
        lines.append(f"<b>{WEEKDAY_NAME[wd]}</b>")
        lines.append(ds)
        lines.append("")

        if not day_rows:
            lines.append("Sin items.")
            return lines

        sections: dict[str, list[MenuRow]] = {}
        for rr in day_rows:
            sec = _section_for_slot(rr.slot, weekday=wd)
            sections.setdefault(sec, []).append(rr)

        for sec in SECTION_ORDER:
            sec_rows = sections.get(sec, [])
            if not sec_rows:
                continue

            sec_title = _pdf_section_title(sec, wd)
            lines.append(f"<b>{sec_title}</b>")

            sec_rows = sorted(sec_rows, key=lambda x: _sort_key_slot(x.slot))

            import re as _re
            for rr in sec_rows:
                if rr.slot == "nuggets":
                    dish_txt = "Nuggets de pollo con papas"
                elif rr.slot in ("pancita", "paella"):
                    # Strip any parenthetical suffix — show only the base name
                    dish_txt = _re.sub(r"\s*\([^)]*\)", "", rr.dish_name).strip()
                else:
                    dish_txt = rr.dish_name
                lines.append(f"- {dish_txt}")

            lines.append("")

        return lines

    day_lines = [build_day_lines(d) for d in days]
    max_lines = max(len(lines) for lines in day_lines) if day_lines else 1

    doc = SimpleDocTemplate(
        out_path,
        pagesize=landscape(letter),
        leftMargin=0.35 * inch,
        rightMargin=0.35 * inch,
        topMargin=0.40 * inch,
        bottomMargin=0.40 * inch,
        title="Menu semanal",
        author="Menu Restaurante",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=8,
    )

    page_w, page_h = doc.pagesize
    available_h = page_h - doc.topMargin - doc.bottomMargin

    reserved_h = 16 + 4 + 9 + 8 + 6
    content_h = max(available_h - reserved_h, 200)

    BASE_FONT = 8.6
    MIN_FONT = 6.8

    def leading_for(fs: float) -> float:
        return fs + 2.2

    fs = BASE_FONT
    while fs >= MIN_FONT:
        lead = leading_for(fs)
        required_h = max_lines * lead
        if required_h <= content_h:
            break
        fs -= 0.2

    if fs < MIN_FONT:
        fs = MIN_FONT

    item_style = ParagraphStyle(
        "Item",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=fs,
        leading=leading_for(fs),
        spaceAfter=0,
    )

    def lines_to_paragraph(lines: list[str]) -> Paragraph:
        html = "<br/>".join(lines)
        return Paragraph(html, item_style)

    col_paragraphs = [lines_to_paragraph(lines) for lines in day_lines]

    available_width = page_w - doc.leftMargin - doc.rightMargin
    col_w = available_width / 6.0
    col_widths = [col_w] * 6

    story = []
    story.append(Paragraph("Menú semanal", title_style))
    story.append(Paragraph(f"Semana: {to_yyyy_mm_dd(week_start)} a {to_yyyy_mm_dd(week_end)}", meta_style))
    story.append(Spacer(1, 6))

    t = Table([col_paragraphs], colWidths=col_widths)
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBEFORE", (1, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(t)
    doc.build(story)
    return out_path


def export_week_csv(week_start_date: str, out_path: str | Path) -> str:
    data = list_week(week_start_date)
    rows: list[MenuRow] = data["rows"]

    out_path = str(out_path)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "menu_date",
                "slot",
                "dish_id",
                "dish_name",
                "course_group",
                "protein",
                "style_tag",
                "is_forced",
                "was_exception",
                "exception_reason",
                "explanation",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r.menu_date,
                    r.slot,
                    r.dish_id,
                    r.dish_name,
                    r.course_group,
                    r.protein,
                    r.style_tag,
                    r.is_forced,
                    r.was_exception,
                    r.exception_reason,
                    r.explanation,
                ]
            )
    return out_path


def finalize_week(
    week_start_date: str,
    finalized: bool = True,
    notes: Optional[str] = None,
    force: bool = False,
) -> list[str]:
    """Finalize (or unfinalize) a week. Returns a list of warnings (non-empty if quality checks failed but force=True)."""
    week_start = ensure_monday(parse_yyyy_mm_dd(week_start_date))
    warnings: list[str] = []
    if finalized:
        week_start_str = to_yyyy_mm_dd(week_start)
        try:
            audit = _raise_if_audit_has_errors(week_start_str, action="auditoria")
        except RuntimeError as e:
            if not force:
                raise
            warnings.append(str(e))
            audit = {}
        try:
            _raise_if_finalization_quality_gate_fails(week_start_str, audit)
        except RuntimeError as e:
            if not force:
                raise
            warnings.append(str(e))
    with get_conn() as conn:
        week_id = _get_or_create_week_id(conn, week_start)
        conn.execute(
            "UPDATE menu_week SET finalized=?, notes=? WHERE id=?",
            (1 if finalized else 0, notes, int(week_id)),
        )
        conn.commit()
    return warnings
