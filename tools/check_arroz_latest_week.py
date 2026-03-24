import sys
from pathlib import Path
from datetime import datetime
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.db import get_conn

ARROZ_FIXED_ID = 1596

def resolve_db_path() -> Path:
    c = get_conn()
    try:
        rows = c.execute("PRAGMA database_list").fetchall()
        for r in rows:
            d = dict(r)
            if d.get("name") == "main" and d.get("file"):
                return Path(d["file"])
        for r in rows:
            d = dict(r)
            if d.get("file"):
                return Path(d["file"])
        raise RuntimeError("No pude resolver la ruta real de la DB (PRAGMA database_list).")
    finally:
        c.close()

def backup_db(db_path: Path) -> Path:
    backups_dir = Path("backups")
    backups_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backups_dir / f"{db_path.name}.bak_{ts}"
    shutil.copy2(db_path, backup_path)
    print(f"[OK] Backup creado: {backup_path}")
    return backup_path

def main():
    db_path = resolve_db_path()
    print(f"[INFO] DB detectada: {db_path}")
    if not db_path.exists():
        raise FileNotFoundError(f"No existe la DB detectada: {db_path}")

    backup_db(db_path)

    with get_conn() as c:
        before = c.execute("""
            SELECT COUNT(*) AS n
            FROM menu_item
            WHERE slot='arroz' AND dish_id != ?
        """, (ARROZ_FIXED_ID,)).fetchone()["n"]

        total = c.execute("""
            SELECT COUNT(*) AS n
            FROM menu_item
            WHERE slot='arroz'
        """).fetchone()["n"]

        print(f"[INFO] Filas arroz totales: {total}")
        print(f"[INFO] Filas arroz a corregir (dish_id != {ARROZ_FIXED_ID}): {before}")

        if before == 0:
            print("[OK] No hay nada que corregir.")
            return

        rows = c.execute("""
            SELECT id, dish_id, explanation
            FROM menu_item
            WHERE slot='arroz' AND dish_id != ?
        """, (ARROZ_FIXED_ID,)).fetchall()

        suffix = "Arroz es fijo por regla (L-V)."

        c.execute("BEGIN")
        for r in rows:
            item_id = int(r["id"])
            old_id = int(r["dish_id"])
            old_exp = r["explanation"] or ""
            new_exp = old_exp if suffix in old_exp else (old_exp + " | " + suffix).strip(" |")

            c.execute("""
                UPDATE menu_item
                SET dish_id=?,
                    was_exception=1,
                    exception_reason=?,
                    explanation=?
                WHERE id=?
            """, (
                ARROZ_FIXED_ID,
                f"ARROZ_FIXED_GUARDRAIL: overwrote dish_id {old_id} -> {ARROZ_FIXED_ID}",
                new_exp,
                item_id
            ))
        c.execute("COMMIT")

        after = c.execute("""
            SELECT COUNT(*) AS n
            FROM menu_item
            WHERE slot='arroz' AND dish_id != ?
        """, (ARROZ_FIXED_ID,)).fetchone()["n"]

        print("[OK] Corrección aplicada.")
        print(f"[INFO] Filas arroz aún incorrectas: {after}")

if __name__ == "__main__":
    main()
