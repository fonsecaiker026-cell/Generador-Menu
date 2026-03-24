import sqlite3
from pathlib import Path

DB_PATH = Path("data/app_prod.db")

def main():
    if not DB_PATH.exists():
        raise SystemExit(f"No existe {DB_PATH}")

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    # Seguridad: FK ON (si tu schema las usa)
    con.execute("PRAGMA foreign_keys = ON;")

    with con:
        # 1) Limpiar historial (vamos a re-cargar semanas reales)
        con.execute("DELETE FROM menu_item;")
        con.execute("DELETE FROM menu_override;")
        con.execute("DELETE FROM menu_week;")
        con.execute("DELETE FROM leftover;")

        # 2) Limpiar locks/relaciones (si existen)
        con.execute("DELETE FROM dish_lock;")
        con.execute("DELETE FROM dish_tag;")
        con.execute("DELETE FROM dish_season;")
        con.execute("DELETE FROM dish_beef_cut;")

        # 3) Borrar dishes retirados (active=0)
        deleted = con.execute("DELETE FROM dish WHERE active=0;").rowcount

        # 4) (Opcional) compactar ids autoincrement de semanas/overrides/items (no dish)
        # OJO: sqlite_sequence existe porque tienes AUTOINCREMENT en algunas tablas.
        # Limpiamos solo las que reiniciamos:
        try:
            con.execute("""
                DELETE FROM sqlite_sequence
                WHERE name IN ('menu_week','menu_item','menu_override','leftover','dish_lock','dish_tag','dish_season','dish_beef_cut')
            """)
        except Exception:
            pass

    # VACUUM debe ir fuera de transacción
    con.execute("VACUUM;")
    con.close()

    print("OK ✅ app_prod.db reseteada (historial limpio) y dishes inactive borrados.")
    print(f"Dishes borrados (active=0): {deleted}")

if __name__ == "__main__":
    main()
