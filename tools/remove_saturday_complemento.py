# tools/remove_saturday_complemento.py
from __future__ import annotations
import os, sys
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_conn

def main():
    with get_conn() as conn:
        conn.execute("BEGIN")
        # borra SOLO los menu_item con slot complemento en sábados
        # strftime('%w'): 0=domingo, 6=sábado (SQLite)
        cur = conn.execute("""
            DELETE FROM menu_item
            WHERE slot = 'complemento'
              AND strftime('%w', menu_date) = '6'
        """)
        deleted = cur.rowcount if cur.rowcount is not None else -1
        conn.execute("COMMIT")
    print(f"OK ✅ Saturday complemento eliminado. rows={deleted}")

if __name__ == "__main__":
    main()
