import os, sys
sys.path.insert(0, os.path.abspath("."))

from datetime import date
from src.db import get_conn
import src.engine.generator as g

DAY = date(2026, 1, 30)

with get_conn() as conn:
    # 1) fetch_all con el MISMO SQL que usa candidates()
    rows = g.fetch_all(
        conn,
        """
        SELECT d.id, d.name, d.course_group, d.protein, d.style_tag
        FROM dish d
        JOIN dish_tag t ON t.dish_id=d.id
        WHERE d.active=1
          AND d.course_group='fuerte'
          AND t.tag=?
        """,
        (g.TAG_FRIDAY_CHAMORRO,),
    )
    print("fetch_all rows =", len(rows))
    if rows:
        print("fetch_all sample:", dict(rows[0]))

    cand = [dict(r) for r in rows] if rows else []
    print("cand before filter_day_only =", len(cand))

    # 2) ver qué está haciendo filter_day_only
    after = g.filter_day_only(conn, cand, DAY)
    print("cand after filter_day_only =", len(after))
    print("after sample =", after[:3])

    # 3) tags reales para esos dishes
    ids = [c["id"] for c in cand]
    if ids:
        q = ",".join(["?"] * len(ids))
        tags = conn.execute(
            f"SELECT dish_id, tag FROM dish_tag WHERE dish_id IN ({q}) ORDER BY dish_id, tag",
            ids,
        ).fetchall()
        print("\nTAGS FOUND:")
        for r in tags:
            print(r["dish_id"], "|", r["tag"])
