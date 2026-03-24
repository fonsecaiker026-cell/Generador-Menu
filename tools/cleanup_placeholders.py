# tools/cleanup_placeholders.py
# tools/cleanup_placeholders.py
from __future__ import annotations

import os
import sys
import re

# --- asegurar root del proyecto ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_conn


# 1) patrones EXACTOS que detectan tus placeholders
PLACEHOLDER_REGEXES = [
    r"^Entrada NO comal \d+$",
    r"^Sopa \d+$",
    r"^Crema \d+$",
    r"^Pasta \d+$",
    r"^Complemento \d+$",
    r"^(Res|Pollo|Pescado|Camaron|Cerdo) estilo \d+$",
    r"^Ensalada [ABC]$",  # solo "Ensalada A/B/C" exacto
    r"Chamorro",
]

DRY_RUN = False  # primero True para revisar. Luego False para aplicar.

def is_placeholder(name: str) -> bool:
    name = (name or "").strip()
    return any(re.match(p, name, flags=re.IGNORECASE) for p in PLACEHOLDER_REGEXES)

def main():
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, name, course_group, protein, style_tag, active
            FROM dish
            WHERE active=1
            ORDER BY id
            """
        ).fetchall()

        targets = [dict(r) for r in rows if is_placeholder(r["name"])]

        print("FOUND:", len(targets))
        for r in targets[:250]:
            print(r)
        if len(targets) > 250:
            print("... (mostrando solo primeros 250)")

        if DRY_RUN:
            print("\nDRY_RUN=True -> no se hizo ningún cambio.")
            return

        ids = [int(r["id"]) for r in targets]
        if not ids:
            print("Nada que desactivar.")
            return

        q = ",".join(["?"] * len(ids))

        # Desactivar (no borrar histórico)
        conn.execute(f"UPDATE dish SET active=0 WHERE id IN ({q})", ids)

        # Limpieza recomendada
        conn.execute(f"DELETE FROM dish_tag WHERE dish_id IN ({q})", ids)
        conn.execute(f"DELETE FROM dish_lock WHERE dish_id IN ({q})", ids)

        # Quitar overrides que apunten a estos dishes
        conn.execute(
            f"""
            DELETE FROM menu_override
            WHERE forced_dish_id IN ({q})
               OR blocked_dish_id IN ({q})
            """,
            ids + ids,
        )

        conn.commit()
        print("OK: desactivados y limpiados:", len(ids))

if __name__ == "__main__":
    main()
