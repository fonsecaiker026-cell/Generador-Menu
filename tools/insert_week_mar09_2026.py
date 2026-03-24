#!/usr/bin/env python3
"""
Refresca la semana 2026-03-09 copiando exactamente los items de 2025-03-09.

No depende de week_id fijos. Usa la fecha fuente correcta y reemplaza el
contenido de la semana destino si ya existe.
"""
import sqlite3
from datetime import date, datetime

DB = "data/app.db"
SRC_WEEK_START = "2025-03-09"
DST_WEEK_START = "2026-03-09"
SRC_START = date(2025, 3, 9)
DST_START = date(2026, 3, 9)


def main() -> None:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    src = conn.execute(
        "SELECT id FROM menu_week WHERE week_start_date=?",
        (SRC_WEEK_START,),
    ).fetchone()
    if not src:
        raise SystemExit(f"ERROR: semana fuente {SRC_WEEK_START} no encontrada")

    dst = conn.execute(
        "SELECT id FROM menu_week WHERE week_start_date=?",
        (DST_WEEK_START,),
    ).fetchone()
    if dst:
        dst_week_id = int(dst["id"])
        conn.execute("DELETE FROM menu_item WHERE menu_week_id=?", (dst_week_id,))
        print(f"Semana destino existente limpiada: id={dst_week_id}")
    else:
        cur = conn.execute(
            "INSERT INTO menu_week (week_start_date, generated_at, finalized) VALUES (?,?,1)",
            (DST_WEEK_START, datetime.now().isoformat()),
        )
        dst_week_id = int(cur.lastrowid)
        print(f"Semana destino creada: id={dst_week_id}")

    src_items = conn.execute(
        """
        SELECT menu_date, slot, dish_id, is_forced, was_exception, exception_reason, explanation
        FROM menu_item
        WHERE menu_week_id=?
        ORDER BY menu_date, slot
        """,
        (int(src["id"]),),
    ).fetchall()
    print(f"Items fuente: {len(src_items)}")

    delta_days = (DST_START - SRC_START).days
    for row in src_items:
        src_date = date.fromisoformat(str(row["menu_date"]))
        dst_date = src_date.fromordinal(src_date.toordinal() + delta_days)
        conn.execute(
            """
            INSERT INTO menu_item(
                menu_week_id, menu_date, slot, dish_id,
                is_forced, was_exception, exception_reason, explanation
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                dst_week_id,
                dst_date.isoformat(),
                row["slot"],
                int(row["dish_id"]),
                int(row["is_forced"] or 0),
                int(row["was_exception"] or 0),
                row["exception_reason"],
                row["explanation"],
            ),
        )

    conn.execute(
        "UPDATE menu_week SET generated_at=?, finalized=1 WHERE id=?",
        (datetime.now().isoformat(), dst_week_id),
    )
    conn.commit()
    conn.close()
    print(f"OK: semana {DST_WEEK_START} refrescada desde {SRC_WEEK_START}")


if __name__ == "__main__":
    main()
