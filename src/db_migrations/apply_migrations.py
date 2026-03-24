"""
Migration runner — idempotente.

Mantiene una tabla `_migrations` en la DB para registrar qué archivos
ya se aplicaron. Solo corre los nuevos. Safe para ejecutar múltiples veces.
"""
from pathlib import Path
from src.db import get_conn


def _ensure_migrations_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            filename TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


def _applied(conn) -> set[str]:
    rows = conn.execute("SELECT filename FROM _migrations").fetchall()
    return {r["filename"] for r in rows}


def _run_sql_safe(conn, sql: str, filename: str):
    """
    Ejecuta cada statement del archivo por separado para poder manejar
    errores específicos (ej: columna ya existe en ALTER TABLE).
    """
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    for stmt in statements:
        try:
            conn.execute(stmt)
        except Exception as e:
            msg = str(e).lower()
            # Ignorar errores de "ya existe" — idempotencia
            if any(k in msg for k in ("already exists", "duplicate column", "table already exists")):
                print(f"    [skip] {stmt[:60]}... ({e})")
            else:
                raise


def main():
    migrations_dir = Path(__file__).parent
    sql_files = sorted(migrations_dir.glob("*.sql"))

    with get_conn() as conn:
        _ensure_migrations_table(conn)
        applied = _applied(conn)

        ran = []
        skipped = []

        for p in sql_files:
            if p.name in applied:
                skipped.append(p.name)
                continue

            print(f"  Applying {p.name}...")
            sql = p.read_text(encoding="utf-8")
            _run_sql_safe(conn, sql, p.name)

            conn.execute(
                "INSERT INTO _migrations(filename) VALUES (?)", (p.name,)
            )
            ran.append(p.name)

        conn.commit()

    if ran:
        print(f"Migrations applied: {ran}")
    if skipped:
        print(f"Already applied (skipped): {skipped}")
    if not ran:
        print("No new migrations to apply.")


if __name__ == "__main__":
    main()
