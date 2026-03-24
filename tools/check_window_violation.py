import os, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath("."))

from src.db import get_conn
from src.engine.generator import candidates

DAY = date(2026, 1, 26)
SLOT = "sopa"
WINDOW = 20

def main():
    c = get_conn()

    start = (DAY - timedelta(days=WINDOW)).isoformat()

    used = c.execute(
        """
        SELECT d.id, d.name, MAX(mi.menu_date) AS last_used
        FROM menu_item mi
        JOIN dish d ON d.id = mi.dish_id
        WHERE mi.slot = ?
          AND date(mi.menu_date) >= date(?)
        GROUP BY d.id
        """,
        (SLOT, start),
    ).fetchall()

    cand = candidates(c, SLOT, DAY)
    cand_ids = {x["id"] for x in cand}

    violations = [
        (r["id"], r["name"], r["last_used"])
        for r in used
        if r["id"] in cand_ids
    ]

    print(f"DAY = {DAY} | SLOT = {SLOT}")
    print("used_last_20_days =", len(used))
    print("still_in_candidates =", len(violations))

    if violations:
        print("\n❌ VIOLATIONS:")
        for v in violations:
            print(v[0], "|", v[1], "| last_used =", v[2])
    else:
        print("\n✅ OK: ningún platillo usado en ventana aparece como candidato")

    c.close()

if __name__ == "__main__":
    main()
