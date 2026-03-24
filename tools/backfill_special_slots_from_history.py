# tools/backfill_special_slots_from_history.py
import os, sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_conn

# Tags
TAG_ONLY_SAT = "only_sat"
TAG_SATURDAY_FIXED = "saturday_fixed"
TAG_FRIDAY_CHAMORRO = "friday_chamorro"
TAG_SAT_ENCHILADAS = "sat_enchiladas"
TAG_MONDAY_MOLCAJETE = "monday_molcajete"

# style_tag esperados para saturday_fixed (ajusta si tú ya usas otros strings)
STYLE_MAP = {
    "pancita": "pancita_fija",
    "paella": "paella_fija",
    "pescado_al_gusto": "pescado_al_gusto_fijo",
    "camaron_al_gusto": "camaron_al_gusto_fijo",
    "nuggets": "nuggets_fijo",
    # enchiladas se maneja con TAG_SAT_ENCHILADAS (y/o saturday_fixed enchiladas_variante si usas eso)
}

SPECIAL_SLOTS = set([
    "pancita", "paella", "pescado_al_gusto", "camaron_al_gusto", "nuggets",
    "enchiladas", "chamorro", "molcajete", "sopa_pollo"
])

def main():
    with get_conn() as conn:
        conn.execute("BEGIN")

        # 0) Asegura ONLY_SAT para todo lo que haya salido en slots que solo existen sábado
        #    (incluye sopa_pollo también)
        sat_slots = ("pancita", "paella", "pescado_al_gusto", "camaron_al_gusto", "nuggets", "enchiladas", "sopa_pollo")
        inserted_only_sat = conn.execute(
            f"""
            INSERT INTO dish_tag(dish_id, tag)
            SELECT DISTINCT mi.dish_id, ?
            FROM menu_item mi
            WHERE mi.slot IN ({",".join(["?"]*len(sat_slots))})
              AND NOT EXISTS (
                SELECT 1 FROM dish_tag t
                WHERE t.dish_id = mi.dish_id AND t.tag = ?
              )
            """,
            (TAG_ONLY_SAT, *sat_slots, TAG_ONLY_SAT),
        ).rowcount

        # 1) Chamorro (slot chamorro) => tag friday_chamorro
        inserted_chamorro = conn.execute(
            """
            INSERT INTO dish_tag(dish_id, tag)
            SELECT DISTINCT mi.dish_id, ?
            FROM menu_item mi
            WHERE mi.slot = 'chamorro'
              AND NOT EXISTS (
                SELECT 1 FROM dish_tag t
                WHERE t.dish_id = mi.dish_id AND t.tag = ?
              )
            """,
            (TAG_FRIDAY_CHAMORRO, TAG_FRIDAY_CHAMORRO),
        ).rowcount

        # 2) Molcajete (slot molcajete) => tag monday_molcajete
        inserted_molcajete = conn.execute(
            """
            INSERT INTO dish_tag(dish_id, tag)
            SELECT DISTINCT mi.dish_id, ?
            FROM menu_item mi
            WHERE mi.slot = 'molcajete'
              AND NOT EXISTS (
                SELECT 1 FROM dish_tag t
                WHERE t.dish_id = mi.dish_id AND t.tag = ?
              )
            """,
            (TAG_MONDAY_MOLCAJETE, TAG_MONDAY_MOLCAJETE),
        ).rowcount

        # 3) Enchiladas (slot enchiladas) => tag sat_enchiladas
        inserted_enchiladas = conn.execute(
            """
            INSERT INTO dish_tag(dish_id, tag)
            SELECT DISTINCT mi.dish_id, ?
            FROM menu_item mi
            WHERE mi.slot = 'enchiladas'
              AND NOT EXISTS (
                SELECT 1 FROM dish_tag t
                WHERE t.dish_id = mi.dish_id AND t.tag = ?
              )
            """,
            (TAG_SAT_ENCHILADAS, TAG_SAT_ENCHILADAS),
        ).rowcount

        # 4) Saturday_fixed + style_tag para slots que dependen de style_tag
        inserted_sat_fixed = 0
        updated_style = 0

        for slot, style in STYLE_MAP.items():
            # tag saturday_fixed
            inserted_sat_fixed += conn.execute(
                """
                INSERT INTO dish_tag(dish_id, tag)
                SELECT DISTINCT mi.dish_id, ?
                FROM menu_item mi
                WHERE mi.slot = ?
                  AND NOT EXISTS (
                    SELECT 1 FROM dish_tag t
                    WHERE t.dish_id = mi.dish_id AND t.tag = ?
                  )
                """,
                (TAG_SATURDAY_FIXED, slot, TAG_SATURDAY_FIXED),
            ).rowcount

            # style_tag (solo si está NULL / vacío, para no pisar cosas hechas a mano)
            updated_style += conn.execute(
                """
                UPDATE dish
                SET style_tag = ?
                WHERE id IN (SELECT DISTINCT dish_id FROM menu_item WHERE slot = ?)
                  AND (style_tag IS NULL OR TRIM(style_tag) = '')
                """,
                (style, slot),
            ).rowcount

        conn.execute("COMMIT")

    print("OK ✅ backfill special slots")
    print("tag only_sat inserted:", inserted_only_sat)
    print("tag friday_chamorro inserted:", inserted_chamorro)
    print("tag monday_molcajete inserted:", inserted_molcajete)
    print("tag sat_enchiladas inserted:", inserted_enchiladas)
    print("tag saturday_fixed inserted:", inserted_sat_fixed)
    print("dish.style_tag updated:", updated_style)

if __name__ == "__main__":
    main()
