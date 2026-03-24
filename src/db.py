from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional
import re
import sqlite3
import threading
import unicodedata

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "db_migrations"

_BOOTSTRAP_LOCK = threading.Lock()
_BOOTSTRAPPED_DB_PATHS: set[str] = set()


class ClosingConnection(sqlite3.Connection):
    """sqlite3 connection that also closes itself when used as a context manager."""

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            return super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.close()


def _connect_raw() -> ClosingConnection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _ensure_migrations_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS _migrations (
            filename TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def _applied_migrations(conn) -> set[str]:
    rows = conn.execute("SELECT filename FROM _migrations").fetchall()
    return {str(r["filename"]) for r in rows}


def _run_migration_sql_safe(conn, sql: str) -> None:
    buffer = ""
    statements: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buffer = f"{buffer}\n{line}" if buffer else line
        if sqlite3.complete_statement(buffer):
            stmt = buffer.strip()
            if stmt:
                statements.append(stmt)
            buffer = ""

    tail = buffer.strip()
    if tail:
        statements.append(tail)

    for stmt in statements:
        try:
            conn.execute(stmt)
        except Exception as exc:
            msg = str(exc).lower()
            if any(token in msg for token in ("already exists", "duplicate column", "table already exists")):
                continue
            raise


def bootstrap_db() -> None:
    """
    Ensure the DB has schema + all SQL migrations applied.

    Safe to call repeatedly. The first call per DB path bootstraps the file;
    later calls are effectively no-ops for the current process.
    """
    db_key = str(DB_PATH.resolve())
    if db_key in _BOOTSTRAPPED_DB_PATHS:
        return

    with _BOOTSTRAP_LOCK:
        if db_key in _BOOTSTRAPPED_DB_PATHS:
            return

        with _connect_raw() as conn:
            schema = SCHEMA_PATH.read_text(encoding="utf-8")
            conn.executescript(schema)

            _ensure_migrations_table(conn)
            applied = _applied_migrations(conn)

            for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if path.name in applied:
                    continue
                sql = path.read_text(encoding="utf-8")
                _run_migration_sql_safe(conn, sql)
                conn.execute("INSERT OR IGNORE INTO _migrations(filename) VALUES (?)", (path.name,))

            conn.commit()

        _BOOTSTRAPPED_DB_PATHS.add(db_key)


def get_conn():
    bootstrap_db()
    return _connect_raw()


def fetch_dishes_admin(
    *,
    name_query: str = "",
    course_group: str = "ALL",
    protein: str = "ALL",
    active_filter: str = "ALL",
    limit: int = 200,
) -> list[dict]:
    q = """
        SELECT d.id, d.name, d.course_group, d.protein, d.style_tag, d.sauce_tag, d.active,
               MAX(CASE WHEN mw.finalized = 1 THEN mi.menu_date END) AS last_used
        FROM dish d
        LEFT JOIN menu_item mi ON mi.dish_id = d.id
        LEFT JOIN menu_week mw ON mw.id = mi.menu_week_id
        WHERE 1=1
    """
    params = {}

    if name_query.strip():
        q += " AND LOWER(d.name) LIKE :name"
        params["name"] = f"%{name_query.strip().lower()}%"

    if course_group != "ALL":
        q += " AND d.course_group = :cg"
        params["cg"] = course_group

    if protein != "ALL":
        q += " AND d.protein = :pr"
        params["pr"] = protein

    if active_filter == "ACTIVE":
        q += " AND d.active = 1"
    elif active_filter == "INACTIVE":
        q += " AND d.active = 0"

    q += " GROUP BY d.id ORDER BY d.active DESC, d.name ASC LIMIT :lim"
    params["lim"] = int(limit)

    with get_conn() as c:
        rows = c.execute(q, params).fetchall()
    return [dict(r) for r in rows]


def dish_usage_stats(dish_id: int) -> dict:
    """Return usage count and latest use date for a dish."""
    with get_conn() as c:
        row = c.execute(
            """
            SELECT
              COUNT(*) AS used_count,
              MAX(date(menu_date)) AS last_used_date
            FROM menu_item
            WHERE dish_id = ?
            """,
            (dish_id,),
        ).fetchone()
    return {
        "used_count": int(row["used_count"]) if row and row["used_count"] is not None else 0,
        "last_used_date": row["last_used_date"],
    }


def dish_future_override_conflicts(dish_id: int, from_date: Optional[date] = None) -> dict:
    """Check whether a dish appears in future forced/blocked overrides."""
    if from_date is None:
        from_date = date.today()

    with get_conn() as c:
        forced = c.execute(
            """
            SELECT COUNT(*) AS n
            FROM menu_override
            WHERE forced_dish_id = ?
              AND date(menu_date) >= date(?)
            """,
            (dish_id, from_date.isoformat()),
        ).fetchone()["n"]

        blocked = c.execute(
            """
            SELECT COUNT(*) AS n
            FROM menu_override
            WHERE blocked_dish_id = ?
              AND date(menu_date) >= date(?)
            """,
            (dish_id, from_date.isoformat()),
        ).fetchone()["n"]

    return {"forced_future": int(forced), "blocked_future": int(blocked)}


def set_dish_active(dish_id: int, active: int) -> None:
    with get_conn() as c:
        c.execute("UPDATE dish SET active = ? WHERE id = ?", (int(active), int(dish_id)))
        c.commit()


def clear_future_forced_overrides(dish_id: int, from_date: Optional[date] = None) -> int:
    """Clear future forced overrides for a dish."""
    if from_date is None:
        from_date = date.today()

    with get_conn() as c:
        cur = c.execute(
            """
            UPDATE menu_override
               SET forced_dish_id = NULL
             WHERE forced_dish_id = ?
               AND date(menu_date) >= date(?)
            """,
            (dish_id, from_date.isoformat()),
        )
        c.commit()
        return cur.rowcount


def init_db():
    bootstrap_db()


def slugify_style_tag(s: str) -> str:
    """Convert text to snake_case ASCII for use as style_tag."""
    s = (s or "").strip().lower()
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def get_dish_by_name_group(conn, name: str, course_group: str):
    """
    Compatibility helper: because `dish.name` is globally unique in schema,
    this now resolves by exact name and returns the row regardless of group.
    """
    return conn.execute(
        """
        SELECT *
        FROM dish
        WHERE lower(trim(name)) = lower(trim(?))
        LIMIT 1
        """,
        (name.strip(),),
    ).fetchone()


def get_dish_by_style_tag(conn, style_tag: str):
    return conn.execute(
        """
        SELECT *
        FROM dish
        WHERE style_tag=?
        LIMIT 1
        """,
        (style_tag,),
    ).fetchone()


def insert_dish(conn, *, name: str, course_group: str, protein: str, style_tag: str | None, active: int) -> int:
    cur = conn.execute(
        """
        INSERT INTO dish (name, course_group, protein, style_tag, active)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, course_group, protein, style_tag, int(active)),
    )
    return cur.lastrowid


def update_dish(conn, *, dish_id: int, protein: str, style_tag: str | None, active: int) -> None:
    conn.execute(
        """
        UPDATE dish
        SET protein=?,
            style_tag=?,
            active=?
        WHERE id=?
        """,
        (protein, style_tag, int(active), dish_id),
    )


def update_dish_full(
    conn,
    *,
    dish_id: int,
    name: str,
    course_group: str,
    protein: str,
    style_tag: str | None,
    sauce_tag: str | None,
    active: int,
) -> None:
    """Actualiza todos los campos editables de un platillo."""
    conn.execute(
        """
        UPDATE dish
        SET name=?,
            course_group=?,
            protein=?,
            style_tag=?,
            sauce_tag=?,
            active=?
        WHERE id=?
        """,
        (name, course_group, protein, style_tag, sauce_tag, int(active), int(dish_id)),
    )


def upsert_dish_by_name_group(
    conn,
    *,
    name: str,
    course_group: str,
    protein: str,
    style_tag: str | None,
    active: int,
) -> tuple[int, str]:
    """
    Upsert aligned with the real schema:
    - `dish.name` is globally unique
    - if the name exists, update that same row
    - otherwise insert a new dish
    """
    existing = get_dish_by_name_group(conn, name, course_group)
    if existing:
        conn.execute(
            """
            UPDATE dish
            SET course_group=?,
                protein=?,
                style_tag=?,
                active=?
            WHERE id=?
            """,
            (course_group, protein, style_tag, int(active), int(existing["id"])),
        )
        return int(existing["id"]), "updated"

    dish_id = insert_dish(conn, name=name, course_group=course_group, protein=protein, style_tag=style_tag, active=active)
    return dish_id, "inserted"


def add_tags(conn, dish_id: int, tags: list[str]) -> None:
    tags = [t.strip() for t in (tags or []) if t and t.strip()]
    if not tags:
        return
    conn.executemany(
        """
        INSERT OR IGNORE INTO dish_tag (dish_id, tag)
        VALUES (?, ?)
        """,
        [(dish_id, t) for t in tags],
    )


def replace_tags(conn, dish_id: int, tags: list[str]) -> None:
    conn.execute("DELETE FROM dish_tag WHERE dish_id=?", (dish_id,))
    add_tags(conn, dish_id, tags)


def list_distinct_tags(conn) -> list[str]:
    rows = conn.execute("SELECT DISTINCT tag FROM dish_tag ORDER BY tag").fetchall()
    return [r["tag"] for r in rows]


if __name__ == "__main__":
    init_db()
    print(f"DB creada/actualizada en: {DB_PATH}")
