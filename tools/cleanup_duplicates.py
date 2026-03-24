"""
Cleanup duplicate dishes in the database.

Decisions made:
- Keep dishes with proper Spanish accents (more professional)
- Keep older IDs when equivalent, unless newer has better name
- Merge: transfer all references (menu_item, dish_tag, overrides, etc.) before deleting
"""
import sqlite3
import shutil
from datetime import datetime

DB = "data/app.db"


def backup_db():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = f"data/app_backup_before_cleanup_{ts}.db"
    shutil.copy2(DB, dest)
    print(f"Backup created: {dest}")
    return dest


def merge_dish(conn, keep_id: int, delete_id: int, new_name: str = None):
    """
    Migrate all references from delete_id to keep_id, then delete delete_id.
    Optionally rename the keeper.
    """
    cur = conn.cursor()

    # Get names for logging
    cur.execute("SELECT name, course_group, protein FROM dish WHERE id=?", (keep_id,))
    keeper = cur.fetchone()
    cur.execute("SELECT name, course_group, protein FROM dish WHERE id=?", (delete_id,))
    removed = cur.fetchone()

    if not keeper or not removed:
        print(f"  SKIP: id={keep_id} or id={delete_id} not found")
        return

    print(f"  MERGE: keep={keep_id} '{keeper[0]}' | drop={delete_id} '{removed[0]}'")

    # Transfer menu_item references (ignore conflicts - same slot/date can't have both)
    cur.execute(
        "UPDATE OR IGNORE menu_item SET dish_id=? WHERE dish_id=?",
        (keep_id, delete_id)
    )
    # Delete any remaining menu_items that couldn't be transferred (conflicts)
    cur.execute("DELETE FROM menu_item WHERE dish_id=?", (delete_id,))

    # Transfer dish_tags (ignore conflicts)
    cur.execute(
        "INSERT OR IGNORE INTO dish_tag (dish_id, tag) "
        "SELECT ?, tag FROM dish_tag WHERE dish_id=?",
        (keep_id, delete_id)
    )
    cur.execute("DELETE FROM dish_tag WHERE dish_id=?", (delete_id,))

    # Transfer menu_override forced references
    cur.execute(
        "UPDATE OR IGNORE menu_override SET forced_dish_id=? WHERE forced_dish_id=?",
        (keep_id, delete_id)
    )
    cur.execute(
        "DELETE FROM menu_override WHERE forced_dish_id=?", (delete_id,)
    )

    # Transfer menu_override blocked references
    cur.execute(
        "UPDATE OR IGNORE menu_override SET blocked_dish_id=? WHERE blocked_dish_id=?",
        (keep_id, delete_id)
    )
    cur.execute(
        "DELETE FROM menu_override WHERE blocked_dish_id=?", (delete_id,)
    )

    # Transfer dish_beef_cut
    cur.execute(
        "INSERT OR IGNORE INTO dish_beef_cut (dish_id, beef_cut_id) "
        "SELECT ?, beef_cut_id FROM dish_beef_cut WHERE dish_id=?",
        (keep_id, delete_id)
    )
    cur.execute("DELETE FROM dish_beef_cut WHERE dish_id=?", (delete_id,))

    # Transfer dish_season
    cur.execute(
        "DELETE FROM dish_season WHERE dish_id=?", (delete_id,)
    )

    # Transfer dish_lock if table exists
    try:
        cur.execute(
            "UPDATE OR IGNORE dish_lock SET dish_id=? WHERE dish_id=?",
            (keep_id, delete_id)
        )
        cur.execute("DELETE FROM dish_lock WHERE dish_id=?", (delete_id,))
    except Exception:
        pass

    # Delete the duplicate dish
    cur.execute("DELETE FROM dish WHERE id=?", (delete_id,))

    # Rename keeper if requested
    if new_name:
        cur.execute("UPDATE dish SET name=? WHERE id=?", (new_name, keep_id))
        print(f"    Renamed keeper to: '{new_name}'")

    print(f"    Done.")


def delete_inactive(conn, dish_id: int):
    """Delete an inactive dish that has no references."""
    cur = conn.cursor()
    cur.execute("SELECT name, active FROM dish WHERE id=?", (dish_id,))
    row = cur.fetchone()
    if not row:
        print(f"  SKIP: id={dish_id} not found")
        return
    if row[1] == 1:
        print(f"  SKIP: id={dish_id} '{row[0]}' is ACTIVE - not deleting")
        return

    # Clean up all references before deleting
    cur.execute("DELETE FROM dish_tag WHERE dish_id=?", (dish_id,))
    cur.execute("DELETE FROM menu_item WHERE dish_id=?", (dish_id,))
    cur.execute("DELETE FROM menu_override WHERE forced_dish_id=?", (dish_id,))
    cur.execute("DELETE FROM menu_override WHERE blocked_dish_id=?", (dish_id,))
    cur.execute("DELETE FROM dish_beef_cut WHERE dish_id=?", (dish_id,))
    cur.execute("DELETE FROM dish_season WHERE dish_id=?", (dish_id,))
    try:
        cur.execute("DELETE FROM dish_lock WHERE dish_id=?", (dish_id,))
    except Exception:
        pass
    cur.execute("DELETE FROM dish WHERE id=?", (dish_id,))
    print(f"  DELETED inactive: id={dish_id} '{row[0]}'")


def fix_name(conn, dish_id: int, new_name: str):
    cur = conn.cursor()
    cur.execute("SELECT name FROM dish WHERE id=?", (dish_id,))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE dish SET name=? WHERE id=?", (new_name, dish_id))
        print(f"  RENAMED: id={dish_id} '{row[0]}' -> '{new_name}'")


def main():
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")

    print("=" * 60)
    print("CLEANUP DUPLICATES")
    print("=" * 60)

    # ── CATEGORY 1: Exact duplicates (accent difference) ──────────
    print("\n[1] Exact duplicates (accent differences) — keep accented version\n")

    # Albóndigas al Chipotle: keep 944 (has accent), delete 1495
    merge_dish(conn, keep_id=944, delete_id=1495)

    # Chilpáchole de Jaiba: keep 550 (has accent), delete 461
    merge_dish(conn, keep_id=550, delete_id=461)

    # Crema de Brócoli: keep 494 (has accent), delete 1348
    merge_dish(conn, keep_id=494, delete_id=1348)

    # Ensalada César: keep 1139 (has accent), delete 172
    merge_dish(conn, keep_id=1139, delete_id=172)

    # ── CATEGORY 2: One active, one inactive — delete inactive ─────
    print("\n[2] Inactive duplicates — deleting inactive versions\n")

    delete_inactive(conn, 539)   # Caldo Xóchitl (inactivo), activo=1413
    delete_inactive(conn, 1590)  # Galleta de Atun (inactivo), activo=1295
    delete_inactive(conn, 1274)  # Rollito de Jamón con Guacamole (inactivo), activo=1575
    delete_inactive(conn, 769)   # Tacos de Camarón Tradicional (inactivo), activo=1440

    # ── CATEGORY 3: Similar names — merge to best version ──────────
    print("\n[3] Similar names — merging to canonical version\n")

    # Crema de Jitomate: "Aceite de Oliva" is correct Spanish, keep 535
    merge_dish(conn, keep_id=535, delete_id=1412)

    # Crema de Zanahoria y Nuez: keep 533 (older, more natural phrasing)
    merge_dish(conn, keep_id=533, delete_id=1368)

    # Lomo en Salsa de Champiñones: keep 868 (plural is correct)
    merge_dish(conn, keep_id=868, delete_id=867)

    # Tortitas de Atún Espejo en Salsa Pasilla: keep 726 (cleaner name)
    merge_dish(conn, keep_id=726, delete_id=719)

    # Cerdo en Salsa Morita vs Cerdo en Salsa de Chile Morita:
    # keep 1479 (more descriptive, explicit "de Chile")
    merge_dish(conn, keep_id=1479, delete_id=781)

    # Crema de Chicharrón: keep 503 (has accent, protein=cerdo is correct)
    merge_dish(conn, keep_id=503, delete_id=1455)

    # Consomé Ranchero: 1466=pollo, 546=res — DIFFERENT proteins, keep both
    # but fix names to distinguish them clearly
    fix_name(conn, 546,  "Consomé Ranchero de Res")
    fix_name(conn, 1466, "Consomé Ranchero de Pollo")

    # Camarones Enchilados al Sarten vs con Queso — genuinely different dishes, keep both
    # No action needed

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("CLEANUP COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    backup_db()
    main()
