import os, sys
from datetime import date

sys.path.insert(0, os.path.abspath("."))

from src.db import get_conn
from src.engine.generator import candidates

def main():
    c = get_conn()

    print("=== DB CHECK ===")
    for cg in ["crema", "sopa", "pasta", "arroz"]:
        n = c.execute(
            "SELECT COUNT(*) n FROM dish WHERE active=1 AND course_group=?",
            (cg,),
        ).fetchone()["n"]
        print(cg, "active_in_db =", n)

    print("\n=== CANDIDATES CHECK ===")
    d = date(2025, 12, 8)
    print("day", d)
    for slot in ["crema", "sopa", "pasta", "arroz"]:
        cand = candidates(c, slot, d)
        print(slot, "candidates =", len(cand))

    c.close()

if __name__ == "__main__":
    main()
