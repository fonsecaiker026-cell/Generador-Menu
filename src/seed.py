import csv
from pathlib import Path
from src.db import get_conn, init_db

SEED_PATH = Path(__file__).resolve().parent.parent / "seeds" / "seed_dishes.csv"

def upsert_beef_cut(conn, cut_name: str) -> int:
    cur = conn.execute("INSERT OR IGNORE INTO beef_cut(name) VALUES (?)", (cut_name,))
    cur = conn.execute("SELECT id FROM beef_cut WHERE name = ?", (cut_name,))
    return cur.fetchone()["id"]

def upsert_dish(conn, name, course_group, protein, style_tag) -> int:
    conn.execute(
        """
        INSERT INTO dish(name, course_group, protein, style_tag, active)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(name) DO UPDATE SET
          course_group=excluded.course_group,
          protein=excluded.protein,
          style_tag=excluded.style_tag,
          active=1
        """,
        (name, course_group, protein, style_tag if style_tag else None),
    )
    cur = conn.execute("SELECT id FROM dish WHERE name = ?", (name,))
    return cur.fetchone()["id"]

def set_tags(conn, dish_id: int, tags: str):
    if not tags:
        return
    for t in [x.strip() for x in tags.split("|") if x.strip()]:
        conn.execute(
            "INSERT OR IGNORE INTO dish_tag(dish_id, tag) VALUES (?, ?)",
            (dish_id, t),
        )

def set_season(conn, dish_id: int, rule: str, start, end):
    if not rule:
        rule = "ALLOW"
    start_m = int(start) if start else None
    end_m = int(end) if end else None
    conn.execute(
        """
        INSERT INTO dish_season(dish_id, rule, start_month, end_month)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(dish_id) DO UPDATE SET
          rule=excluded.rule,
          start_month=excluded.start_month,
          end_month=excluded.end_month
        """,
        (dish_id, rule, start_m, end_m),
    )

def link_beef_cut(conn, dish_id: int, cut_name: str):
    if not cut_name:
        return
    cut_id = upsert_beef_cut(conn, cut_name)
    conn.execute(
        "INSERT OR IGNORE INTO dish_beef_cut(dish_id, beef_cut_id) VALUES (?, ?)",
        (dish_id, cut_id),
    )

def run_seed():
    init_db()
    with get_conn() as conn:
        with SEED_PATH.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dish_id = upsert_dish(
                    conn,
                    row["name"],
                    row["course_group"],
                    row["protein"],
                    row.get("style_tag", ""),
                )
                set_tags(conn, dish_id, row.get("tags", ""))
                set_season(conn, dish_id, row.get("season_rule", "ALLOW"),
                           row.get("season_start", ""), row.get("season_end", ""))
                link_beef_cut(conn, dish_id, row.get("beef_cut", ""))

        conn.commit()

    print("Seed cargado OK.")

if __name__ == "__main__":
    run_seed()
