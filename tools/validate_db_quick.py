# tools/validate_db_quick.py
import os, sys
import unicodedata, re
from collections import defaultdict

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_conn

ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200D\uFEFF]")
WS_RE = re.compile(r"\s+")

def norm_key(s: str) -> str:
    s = (s or "").strip().replace("\u00a0", " ")
    s = ZERO_WIDTH_RE.sub("", s)
    s = WS_RE.sub(" ", s)
    s = unicodedata.normalize("NFKC", s)
    return s.casefold()

def main():
    with get_conn() as c:
        total_dish = c.execute("SELECT COUNT(*) AS n FROM dish").fetchone()["n"]
        total_items = c.execute("SELECT COUNT(*) AS n FROM menu_item").fetchone()["n"]

        rows = c.execute("SELECT id, name FROM dish").fetchall()
        buckets = defaultdict(list)
        for r in rows:
            buckets[norm_key(r["name"])].append((r["id"], r["name"]))

        dup_groups = {k:v for k,v in buckets.items() if len(v) > 1}

        print("dish_total:", total_dish)
        print("menu_item_total:", total_items)
        print("dup_groups:", len(dup_groups))

        if dup_groups:
            # muestra solo 10 grupos
            for i, (k, v) in enumerate(dup_groups.items()):
                if i >= 10:
                    break
                print("DUP:", v)

if __name__ == "__main__":
    main()
