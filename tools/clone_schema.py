# tools/clone_schema.py
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SRC_DB = Path("data/app.db")
DST_DB = Path("data/app_prod.db")

def main():
    if not SRC_DB.exists():
        raise SystemExit(f"No existe: {SRC_DB.resolve()}")

    # Si ya existe destino, lo borramos para recrearlo limpio
    if DST_DB.exists():
        DST_DB.unlink()

    DST_DB.parent.mkdir(parents=True, exist_ok=True)

    src = sqlite3.connect(SRC_DB)
    src.row_factory = sqlite3.Row
    dst = sqlite3.connect(DST_DB)

    try:
        # Trae TODOS los objetos del schema (tablas, índices, triggers)
        rows = src.execute("""
            SELECT type, name, sql
            FROM sqlite_master
            WHERE sql IS NOT NULL
              AND name NOT LIKE 'sqlite_%'
            ORDER BY
              CASE type
                WHEN 'table' THEN 1
                WHEN 'index' THEN 2
                WHEN 'trigger' THEN 3
                WHEN 'view' THEN 4
                ELSE 9
              END,
              name
        """).fetchall()

        dst.execute("PRAGMA foreign_keys=ON;")

        for r in rows:
            sql = r["sql"]
            if not sql:
                continue
            dst.executescript(sql + ";\n" if not sql.strip().endswith(";") else sql + "\n")

        dst.commit()

    finally:
        src.close()
        dst.close()

    print(f"OK ✅ Schema clonado a: {DST_DB.resolve()}")

if __name__ == "__main__":
    main()
