from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db import get_conn

TAG_ONLY_SAT = "only_sat"
TAG_SAT_ENCHILADAS = "sat_enchiladas"
SATURDAY_WEEKDAY = 5
DEFAULT_PRIORITY_WEIGHT = 18


@dataclass(frozen=True)
class DishRule:
    label: str
    like_pattern: str
    required_tags: tuple[str, ...]
    slot: str


SATURDAY_RULES = [
    DishRule("Sabado res", "%Hamburguesa Tradicional%", (TAG_ONLY_SAT,), "fuerte_res"),
    DishRule("Sabado res", "%Tacos Campechanos%", (TAG_ONLY_SAT,), "fuerte_res"),
    DishRule("Sabado res", "%Tipetito de Arrachera%", (TAG_ONLY_SAT,), "fuerte_res"),
    DishRule("Sabado res", "%Tacos Norteño%", (TAG_ONLY_SAT,), "fuerte_res"),
    DishRule("Sabado cerdo", "%Gringa de Pastor%", (TAG_ONLY_SAT,), "fuerte_cerdo"),
    DishRule("Sabado cerdo", "%Costillas Bbq%", (TAG_ONLY_SAT,), "fuerte_cerdo"),
    DishRule("Sabado cerdo", "%Tacos de Pastor%", (TAG_ONLY_SAT,), "fuerte_cerdo"),
    DishRule("Sabado cerdo", "%Tacos de Cochinita%", (TAG_ONLY_SAT,), "fuerte_cerdo"),
    DishRule("Sabado cerdo", "%Taco de Chuleta con Nopales%", (TAG_ONLY_SAT,), "fuerte_cerdo"),
    DishRule("Sabado cerdo", "%Chorizo Argentino%", (TAG_ONLY_SAT,), "fuerte_cerdo"),
    DishRule("Sabado camaron", "%Camarones al Mango%", (TAG_ONLY_SAT,), "camaron_al_gusto"),
    DishRule("Sabado camaron", "%Camarones Hawaianos%", (TAG_ONLY_SAT,), "camaron_al_gusto"),
    DishRule("Sabado camaron", "%Camarones para Pelar%", (TAG_ONLY_SAT,), "camaron_al_gusto"),
    DishRule("Sabado camaron", "%Camarones al Coco%", (TAG_ONLY_SAT,), "camaron_al_gusto"),
    DishRule("Sabado camaron", "%Camarones al Tamarindo Habanero%", (TAG_ONLY_SAT,), "camaron_al_gusto"),
    DishRule("Enchiladas sabado", "%Enchiladas Verdes%", (TAG_ONLY_SAT, TAG_SAT_ENCHILADAS), "enchiladas"),
    DishRule("Enchiladas sabado", "%Enchiladas Rojas%", (TAG_ONLY_SAT, TAG_SAT_ENCHILADAS), "enchiladas"),
    DishRule("Enchiladas sabado", "%Enmoladas%", (TAG_ONLY_SAT, TAG_SAT_ENCHILADAS), "enchiladas"),
    DishRule("Enchiladas sabado", "%Divorciadas%", (TAG_ONLY_SAT, TAG_SAT_ENCHILADAS), "enchiladas"),
    DishRule("Enchiladas sabado", "%Chile Cascabel Gratinadas%", (TAG_ONLY_SAT, TAG_SAT_ENCHILADAS), "enchiladas"),
    DishRule("Enchiladas sabado", "%Enchiladas Suizas%", (TAG_ONLY_SAT, TAG_SAT_ENCHILADAS), "enchiladas"),
    DishRule("Enchiladas sabado", "%Entomatadas Cremosas%", (TAG_ONLY_SAT, TAG_SAT_ENCHILADAS), "enchiladas"),
]


def main() -> None:
    unresolved = [
        "Sabado pollo: 'pechuga de pollo en cualquier modalidad' requiere confirmar si se taggea todo el grupo o una lista cerrada.",
    ]

    matched_rows = []

    with get_conn() as conn:
        for rule in SATURDAY_RULES:
            rows = conn.execute(
                """
                SELECT id, name
                FROM dish
                WHERE active = 1
                  AND name LIKE ?
                ORDER BY id
                """,
                (rule.like_pattern,),
            ).fetchall()

            if not rows:
                unresolved.append(f"Sin match: {rule.like_pattern}")
                continue

            for row in rows:
                dish_id = int(row["id"])
                name = str(row["name"])
                for tag in rule.required_tags:
                    conn.execute(
                        "INSERT OR IGNORE INTO dish_tag(dish_id, tag) VALUES (?, ?)",
                        (dish_id, tag),
                    )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO dish_priority_rule(dish_id, weekday, slot, weight, note)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (dish_id, SATURDAY_WEEKDAY, rule.slot, DEFAULT_PRIORITY_WEIGHT, "saturday_specialty"),
                )
                matched_rows.append((dish_id, name, ", ".join(rule.required_tags), rule.slot))

        conn.commit()

    print("Platillos de sabado etiquetados/priorizados:")
    for dish_id, name, tags, slot in matched_rows:
        print(f"  [{dish_id}] {name} -> {tags} | slot={slot}")

    if unresolved:
        print("\nPendientes / ambiguos:")
        for item in unresolved:
            print(f"  - {item}")


if __name__ == "__main__":
    main()
