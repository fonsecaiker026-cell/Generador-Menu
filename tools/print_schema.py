import sys
from pathlib import Path

# Asegura import de src aunque se ejecute desde tools/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db import get_conn

def main():
    with get_conn() as c:
        rows = c.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()

        for r in rows:
            print("\n===", r["name"], "===")
            print(r["sql"])

if __name__ == "__main__":
    main()
