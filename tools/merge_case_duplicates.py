from __future__ import annotations

import os
import re
import sqlite3
import sys
import unicodedata
from typing import Dict, List, Tuple

# --- asegurar root del proyecto en sys.path ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_conn  # noqa: E402


# -------------------------
# Normalización de nombres
# -------------------------
_WS_RE = re.compile(r"\s+")
_ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200D\uFEFF]")

def norm_name(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("\u00a0", " ")
    s = _ZERO_WIDTH_RE.sub("", s)
    s = _WS_RE.sub(" ", s)
    s = unicodedata.normalize("NFKC", s)
    return s.casefold()


def is_all_upper(s: str) -> bool:
    letters = [ch for ch in (s or "") if ch.isalpha()]
    if not letters:
        return False
    return all(ch.isupper() for ch in letters)


def choose_canonical(rows: List[sqlite3.Row]) -> sqlite3.Row:
    """
    Escoge el "mejor" dish como canonical:
    1) preferir NO todo mayúsculas
    2) preferir active=1
    3) preferir id más bajo
    """
    def key(r: sqlite3.Row):
        name = r["name"] or ""
        active = int(r["active"] or 0)
        return (
            1 if is_all_upper(name) else 0,   # 0 mejor (no uppercase)
            0 if active == 1 else 1,          # 0 mejor (activo)
            int(r["id"]),                     # menor id mejor
        )
    return sorted(rows, key=key)[0]


# -------------------------
# Introspección DB
# -------------------------
def list_tables(conn) -> List[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def table_columns(conn, table: str) -> List[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [r[1] for r in rows]


def referencing_columns_for_dish(conn) -> List[Tuple[str, str]]:
    """
    Encuentra automáticamente columnas que apuntan a dish:
    - dish_id
    - forced_dish_id
    - blocked_dish_id
    (solo si existen en la tabla)
    """
    targets = []
    for t in list_tables(conn):
        cols = set(table_columns(conn, t))
        for c in ("dish_id", "forced_dish_id", "blocked_dish_id"):
            if c in cols:
                targets.append((t, c))
    return targets


# -------------------------
# Reasignación segura
# -------------------------
def try_update_fk(conn, table: str, col: str, dup_id: int, canon_id: int) -> None:
    """
    Intenta UPDATE directo. Si falla por UNIQUE, cae a merge por INSERT OR IGNORE + DELETE.
    Si la columna no existe, no hace nada (blindado).
    """
    cols = set(table_columns(conn, table))
    if col not in cols:
        return  # blindado contra schema

    # UPDATE simple suele funcionar en menu_item, leftover, menu_override, etc.
    try:
        conn.execute(
            f"UPDATE {table} SET {col}=? WHERE {col}=?",
            (canon_id, dup_id),
        )
        return
    except sqlite3.IntegrityError:
        # En tablas con constraints (p.ej. dish_tag UNIQUE(dish_id,tag)),
        # hacemos merge por "insert ignore" y luego borramos dup.
        pass

    # Fallback: merge por INSERT OR IGNORE + DELETE
    # Construimos INSERT con todas las columnas (excepto autoincrement id si existe)
    # y reemplazamos col por canon_id.
    col_list = table_columns(conn, table)
    # Detectar columna PK autoincrement típica "id"
    insert_cols = [c for c in col_list if c != "id"]

    if col not in insert_cols:
        # Si la col es "id" (no debería pasar) o no insertable:
        # hacemos delete directo de filas dup para no romper.
        conn.execute(f"DELETE FROM {table} WHERE {col}=?", (dup_id,))
        return

    select_exprs = []
    params = []
    for c in insert_cols:
        if c == col:
            select_exprs.append("?")
            params.append(canon_id)
        else:
            select_exprs.append(c)

    insert_cols_sql = ", ".join(insert_cols)
    select_sql = ", ".join(select_exprs)

    # Insertar las filas del dup como canon, ignorando duplicados
    conn.execute(
        f"""
        INSERT OR IGNORE INTO {table} ({insert_cols_sql})
        SELECT {select_sql}
        FROM {table}
        WHERE {col} = ?
        """,
        tuple(params + [dup_id]),
    )

    # Borrar filas del dup
    conn.execute(f"DELETE FROM {table} WHERE {col}=?", (dup_id,))


def merge_dish_group(conn, canon: sqlite3.Row, dups: List[sqlite3.Row], ref_cols: List[Tuple[str, str]]) -> int:
    """
    Reasigna todos los dup -> canon y elimina dishes duplicados.
    Retorna cuántos dishes se eliminaron.
    """
    canon_id = int(canon["id"])
    removed = 0

    for r in dups:
        dup_id = int(r["id"])
        if dup_id == canon_id:
            continue

        # 1) Reasignar referencias en todas las tablas/columnas detectadas
        for (table, col) in ref_cols:
            try_update_fk(conn, table, col, dup_id, canon_id)

        # 2) Eliminar el dish duplicado
        conn.execute("DELETE FROM dish WHERE id=?", (dup_id,))
        removed += 1

    return removed


# -------------------------
# Main
# -------------------------
def main() -> None:
    with get_conn() as conn:
        db_list = conn.execute("PRAGMA database_list").fetchall()
        print("DB:", [tuple(r) for r in db_list])

        # para que sea más predecible
        conn.execute("PRAGMA foreign_keys=OFF")

        dishes = conn.execute("SELECT id, name, active FROM dish").fetchall()

        groups: Dict[str, List[sqlite3.Row]] = {}
        for r in dishes:
            k = norm_name(r["name"])
            groups.setdefault(k, []).append(r)

        dup_groups = [v for v in groups.values() if len(v) > 1]
        print("dup_groups:", len(dup_groups))

        ref_cols = referencing_columns_for_dish(conn)
        # print("ref_cols:", ref_cols)

        removed_total = 0

        # Transacción grande
        conn.execute("BEGIN")
        try:
            for grp in dup_groups:
                canon = choose_canonical(grp)
                removed_total += merge_dish_group(conn, canon, grp, ref_cols)

            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        conn.execute("PRAGMA foreign_keys=ON")

        print(f"OK ✅ Merge terminado. dish eliminados: {removed_total}")


if __name__ == "__main__":
    main()
