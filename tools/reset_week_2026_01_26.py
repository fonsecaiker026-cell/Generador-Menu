from __future__ import annotations
import os, sys
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_conn

WEEK_START = "2026-01-26"

def main():
    with get_conn() as c:
        row = c.execute(
            "SELECT id FROM menu_week WHERE week_start_date=?",
            (WEEK_START,),
        ).fetchone()

        if not row:
            print("No existe la semana", WEEK_START)
            return

        week_id = row["id"]
        start = datetime.strptime(WEEK_START, "%Y-%m-%d").date()
        end = start + timedelta(days=6)

        c.execute("BEGIN")
        di = c.execute(
            "DELETE FROM menu_item WHERE menu_week_id=?",
            (week_id,),
        ).rowcount

        do = c.execute(
            "DELETE FROM menu_override WHERE date(menu_date) BETWEEN ? AND ?",
            (start.isoformat(), end.isoformat()),
        ).rowcount

        dw = c.execute(
            "DELETE FROM menu_week WHERE id=?",
            (week_id,),
        ).rowcount

        c.execute("COMMIT")

    print(
        f"OK reset week {WEEK_START} | "
        f"menu_item={di} | overrides={do} | menu_week={dw}"
    )

if __name__ == "__main__":
    main()
