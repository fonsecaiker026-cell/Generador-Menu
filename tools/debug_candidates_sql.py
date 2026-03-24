# tools/debug_candidates_sql.py
from __future__ import annotations

import os, sys
from datetime import date

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_conn
import src.engine.generator as g

def main():
    d = date(2025, 12, 8)
    slots = ["crema", "sopa", "pasta", "arroz"]

    print("=== PATH CHECK ===")
    print("generator_file =", os.path.abspath(g.__file__))

    with get_conn() as c:
        print("\n=== RAW SQL COUNTS (conn.execute) ===")
        for cg in slots:
            n = c.execute(
                "SELECT COUNT(*) n FROM dish WHERE active=1 AND course_group=?",
                (cg,),
            ).fetchone()["n"]
            print(f"{cg:6s} raw_count =", n)

        print("\n=== fetch_all COUNTS (generator.fetch_all) ===")
        for cg in slots:
            rows = g.fetch_all(
                c,
                "SELECT id,name FROM dish WHERE active=1 AND course_group=?",
                (cg,),
            )
            print(f"{cg:6s} fetch_all =", len(rows), "| sample =", (rows[0] if rows else None))

        print("\n=== candidates() COUNTS ===")
        for slot in slots:
            cand = g.candidates(c, slot, d)
            print(f"{slot:6s} candidates =", len(cand), "| sample =", (cand[0] if cand else None))

        print("\n=== filter_day_only sanity ===")
        # probamos el filtro directo con cremas
        crema_rows = g.fetch_all(
            c,
            "SELECT id,name,course_group,protein,style_tag FROM dish WHERE active=1 AND course_group=? LIMIT 20",
            ("crema",),
        )
        crema = [dict(r) for r in crema_rows]
        out = g.filter_day_only(c, crema, d)  # como lo tengas actualmente
        print("crema before =", len(crema), "after_filter_day_only =", len(out))

if __name__ == "__main__":
    main()
