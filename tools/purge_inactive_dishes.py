# tools/purge_inactive_dishes.py
from __future__ import annotations

import os
import sys
from typing import List, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_conn


def table_exists(conn, table: str) -> bool:
    r = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return bool(r)


def table_cols(conn, table: str) -> List[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [r["name"] for r in rows]


def pick_col(conn, table: str, candidates: List[str]) -> Optional[str]:
    cols = set(table_cols(conn, table))
    for c in candidates:
        if c in cols:
            return c
    return None


def delete_refs(conn, table: str, fk_candidates: List[str], ids: List[int]) -> None:
    if not table_exists(conn, table):
        return
    fk = pick_col(conn, table, fk_candidates)
    if not fk:
        print(f"SKIP: {table} (sin FK {fk_candidates}). Columnas: {table_cols(conn, table)}")
        return
    q = f"DELETE FROM {table} WHERE {fk} IN ({','.join(['?']*len(ids))})"
    conn.execute(q, ids)


def main() -> None:
    with get_conn() as conn:
        inactive = conn.execute("SELECT COUNT(*) n FROM dish WHERE active=0").fetchone()["n"]
        print("inactive dishes:", inactive)

        if inactive == 0:
            print("OK: no hay dishes inactive.")
            return

        # Lista de ids inactive
        ids = conn.execute("SELECT id FROM dish WHERE active=0").fetchall()
        inactive_ids = [int(r["id"]) for r in ids]

        # Seguridad 1: NO borrar si algún inactive está usado en menu_item
        used = conn.execute("""
            SELECT COUNT(*) n
            FROM menu_item mi
            JOIN dish d ON d.id = mi.dish_id
            WHERE d.active = 0
        """).fetchone()["n"]
        if used:
            raise RuntimeError(f"ABORT: hay {used} menu_item usando dishes inactive. No se borrará nada.")

        # (Opcional) Aviso: qué inactive vamos a borrar
        rows = conn.execute(
            f"SELECT id,name FROM dish WHERE id IN ({','.join(['?']*len(inactive_ids))})",
            inactive_ids
        ).fetchall()
        for r in rows:
            print("will_delete:", r["id"], r["name"])

        conn.execute("BEGIN")

        # Limpieza de referencias en tablas hijas (solo si existen)
        child_tables = [
            ("dish_tag", ["dish_id", "dish", "dishId"]),
            ("dish_beef_cut", ["dish_id", "dish", "dishId"]),
            ("dish_season", ["dish_id", "dish", "dishId"]),
            ("dish_lock", ["dish_id", "dish", "dishId"]),
            ("leftover", ["dish_id", "dish", "dishId"]),
            ("menu_override", ["dish_id", "dish", "dishId"]),
        ]

        for tbl, fk_candidates in child_tables:
            delete_refs(conn, tbl, fk_candidates, inactive_ids)

        # Limpia menu_override por columnas reales (forced_dish_id / blocked_dish_id)
        if table_exists(conn, "menu_override"):
            cols = set(table_cols(conn, "menu_override"))
        if "forced_dish_id" in cols:
            q = f"UPDATE menu_override SET forced_dish_id=NULL WHERE forced_dish_id IN ({','.join(['?']*len(inactive_ids))})"
            conn.execute(q, inactive_ids)
        if "blocked_dish_id" in cols:
            q = f"UPDATE menu_override SET blocked_dish_id=NULL WHERE blocked_dish_id IN ({','.join(['?']*len(inactive_ids))})"
            conn.execute(q, inactive_ids)


        # Finalmente borrar dishes inactive
        qd = f"DELETE FROM dish WHERE id IN ({','.join(['?']*len(inactive_ids))})"
        conn.execute(qd, inactive_ids)

        conn.execute("COMMIT")
        print(f"OK ✅ dishes inactive borrados: {len(inactive_ids)}")


if __name__ == "__main__":
    main()
