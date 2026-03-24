from __future__ import annotations
import os, sys
from datetime import date, timedelta

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_conn
from src.engine.slots import slots_for_day
from src.engine.generator import candidates  # ✅ aquí vive

def main():
    # Rango representativo: historial + semanas recientes
    start = date(2025, 12, 1)
    end = date(2026, 2, 28)

    slot_min = {}        # slot -> (min_count, day)
    slot_zero_days = {}  # slot -> [days...]

    with get_conn() as conn:
        d = start
        while d <= end:
            if d.weekday() <= 5:  # Lun-Sab
                for slot in slots_for_day(d):
                    try:
                        cand = candidates(conn, slot, d)
                        n = len(cand)
                    except Exception as e:
                        print(f"ERROR candidates(slot={slot}, day={d}): {e}")
                        n = -1

                    prev = slot_min.get(slot)
                    if prev is None or (n >= 0 and n < prev[0]):
                        slot_min[slot] = (n, d)

                    if n == 0:
                        slot_zero_days.setdefault(slot, []).append(d)

            d += timedelta(days=1)

    print("\n=== MIN CANDIDATES POR SLOT (RANGO) ===")
    for slot, (n, d) in sorted(slot_min.items(), key=lambda x: x[1][0]):
        print(f"{slot:18} min={n:3} on {d}")

    print("\n=== DÍAS CON 0 CANDIDATOS (ALERTA) ===")
    for slot, days in sorted(slot_zero_days.items(), key=lambda x: len(x[1]), reverse=True):
        if days:
            print(f"{slot:18} zero_days={len(days)}  example={days[0]}")

if __name__ == "__main__":
    main()
