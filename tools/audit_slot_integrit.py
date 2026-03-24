# tools/audit_slot_integrity.py
import os, sys
from datetime import datetime, timedelta, date

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_conn
from src.engine.generator import candidates

WINDOW_DEFAULT = 20
WINDOW_PASTA = 15

def main():
    day = date(2026, 1, 31)  # usa un sábado para cubrir todo
    base_slots = [
        "crema","sopa","pasta","arroz","entrada_no_comal",
        "fuerte_res","fuerte_pollo","fuerte_cerdo","fuerte_pescado","fuerte_camaron",
        "ensalada_A","ensalada_B","ensalada_C",
        "molcajete","chamorro",
        "pancita","paella","nuggets","enchiladas","sopa_pollo","pescado_al_gusto","camaron_al_gusto",
        "complemento"
    ]

    with get_conn() as c:
        print("=== CANDIDATES COUNTS ===")
        for slot in base_slots:
            try:
                n = len(candidates(c, slot, day))
            except Exception as e:
                print(slot, "ERROR:", e)
                continue
            print(f"{slot:16} {n}")

        print("\n=== SLOT <-> COURSE_GROUP sanity (random sample used items) ===")
        rows = c.execute("""
            SELECT mi.slot, d.course_group, d.protein, COUNT(*) n
            FROM menu_item mi
            JOIN dish d ON d.id = mi.dish_id
            GROUP BY mi.slot, d.course_group, d.protein
            ORDER BY n DESC
        """).fetchall()

        # muestra combos raros (ej: slot='crema' pero course_group != 'crema')
        weird = []
        for r in rows:
            slot = r["slot"]
            cg = r["course_group"]
            prot = r["protein"]
            if slot in ("crema","sopa","pasta","arroz","entrada_no_comal") and cg != slot:
                weird.append((slot,cg,prot,r["n"]))
            if slot.startswith("fuerte_"):
                # fuerte_* deben ser course_group fuerte
                if cg != "fuerte":
                    weird.append((slot,cg,prot,r["n"]))

        if not weird:
            print("OK ✅ no hay inconsistencias claras slot->course_group")
        else:
            print("ALERTA ❌ inconsistencias encontradas (slot,course_group,protein,count):")
            for x in weird[:60]:
                print(x)

if __name__ == "__main__":
    main()
