"""
src/engine/report.py

Post-generation quality report for a weekly menu.
Returns a structured dict usable by any UI or CLI.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from src.db import get_conn
from src.engine.generator import (
    DISH_ID_ANTOJITOS_COMAL,
    DISH_ID_ARROZ_AL_GUSTO,
    STYLE_NUGGETS_FIJO,
    STYLE_PAELLA_FIJA,
    STYLE_PANCITA_FIJA,
    TAG_FRIDAY_CHAMORRO,
    TAG_MONDAY_MOLCAJETE,
    TAG_SAT_ENCHILADAS,
    TAG_ONLY_FRI,
    TAG_ONLY_SAT,
)
from src.engine.slots import slots_for_day

DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
SLOTS_ORDER = [
    "entrada_comal", "entrada_no_comal",
    "sopa", "crema", "pasta", "arroz",
    "ensalada_A", "ensalada_B", "ensalada_C",
    "molcajete",
    "fuerte_res", "fuerte_pollo", "fuerte_cerdo", "fuerte_pescado", "fuerte_camaron",
    "chamorro",
    "complemento",
    "pancita", "paella", "nuggets",
    "pescado_al_gusto", "camaron_al_gusto",
    "enchiladas", "sopa_pollo",
]

FIXED_STYLE_BY_SLOT = {
    "paella": STYLE_PAELLA_FIJA,
    "nuggets": STYLE_NUGGETS_FIJO,
    "pancita": STYLE_PANCITA_FIJA,
}

FIXED_SLOTS = {"entrada_comal", "arroz", "paella", "nuggets", "pancita"}
CATALOG_HEALTH_FIXED_SLOTS = FIXED_SLOTS | {"chamorro"}


def audit_week(week_start_date: str) -> dict[str, Any]:
    """
    Validate a generated week and return blocking errors + soft warnings.

    Blocking errors are intended to stop finalization.
    """
    with get_conn() as conn:
        week_row = conn.execute(
            "SELECT id, week_start_date, generated_at, finalized, notes FROM menu_week WHERE week_start_date=?",
            (week_start_date,),
        ).fetchone()
        if not week_row:
            return {"error": f"No existe menÃº para la semana {week_start_date}"}

        week_id = int(week_row["id"])
        items = [
            dict(r)
            for r in conn.execute(
                """
                SELECT
                    mi.menu_date,
                    mi.slot,
                    mi.dish_id,
                    mi.is_forced,
                    mi.was_exception,
                    mi.exception_reason,
                    d.name AS dish_name,
                    d.protein,
                    d.style_tag,
                    d.active
                FROM menu_item mi
                JOIN dish d ON d.id = mi.dish_id
                WHERE mi.menu_week_id = ?
                ORDER BY mi.menu_date, mi.slot
                """,
                (week_id,),
            ).fetchall()
        ]

        tag_rows = conn.execute(
            """
            SELECT mi.menu_date, mi.slot, mi.dish_id, dt.tag
            FROM menu_item mi
            JOIN dish_tag dt ON dt.dish_id = mi.dish_id
            WHERE mi.menu_week_id = ?
              AND dt.tag IN (?, ?, ?, ?, ?)
            """,
            (
                week_id,
                TAG_ONLY_FRI,
                TAG_ONLY_SAT,
                TAG_MONDAY_MOLCAJETE,
                TAG_FRIDAY_CHAMORRO,
                TAG_SAT_ENCHILADAS,
            ),
        ).fetchall()
        closed_dates = {
            str(r["menu_date"])
            for r in conn.execute(
                "SELECT menu_date FROM menu_closed_day WHERE menu_week_id=?",
                (week_id,),
            ).fetchall()
        }

    errors: list[str] = []
    warnings: list[str] = []

    if not items:
        return {
            "week_start": week_start_date,
            "week_id": week_id,
            "errors": ["La semana no tiene items generados."],
            "warnings": [],
            "score": 0,
            "totals": {"items": 0, "errors": 1, "warnings": 0},
        }

    items_by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        items_by_day[item["menu_date"]].append(item)
        if int(item["active"] or 0) != 1:
            errors.append(
                f"{item['menu_date']} slot={item['slot']} usa platillo inactivo: {item['dish_name']} (id={item['dish_id']})."
            )

        if item["slot"] == "entrada_comal" and int(item["dish_id"]) != DISH_ID_ANTOJITOS_COMAL:
            errors.append(
                f"{item['menu_date']} entrada_comal no es fijo: id={item['dish_id']} en vez de {DISH_ID_ANTOJITOS_COMAL}."
            )
        if item["slot"] == "arroz" and int(item["dish_id"]) != DISH_ID_ARROZ_AL_GUSTO:
            errors.append(
                f"{item['menu_date']} arroz no es fijo: id={item['dish_id']} en vez de {DISH_ID_ARROZ_AL_GUSTO}."
            )
        if item["slot"] in FIXED_STYLE_BY_SLOT:
            expected_style = FIXED_STYLE_BY_SLOT[item["slot"]]
            if item["style_tag"] != expected_style:
                errors.append(
                    f"{item['menu_date']} {item['slot']} no usa style_tag fijo '{expected_style}'."
                )

    day_only_tags_by_item = {(r["menu_date"], r["slot"], int(r["dish_id"]), str(r["tag"])) for r in tag_rows}
    for menu_date, slot, dish_id, tag in day_only_tags_by_item:
        weekday = date.fromisoformat(menu_date).weekday()
        if tag == TAG_ONLY_FRI and weekday != 4:
            errors.append(f"{menu_date} slot={slot} usa only_fri fuera de viernes (dish_id={dish_id}).")
        if tag == TAG_ONLY_SAT and weekday != 5:
            errors.append(f"{menu_date} slot={slot} usa only_sat fuera de sÃ¡bado (dish_id={dish_id}).")

    week_start = date.fromisoformat(week_start_date)
    for offset in range(6):
        day = week_start + timedelta(days=offset)
        menu_date = day.isoformat()
        if menu_date in closed_dates:
            continue
        actual_slots = {row["slot"] for row in items_by_day.get(menu_date, [])}
        expected_slots = set(slots_for_day(day))

        if day.weekday() == 0 and "molcajete" in actual_slots:
            mol_row = next((row for row in items_by_day[menu_date] if row["slot"] == "molcajete"), None)
            if mol_row and mol_row["protein"] and mol_row["protein"] != "none":
                expected_slots.discard(f"fuerte_{mol_row['protein']}")

        missing = sorted(expected_slots - actual_slots)
        extra = sorted(actual_slots - expected_slots)

        if missing:
            errors.append(f"{menu_date} tiene slots faltantes: {', '.join(missing)}.")
        if extra:
            errors.append(f"{menu_date} tiene slots inesperados: {', '.join(extra)}.")

    exception_count = sum(1 for item in items if int(item.get("was_exception") or 0) == 1)
    non_fixed_items = sum(1 for item in items if item["slot"] not in FIXED_SLOTS)
    forced_count = sum(
        1
        for item in items
        if int(item.get("is_forced") or 0) == 1 and item["slot"] not in {"entrada_comal", "arroz", "paella", "nuggets", "pancita"}
    )

    if exception_count:
        warnings.append(f"{exception_count} slot(s) quedaron marcados como excepciÃ³n.")
    if forced_count:
        warnings.append(f"{forced_count} slot(s) quedaron forzados manualmente.")

    score = max(0, 100 - len(errors) * 15 - len(warnings) * 3)
    return {
        "week_start": week_start_date,
        "week_id": week_id,
        "errors": errors,
        "warnings": warnings,
        "score": score,
        "totals": {
            "items": len(items),
            "non_fixed_items": non_fixed_items,
            "errors": len(errors),
            "warnings": len(warnings),
            "exceptions": exception_count,
            "forced_non_fixed": forced_count,
        },
    }


def strict_audit_week(week_start_date: str) -> dict[str, Any]:
    """
    Extended audit with stricter checks for owner-facing special rules.
    """
    audit = audit_week(week_start_date)
    if audit.get("error"):
        return audit

    errors = list(audit.get("errors") or [])
    warnings = list(audit.get("warnings") or [])

    with get_conn() as conn:
        week_row = conn.execute(
            "SELECT id FROM menu_week WHERE week_start_date=?",
            (week_start_date,),
        ).fetchone()
        if not week_row:
            return {"error": f"No existe menu para la semana {week_start_date}"}

        week_id = int(week_row["id"])
        rows = conn.execute(
            """
            SELECT
                mi.menu_date,
                mi.slot,
                mi.dish_id,
                mi.is_forced,
                d.name AS dish_name,
                d.protein,
                GROUP_CONCAT(dt.tag, '|') AS tags
            FROM menu_item mi
            JOIN dish d ON d.id = mi.dish_id
            LEFT JOIN dish_tag dt ON dt.dish_id = d.id
            WHERE mi.menu_week_id = ?
            GROUP BY mi.menu_date, mi.slot, mi.dish_id, mi.is_forced, d.name, d.protein
            ORDER BY mi.menu_date, mi.slot
            """,
            (week_id,),
        ).fetchall()

        beef_cut_rows = conn.execute(
            """
            SELECT
                mi.menu_date,
                mi.slot,
                mi.dish_id,
                d.name AS dish_name,
                bc.name AS beef_cut_name
            FROM menu_item mi
            JOIN dish d ON d.id = mi.dish_id
            JOIN dish_beef_cut dbc ON dbc.dish_id = mi.dish_id
            JOIN beef_cut bc ON bc.id = dbc.beef_cut_id
            WHERE mi.menu_week_id = ?
              AND mi.slot IN ('fuerte_res', 'molcajete')
            ORDER BY mi.menu_date, mi.slot, bc.name
            """,
            (week_id,),
        ).fetchall()

    exception_count = int(audit.get("totals", {}).get("exceptions", 0))
    non_fixed_items = int(audit.get("totals", {}).get("non_fixed_items", 0))
    if non_fixed_items and (exception_count / non_fixed_items) >= 0.20:
        warnings.append(
            f"La semana uso demasiadas excepciones ({exception_count}/{non_fixed_items})."
        )

    non_fixed_repeats: dict[int, list[tuple[str, str, str]]] = defaultdict(list)
    sauce_repeats: dict[str, list[tuple[str, str, str]]] = defaultdict(list)

    for row in rows:
        menu_date = str(row["menu_date"])
        slot = str(row["slot"])
        dish_id = int(row["dish_id"])
        tags = {tag for tag in str(row["tags"] or "").split("|") if tag}
        dish_name = str(row["dish_name"])

        if slot in FIXED_SLOTS and int(row["is_forced"] or 0) != 1:
            errors.append(f"{menu_date} {slot} debio guardarse como fijo/forzado.")
        if slot == "molcajete" and TAG_MONDAY_MOLCAJETE not in tags:
            errors.append(f"{menu_date} molcajete no usa tag monday_molcajete (dish_id={dish_id}).")
        if slot == "molcajete" and str(row["protein"] or "none") == "none":
            errors.append(f"{menu_date} molcajete sin protein definida (dish_id={dish_id}).")
        if slot == "chamorro" and TAG_FRIDAY_CHAMORRO not in tags:
            errors.append(f"{menu_date} chamorro no usa tag friday_chamorro (dish_id={dish_id}).")
        if slot == "enchiladas" and TAG_SAT_ENCHILADAS not in tags:
            errors.append(f"{menu_date} enchiladas no usa tag sat_enchiladas (dish_id={dish_id}).")

        if slot not in FIXED_SLOTS:
            non_fixed_repeats[dish_id].append((menu_date, slot, dish_name))

    with get_conn() as conn:
        sauce_rows = conn.execute(
            """
            SELECT mi.menu_date, mi.slot, d.name AS dish_name, d.sauce_tag
            FROM menu_item mi
            JOIN dish d ON d.id = mi.dish_id
            WHERE mi.menu_week_id = ?
              AND d.sauce_tag IS NOT NULL
              AND d.sauce_tag != ''
            ORDER BY mi.menu_date, mi.slot
            """,
            (week_id,),
        ).fetchall()

    for row in sauce_rows:
        slot = str(row["slot"])
        if slot in FIXED_SLOTS or slot.startswith("ensalada_"):
            continue
        sauce_repeats[str(row["sauce_tag"])].append(
            (str(row["menu_date"]), slot, str(row["dish_name"]))
        )

    for dish_id, usages in sorted(non_fixed_repeats.items(), key=lambda x: len(x[1]), reverse=True):
        if len(usages) <= 1:
            continue
        slots = {s for _, s, _ in usages}
        if len(slots) <= 1:
            # Repetition in the same slot can be unavoidable with small catalogs.
            continue
        if all(s.startswith("ensalada_") for s in slots) and len(slots) == 1:
            # Allowed weekly mirror pair (e.g. ensalada_A lunes/jueves).
            continue
        places = ", ".join(f"{d} {s}" for d, s, _ in usages[:4])
        warnings.append(
            f"Platillo repetido en semana (dish_id={dish_id}) {len(usages)} veces: {places}."
        )

    for sauce_tag, usages in sorted(sauce_repeats.items(), key=lambda x: len(x[1]), reverse=True):
        if len(usages) <= 1:
            continue
        places = ", ".join(f"{d} {s}" for d, s, _ in usages[:4])
        errors.append(
            f"Salsa repetida en semana ('{sauce_tag}') {len(usages)} veces: {places}."
        )

    beef_cut_usage: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for row in beef_cut_rows:
        menu_date = str(row["menu_date"])
        weekday = date.fromisoformat(menu_date).weekday()
        if weekday == 5:
            continue
        cut_name = str(row["beef_cut_name"])
        beef_cut_usage[cut_name].append((menu_date, str(row["slot"]), str(row["dish_name"])))

    for cut_name, usages in sorted(beef_cut_usage.items(), key=lambda x: len(x[1]), reverse=True):
        if len(usages) <= 1:
            continue
        places = ", ".join(f"{d} {s}" for d, s, _ in usages[:4])
        errors.append(
            f"Corte de res repetido en L-V ('{cut_name}') {len(usages)} veces: {places}."
        )

    dedup_errors = list(dict.fromkeys(errors))
    dedup_warnings = list(dict.fromkeys(warnings))
    score = max(0, 100 - len(dedup_errors) * 15 - len(dedup_warnings) * 3)
    totals = dict(audit.get("totals") or {})
    totals["errors"] = len(dedup_errors)
    totals["warnings"] = len(dedup_warnings)

    return {
        "week_start": audit["week_start"],
        "week_id": audit["week_id"],
        "errors": dedup_errors,
        "warnings": dedup_warnings,
        "score": score,
        "totals": totals,
    }


def week_report(week_start_date: str) -> dict[str, Any]:
    """
    Generate a quality report for a week.

    Returns:
        {
          "week_start": "YYYY-MM-DD",
          "days": [
            {
              "date": "YYYY-MM-DD",
              "day_name": "Lunes",
              "slots": [{"slot": str, "dish": str, "protein": str,
                          "sauce_tag": str|None, "is_forced": bool,
                          "was_exception": bool, "exception_reason": str|None}]
            }, ...
          ],
          "sauces_used": ["salsa_chipotle", ...],          # all sauce_tags this week
          "proteins_by_day": {"2026-03-16": {"res": 2, "pollo": 1, ...}},
          "exceptions": [{"date", "slot", "reason", "dish"}],
          "warnings": ["..."],   # soft issues
          "score": int,          # 0-100 quality score
          "totals": {"dishes": int, "with_sauce_tag": int, "exceptions": int}
        }
    """
    with get_conn() as conn:
        # Find week_id
        row = conn.execute(
            "SELECT id FROM menu_week WHERE week_start_date=?", (week_start_date,)
        ).fetchone()
        if not row:
            return {"error": f"No existe menú para la semana {week_start_date}"}
        week_id = int(row["id"])

        items = conn.execute(
            """
            SELECT mi.menu_date, mi.slot, d.name AS dish_name,
                   d.protein, d.sauce_tag, d.course_group,
                   mi.is_forced, mi.was_exception, mi.exception_reason
            FROM menu_item mi
            JOIN dish d ON d.id = mi.dish_id
            WHERE mi.menu_week_id = ?
            ORDER BY mi.menu_date, mi.slot
            """,
            (week_id,),
        ).fetchall()

    # ── Organise by day ──────────────────────────────────────────
    days_map: dict[str, list] = defaultdict(list)
    for r in items:
        days_map[r["menu_date"]].append(dict(r))

    days_out = []
    for date_str in sorted(days_map.keys()):
        d = date.fromisoformat(date_str)
        slots = sorted(days_map[date_str], key=lambda x: (
            SLOTS_ORDER.index(x["slot"]) if x["slot"] in SLOTS_ORDER else 99
        ))
        days_out.append({
            "date": date_str,
            "day_name": DIAS_ES[d.weekday()],
            "slots": [
                {
                    "slot": s["slot"],
                    "dish": s["dish_name"],
                    "protein": s["protein"],
                    "sauce_tag": s["sauce_tag"],
                    "is_forced": bool(s["is_forced"]),
                    "was_exception": bool(s["was_exception"]),
                    "exception_reason": s["exception_reason"],
                }
                for s in slots
            ],
        })

    # ── Sauce summary ────────────────────────────────────────────
    sauces_used = sorted(set(
        r["sauce_tag"] for r in items
        if r["sauce_tag"] and not r["slot"].startswith("ensalada_")
    ))

    # ── Protein distribution per day ─────────────────────────────
    proteins_by_day: dict[str, dict[str, int]] = {}
    for r in items:
        if r["protein"] and r["protein"] != "none":
            d = r["menu_date"]
            if d not in proteins_by_day:
                proteins_by_day[d] = defaultdict(int)
            proteins_by_day[d][r["protein"]] += 1

    # ── Exceptions ───────────────────────────────────────────────
    exceptions = [
        {
            "date": r["menu_date"],
            "slot": r["slot"],
            "reason": r["exception_reason"],
            "dish": r["dish_name"],
        }
        for r in items if r["was_exception"]
    ]

    # ── Warnings ─────────────────────────────────────────────────
    warnings: list[str] = []

    sauce_exc = [e for e in exceptions if "SAUCE" in (e["reason"] or "")]
    if sauce_exc:
        warnings.append(f"{len(sauce_exc)} slot(s) tuvieron que relajar el filtro de salsa.")

    window_exc = [e for e in exceptions if "WINDOW_RELAXED" in (e["reason"] or "")]
    if window_exc:
        warnings.append(f"{len(window_exc)} slot(s) usaron un platillo repetido antes de 20 días.")

    forced = [r for r in items if r["is_forced"]]
    forced_non_fixed = [
        r for r in forced
        if r["slot"] not in {"entrada_comal", "arroz", "paella", "nuggets", "pancita"}
    ]
    if forced_non_fixed:
        warnings.append(f"{len(forced_non_fixed)} slot(s) tienen override manual forzado.")

    # ── Score (0-100) ─────────────────────────────────────────────
    # Deduct points for exceptions and warnings
    score = 100
    score -= len(sauce_exc) * 5
    score -= len(window_exc) * 3
    score -= len(warnings) * 2
    score = max(0, score)

    # ── Totals ───────────────────────────────────────────────────
    totals = {
        "dishes": len(items),
        "with_sauce_tag": sum(1 for r in items if r["sauce_tag"]),
        "exceptions": len(exceptions),
        "forced_overrides": len(forced_non_fixed),
        "sauces_unique": len(sauces_used),
    }

    return {
        "week_start": week_start_date,
        "week_id": week_id,
        "days": days_out,
        "sauces_used": sauces_used,
        "proteins_by_day": {k: dict(v) for k, v in proteins_by_day.items()},
        "exceptions": exceptions,
        "warnings": warnings,
        "score": score,
        "totals": totals,
    }


def selection_diagnostics(week_start_date: str) -> dict[str, Any]:
    """
    Explain, slot by slot, why each dish ended up in the generated menu.

    Intended for owner-facing diagnostics and debugging.
    """
    with get_conn() as conn:
        week_row = conn.execute(
            "SELECT id, week_start_date, generated_at, finalized, notes FROM menu_week WHERE week_start_date=?",
            (week_start_date,),
        ).fetchone()
        if not week_row:
            return {"error": f"No existe menú para la semana {week_start_date}"}

        week_id = int(week_row["id"])
        rows = conn.execute(
            """
            SELECT
                mi.menu_date,
                mi.slot,
                mi.dish_id,
                mi.is_forced,
                mi.was_exception,
                mi.exception_reason,
                mi.explanation,
                d.name AS dish_name,
                d.protein,
                d.style_tag,
                d.sauce_tag,
                GROUP_CONCAT(dt.tag, '|') AS tags
            FROM menu_item mi
            JOIN dish d ON d.id = mi.dish_id
            LEFT JOIN dish_tag dt ON dt.dish_id = d.id
            WHERE mi.menu_week_id = ?
            GROUP BY
                mi.menu_date, mi.slot, mi.dish_id,
                mi.is_forced, mi.was_exception, mi.exception_reason, mi.explanation,
                d.name, d.protein, d.style_tag, d.sauce_tag
            ORDER BY mi.menu_date, mi.slot
            """,
            (week_id,),
        ).fetchall()

        priority_rows = conn.execute(
            """
            SELECT dish_id, weekday, slot, weight, note
            FROM dish_priority_rule
            """
        ).fetchall()

    priorities_by_dish: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in priority_rows:
        priorities_by_dish[int(row["dish_id"])].append(
            {
                "weekday": row["weekday"],
                "slot": row["slot"],
                "weight": int(row["weight"] or 0),
                "note": row["note"],
            }
        )

    days: list[dict[str, Any]] = []
    day_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        item = dict(row)
        tags = sorted([t for t in (item.get("tags") or "").split("|") if t])
        weekday = date.fromisoformat(item["menu_date"]).weekday()
        matching_priorities = [
            p
            for p in priorities_by_dish.get(int(item["dish_id"]), [])
            if (p["weekday"] is None or int(p["weekday"]) == weekday)
            and (p["slot"] is None or p["slot"] == item["slot"])
        ]

        reasons: list[str] = []
        if item["slot"] in FIXED_SLOTS:
            reasons.append("Slot fijo del sistema.")
        if item["slot"] == "molcajete" and weekday == 0:
            reasons.append("Molcajete obligatorio del lunes por diseño del menú.")
        if int(item["is_forced"] or 0) == 1 and item["slot"] not in FIXED_SLOTS:
            reasons.append("El dueño o la edición manual lo dejó forzado.")
        if int(item["was_exception"] or 0) == 1:
            reasons.append(f"Entró por excepción: {item['exception_reason']}.")
        if TAG_ONLY_FRI in tags:
            reasons.append("Platillo exclusivo de viernes.")
        if TAG_ONLY_SAT in tags:
            reasons.append("Platillo exclusivo de sábado.")
        if TAG_MONDAY_MOLCAJETE in tags:
            reasons.append("Marcado para el slot especial de molcajete.")
        if matching_priorities:
            total_weight = sum(int(p["weight"]) for p in matching_priorities)
            reasons.append(f"Tuvo prioridad configurada para este día/slot (+{total_weight}).")
        if item.get("sauce_tag"):
            reasons.append(f"Considerado dentro de rotación de salsa: {item['sauce_tag']}.")
        if item.get("explanation"):
            reasons.append(str(item["explanation"]))

        day_map[item["menu_date"]].append(
            {
                "slot": item["slot"],
                "dish_id": int(item["dish_id"]),
                "dish_name": item["dish_name"],
                "protein": item["protein"],
                "style_tag": item["style_tag"],
                "sauce_tag": item["sauce_tag"],
                "tags": tags,
                "is_fixed": item["slot"] in FIXED_SLOTS,
                "is_forced": bool(item["is_forced"]),
                "was_exception": bool(item["was_exception"]),
                "exception_reason": item["exception_reason"],
                "priority_rules": matching_priorities,
                "why": reasons,
            }
        )

    for menu_date in sorted(day_map.keys()):
        d = date.fromisoformat(menu_date)
        slots = sorted(
            day_map[menu_date],
            key=lambda x: SLOTS_ORDER.index(x["slot"]) if x["slot"] in SLOTS_ORDER else 999,
        )
        days.append(
            {
                "date": menu_date,
                "day_name": DIAS_ES[d.weekday()],
                "slots": slots,
            }
        )

    return {
        "week_start": week_start_date,
        "week_id": week_id,
        "generated_at": week_row["generated_at"],
        "finalized": int(week_row["finalized"] or 0),
        "days": days,
    }


def summarize_simulation_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Aggregate stress-test runs into a compact quality summary.
    """
    total_runs = len(runs)
    failed_runs = [run for run in runs if run.get("status") != "ok"]
    ok_runs = [run for run in runs if run.get("status") == "ok"]

    avg_score = 0.0
    if ok_runs:
        avg_score = sum(float(run.get("score") or 0) for run in ok_runs) / len(ok_runs)

    slot_exception_counts: dict[str, int] = defaultdict(int)
    for run in ok_runs:
        for exc in run.get("exceptions", []):
            slot_exception_counts[str(exc["slot"])] += 1

    recommendations: list[str] = []
    if failed_runs:
        recommendations.append("Hay corridas que fallaron. Revisa el catalogo o reglas obligatorias.")
    if any(int(run.get("exception_count") or 0) > 0 for run in ok_runs):
        recommendations.append("Hay excepciones de rotacion. Conviene ampliar catalogo o ajustar prioridades.")
    if avg_score and avg_score < 95:
        recommendations.append("El score promedio sigue por debajo de 95. Hay margen para mejorar precision.")

    return {
        "total_runs": total_runs,
        "failed_runs": len(failed_runs),
        "ok_runs": len(ok_runs),
        "average_score": round(avg_score, 2),
        "worst_score": min((int(run.get("score") or 0) for run in ok_runs), default=0),
        "total_exceptions": sum(int(run.get("exception_count") or 0) for run in ok_runs),
        "slot_exception_counts": dict(sorted(slot_exception_counts.items())),
        "recommendations": recommendations,
    }


def print_report(week_start_date: str) -> None:
    """Print a human-readable quality report to stdout."""
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    r = week_report(week_start_date)
    if "error" in r:
        print(f"ERROR: {r['error']}")
        return

    print(f"\n{'='*60}")
    print(f"REPORTE DE CALIDAD — Semana {r['week_start']}")
    print(f"Score: {r['score']}/100")
    print(f"{'='*60}")

    print(f"\nTotales: {r['totals']['dishes']} platillos | "
          f"{r['totals']['sauces_unique']} salsas únicas | "
          f"{r['totals']['exceptions']} excepciones")

    if r["warnings"]:
        print("\nADVERTENCIAS:")
        for w in r["warnings"]:
            print(f"  ⚠  {w}")

    print("\nSALSAS USADAS ESTA SEMANA:")
    print("  " + ", ".join(r["sauces_used"]) if r["sauces_used"] else "  (ninguna)")

    print("\nPROTEÍNAS POR DÍA:")
    for day in r["days"]:
        prot = r["proteins_by_day"].get(day["date"], {})
        prot_str = " | ".join(f"{k}:{v}" for k, v in sorted(prot.items()))
        print(f"  {day['day_name']:10} {prot_str}")

    if r["exceptions"]:
        print("\nEXCEPCIONES:")
        for e in r["exceptions"]:
            print(f"  {e['date']} {e['slot']:20} | {e['reason']} | {e['dish']}")

    print(f"\n{'='*60}\n")


# =============================================================
# Shopping summary (protein counts for purchase order)
# =============================================================

# How many portions each slot contributes to purchasing
SLOT_PORTIONS: dict[str, int] = {
    "fuerte_res": 1,
    "fuerte_pollo": 1,
    "fuerte_cerdo": 1,
    "fuerte_pescado": 1,
    "fuerte_camaron": 1,
    "molcajete": 1,
    "chamorro": 1,
    "pescado_al_gusto": 1,
    "camaron_al_gusto": 1,
    "sopa_pollo": 1,
    "pancita": 1,
}


def shopping_summary(week_start_date: str) -> dict[str, Any]:
    """
    Generate a protein purchasing summary for a week.

    Returns:
        {
          "week_start": "YYYY-MM-DD",
          "by_protein": {
            "res":    [{"date": ..., "slot": ..., "dish": ...}, ...],
            "pollo":  [...],
            ...
          },
          "counts": {"res": int, "pollo": int, "cerdo": int, "pescado": int, "camaron": int},
          "daily_breakdown": {
            "2026-03-09": {"res": 2, "pollo": 1, ...},
            ...
          }
        }
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM menu_week WHERE week_start_date=?", (week_start_date,)
        ).fetchone()
        if not row:
            return {"error": f"No existe menú para la semana {week_start_date}"}
        week_id = int(row["id"])

        items = conn.execute(
            """
            SELECT mi.menu_date, mi.slot, d.name AS dish_name, d.protein
            FROM menu_item mi
            JOIN dish d ON d.id = mi.dish_id
            WHERE mi.menu_week_id = ?
              AND d.protein != 'none'
              AND d.protein IS NOT NULL
            ORDER BY mi.menu_date, mi.slot
            """,
            (week_id,),
        ).fetchall()

    by_protein: dict[str, list] = defaultdict(list)
    counts: dict[str, int] = defaultdict(int)
    daily_breakdown: dict[str, dict[str, int]] = {}

    for r in items:
        prot = r["protein"]
        entry = {
            "date": r["menu_date"],
            "slot": r["slot"],
            "dish": r["dish_name"],
        }
        by_protein[prot].append(entry)
        counts[prot] += 1

        d = r["menu_date"]
        if d not in daily_breakdown:
            daily_breakdown[d] = defaultdict(int)
        daily_breakdown[d][prot] += 1

    return {
        "week_start": week_start_date,
        "by_protein": {k: v for k, v in sorted(by_protein.items())},
        "counts": dict(counts),
        "daily_breakdown": {k: dict(v) for k, v in sorted(daily_breakdown.items())},
    }


def print_shopping_summary(week_start_date: str) -> None:
    """Print a human-readable shopping/protein summary to stdout."""
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    r = shopping_summary(week_start_date)
    if "error" in r:
        print(f"ERROR: {r['error']}")
        return

    print(f"\n{'='*60}")
    print(f"RESUMEN DE COMPRAS — Semana {r['week_start']}")
    print(f"{'='*60}")

    total = sum(r["counts"].values())
    print(f"\nTotal porciones con proteína: {total}")
    print("\nTOTAL POR PROTEÍNA:")
    for prot, count in sorted(r["counts"].items(), key=lambda x: -x[1]):
        print(f"  {prot:10} {count:3} porciones")

    print("\nDETALLE DIARIO:")
    for date_str, prots in r["daily_breakdown"].items():
        d = date.fromisoformat(date_str)
        day_name = DIAS_ES[d.weekday()]
        prot_str = " | ".join(f"{k}:{v}" for k, v in sorted(prots.items()))
        print(f"  {day_name:10} ({date_str})  {prot_str}")

    print("\nPOR PROTEÍNA (detalle):")
    for prot, entries in r["by_protein"].items():
        print(f"\n  [{prot.upper()}] — {len(entries)} total")
        for e in entries:
            d = date.fromisoformat(e["date"])
            print(f"    {DIAS_ES[d.weekday()]:10} {e['slot']:20} {e['dish']}")

    print(f"\n{'='*60}\n")


# =============================================================
# Underused / overused dish report (catalog health)
# =============================================================

def catalog_health_report(
    since_days: int = 60,
    min_uses_warn: int = 0,
    max_uses_warn: int = 11,
) -> dict[str, Any]:
    """
    Report dishes that haven't appeared recently or appear too frequently.

    Args:
        since_days:    Flag dishes not used in last N days as "dormant".
        min_uses_warn: Dishes with fewer uses than this are "underused" (0 = all-time unused).
        max_uses_warn: Dishes with more uses than this are "overused".

    Returns:
        {
          "generated_at": "YYYY-MM-DD",
          "total_active": int,
          "never_used": [{"id", "name", "course_group", "protein"}],
          "dormant":    [{"id", "name", "course_group", "protein", "last_used", "days_ago"}],
          "overused":   [{"id", "name", "course_group", "protein", "uses"}],
          "by_group":   {"sopa": {"total": N, "never": N, "dormant": N}, ...}
        }
    """
    today = date.today()
    cutoff = today - timedelta(days=since_days)

    fixed_slots_sql = "', '".join(sorted(CATALOG_HEALTH_FIXED_SLOTS))
    with get_conn() as conn:
        all_active = conn.execute(
            f"""
            SELECT
                d.id,
                d.name,
                d.course_group,
                d.protein,
                COUNT(mi.id) AS uses_total,
                COALESCE(
                    SUM(
                        CASE
                            WHEN mi.id IS NULL THEN 0
                            WHEN mi.slot IN ('{fixed_slots_sql}') THEN 0
                            ELSE 1
                        END
                    ),
                    0
                ) AS uses_non_fixed,
                MAX(mi.menu_date) AS last_used
            FROM dish d
            LEFT JOIN menu_item mi ON mi.dish_id = d.id
            WHERE d.active = 1
            GROUP BY d.id
            ORDER BY d.course_group, uses_non_fixed, d.name
            """,
        ).fetchall()

    never_used = []
    dormant = []
    overused = []
    by_group: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "never": 0, "dormant": 0, "overused": 0})

    for r in all_active:
        cg = r["course_group"]
        uses_total = int(r["uses_total"] or 0)
        uses = int(r["uses_non_fixed"] or 0)
        last_used = r["last_used"]
        by_group[cg]["total"] += 1

        base = {"id": r["id"], "name": r["name"], "course_group": cg, "protein": r["protein"]}

        if uses == 0:
            never_used.append(base)
            by_group[cg]["never"] += 1
        elif last_used and date.fromisoformat(last_used) < cutoff:
            days_ago = (today - date.fromisoformat(last_used)).days
            dormant.append(
                {
                    **base,
                    "last_used": last_used,
                    "days_ago": days_ago,
                    "uses": uses,
                    "uses_total": uses_total,
                }
            )
            by_group[cg]["dormant"] += 1

        if uses >= max_uses_warn:
            overused.append({**base, "uses": uses, "uses_total": uses_total})
            by_group[cg]["overused"] += 1

    # Sort dormant by days_ago desc (longest dormant first)
    dormant.sort(key=lambda x: -x["days_ago"])
    overused.sort(key=lambda x: -x["uses"])

    return {
        "generated_at": today.isoformat(),
        "since_days": since_days,
        "total_active": len(all_active),
        "never_used": never_used,
        "dormant": dormant,
        "overused": overused,
        "by_group": {k: dict(v) for k, v in sorted(by_group.items())},
    }


def print_catalog_health(since_days: int = 60, max_uses_warn: int = 11) -> None:
    """Print a human-readable catalog health report to stdout."""
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    r = catalog_health_report(since_days=since_days, max_uses_warn=max_uses_warn)

    print(f"\n{'='*60}")
    print(f"SALUD DEL CATÁLOGO — {r['generated_at']}")
    print(f"Ventana dormido: {since_days} días | Umbral sobreusado: ≥{max_uses_warn} usos")
    print(f"{'='*60}")
    print(f"\nTotal activos: {r['total_active']}")
    print(f"Nunca usados:  {len(r['never_used'])}")
    print(f"Dormidos:      {len(r['dormant'])} (sin aparecer en {since_days} días)")
    print(f"Sobreusados:   {len(r['overused'])} (≥{max_uses_warn} usos)")

    print("\nPOR GRUPO:")
    for cg, stats in r["by_group"].items():
        print(f"  {cg:20} total={stats['total']:4} | nunca={stats['never']:3} | dormidos={stats['dormant']:3} | sobreusados={stats['overused']:3}")

    if r["never_used"]:
        print(f"\nNUNCA USADOS ({len(r['never_used'])}):")
        by_cg: dict[str, list] = defaultdict(list)
        for d in r["never_used"]:
            by_cg[d["course_group"]].append(d)
        for cg in sorted(by_cg):
            print(f"\n  [{cg}] — {len(by_cg[cg])}")
            for d in by_cg[cg]:
                prot = f"[{d['protein']:8}] " if d["protein"] != "none" else ""
                print(f"    id={d['id']:5} {prot}{d['name']}")

    if r["dormant"]:
        print(f"\nDORMIDOS ({len(r['dormant'])}) — sin aparecer en {since_days}+ días:")
        for d in r["dormant"][:30]:  # top 30
            prot = f"[{d['protein']:8}] " if d["protein"] != "none" else ""
            print(f"  {d['course_group']:20} {prot}{d['name']:40} último: {d['last_used']} ({d['days_ago']}d)")
        if len(r["dormant"]) > 30:
            print(f"  ... y {len(r['dormant']) - 30} más.")

    if r["overused"]:
        print(f"\nSOBREUSADOS (≥{max_uses_warn} usos):")
        for d in r["overused"]:
            prot = f"[{d['protein']:8}] " if d["protein"] != "none" else ""
            print(f"  {d['course_group']:20} {prot}{d['name']:40} usos={d['uses']}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    import sys
    week = sys.argv[1] if len(sys.argv) > 1 else "2026-04-06"
    print_report(week)
