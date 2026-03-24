import os, sys
sys.path.insert(0, os.path.abspath("."))

from src.db import get_conn

KEEP_ID = 1596
MERGE_IDS = [1256, 1318]  # se van a reemplazar por KEEP_ID

def main():
    with get_conn() as c:
        # sanity
        keep = c.execute("SELECT id,name,course_group,active FROM dish WHERE id=?", (KEEP_ID,)).fetchone()
        print("KEEP =", dict(keep) if keep else None)

        rows = c.execute(
            "SELECT id,name,course_group,active FROM dish WHERE id IN (?,?)",
            (MERGE_IDS[0], MERGE_IDS[1]),
        ).fetchall()
        print("MERGE =")
        for r in rows:
            print(dict(r))

        c.execute("BEGIN")

        total = 0
        for old_id in MERGE_IDS:
            n = c.execute(
                "UPDATE menu_item SET dish_id=? WHERE dish_id=?",
                (KEEP_ID, old_id),
            ).rowcount
            total += n
            # desactiva el viejo
            c.execute("UPDATE dish SET active=0 WHERE id=?", (old_id,))

        c.execute("COMMIT")

        print("OK updated menu_item =", total)
        # ver distinct arroz dish en menu_item
        rows2 = c.execute("""
            SELECT DISTINCT d.id, d.name, d.active
            FROM menu_item mi
            JOIN dish d ON d.id = mi.dish_id
            WHERE mi.slot='arroz'
            ORDER BY d.id
        """).fetchall()
        print("ARROZ MENU ITEMS DISTINCT =")
        for r in rows2:
            print(r["id"], "|", r["name"], "| active=", r["active"])

if __name__ == "__main__":
    main()
