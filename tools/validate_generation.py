"""
Pre-generation health check for menu slots.

Verifies that every slot in a given week has enough candidate dishes available
AFTER applying the rotation window. Useful to detect catalog gaps before
generation fails mid-way.

Run:
    python tools/validate_generation.py             # next Mon from today
    python tools/validate_generation.py 2026-03-16  # specific week

Exit codes:
    0  All slots OK
    1  One or more slots below minimum threshold
"""
import os
import sys
from collections import defaultdict
from datetime import date, timedelta

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.stdout.reconfigure(encoding="utf-8")

from src.db import get_conn
from src.engine.generator import (
    FIXED_SLOTS,
    NO_ROTATION_SLOTS,
    candidates,
    ensure_monday,
    parse_yyyy_mm_dd,
    recent_dish_ids,
    to_yyyy_mm_dd,
    window_days_for_slot,
)
from src.engine.slots import slots_for_day

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────
MIN_CANDIDATES = 5   # alert if fewer candidates remain after rotation window
WARN_CANDIDATES = 10  # warning (yellow) if fewer than this

# These slots have window=0 — they can't run out via rotation; skip count check
SKIP_CHECK_SLOTS = NO_ROTATION_SLOTS


def _next_monday() -> date:
    today = date.today()
    return today + timedelta(days=(7 - today.weekday()) % 7 or 7)


def _candidates_after_window(conn, slot: str, day: date) -> tuple[int, int]:
    """
    Returns (total_catalog, after_window) for a slot on a given day.
    after_window = candidates that survive the rotation filter.
    """
    window = window_days_for_slot(slot)
    cand = candidates(conn, slot, day)
    total = len(cand)

    if window <= 0 or not cand:
        return total, total

    recent = recent_dish_ids(conn, day, window, slot=slot)
    available = [c for c in cand if int(c["id"]) not in recent]
    return total, len(available)


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def validate_week(week_start: date) -> bool:
    """
    Validates all slots for the week starting on `week_start`.
    Returns True if all slots are OK, False if any slot is below MIN_CANDIDATES.
    """
    DAYS = ["LUN", "MAR", "MIE", "JUE", "VIE", "SAB"]
    issues: list[tuple[str, str, int, int]] = []   # (day_label, slot, total, available)
    warnings: list[tuple[str, str, int, int]] = []
    by_slot: dict[str, list[int]] = defaultdict(list)

    print(f"\n{'='*62}")
    print(f"  VALIDACIÓN PRE-GENERACIÓN — semana {to_yyyy_mm_dd(week_start)}")
    print(f"{'='*62}")

    # slot → (day, total_catalog) for the first day the slot appears
    slot_representative_day: dict[str, tuple[date, int]] = {}

    with get_conn() as conn:
        for offset in range(6):
            day = week_start + timedelta(days=offset)
            day_label = DAYS[offset]
            slots = slots_for_day(day)

            for slot in slots:
                if slot in FIXED_SLOTS or slot in SKIP_CHECK_SLOTS:
                    continue

                total, avail = _candidates_after_window(conn, slot, day)

                # Record first-seen day for this slot (for catalog count display)
                if slot not in slot_representative_day:
                    slot_representative_day[slot] = (day, total)

                by_slot[slot].append(avail)

                if avail < MIN_CANDIDATES:
                    issues.append((day_label, slot, total, avail))
                elif avail < WARN_CANDIDATES:
                    warnings.append((day_label, slot, total, avail))

    # ── Summary by slot (min available across the week) ──────────────────
    print(f"\n{'SLOT':<22} {'CATÁLOGO':>9} {'DISPONIBLE (min)':>17}  STATUS")
    print("-" * 62)

    for slot, avail_list in sorted(by_slot.items()):
        min_avail = min(avail_list)
        _, total = slot_representative_day.get(slot, (None, "?"))
        if min_avail < MIN_CANDIDATES:
            status = "!! ERROR"
        elif min_avail < WARN_CANDIDATES:
            status = " ! WARN"
        else:
            status = "    OK"
        print(f"  {slot:<20} {total:>9}   {min_avail:>15}  {status}")

    # ── Issue details ────────────────────────────────────────────────────
    if issues:
        print(f"\n{'='*62}")
        print(f"  ERRORES — slots con < {MIN_CANDIDATES} candidatos disponibles")
        print(f"{'='*62}")
        for day_label, slot, total, avail in issues:
            print(f"  {day_label}  {slot:<22} catálogo={total}  disponible={avail}")

    if warnings:
        print(f"\n{'='*62}")
        print(f"  ADVERTENCIAS — slots con < {WARN_CANDIDATES} candidatos disponibles")
        print(f"{'='*62}")
        for day_label, slot, total, avail in warnings:
            print(f"  {day_label}  {slot:<22} catálogo={total}  disponible={avail}")

    # ── Final verdict ────────────────────────────────────────────────────
    print(f"\n{'='*62}")
    if not issues:
        print(f"  RESULTADO: OK — todos los slots tienen >= {MIN_CANDIDATES} candidatos")
    else:
        print(f"  RESULTADO: FALLO — {len(issues)} slot(s) por debajo del mínimo")
    print(f"{'='*62}\n")

    return len(issues) == 0


def main() -> None:
    if len(sys.argv) > 1:
        try:
            week_start = ensure_monday(parse_yyyy_mm_dd(sys.argv[1]))
        except ValueError:
            print(f"Fecha inválida: {sys.argv[1]}. Usa formato YYYY-MM-DD.")
            sys.exit(2)
    else:
        week_start = ensure_monday(_next_monday())

    ok = validate_week(week_start)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
