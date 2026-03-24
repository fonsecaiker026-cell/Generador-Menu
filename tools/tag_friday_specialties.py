from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.engine.dish_manager import create_dish, search_dishes
from src.db import get_conn

TAG_ONLY_FRI = "only_fri"
FRIDAY_WEEKDAY = 4
DEFAULT_PRIORITY_WEIGHT = 18


@dataclass(frozen=True)
class FridayDish:
    name: str
    course_group: str
    protein: str
    style_tag: str
    slot: str


FRIDAY_DISHES = [
    FridayDish("Galleta de Atun", "entrada_no_comal", "none", "galleta_de_atun", "entrada_no_comal"),
    FridayDish("Pescaditos Rebozados", "entrada_no_comal", "none", "pescaditos_rebozados", "entrada_no_comal"),
    FridayDish("Tostada de Pata", "entrada_no_comal", "none", "tostada_de_pata", "entrada_no_comal"),
    FridayDish("Taco de Rajas con Crema", "entrada_no_comal", "none", "taco_de_rajas_con_crema", "entrada_no_comal"),
    FridayDish("Gordita", "entrada_no_comal", "none", "gordita", "entrada_no_comal"),
    FridayDish("Galleta o Mini Tostada de Ensalada de Surimi", "entrada_no_comal", "none", "galleta_mini_tostada_ensalada_surimi", "entrada_no_comal"),
    FridayDish("Tlacoyo", "entrada_no_comal", "none", "tlacoyo", "entrada_no_comal"),
    FridayDish("Crema de Elote", "crema", "none", "crema_de_elote", "crema"),
    FridayDish("Crema Conde", "crema", "none", "crema_conde", "crema"),
    FridayDish("Crema de Queso", "crema", "none", "crema_de_queso", "crema"),
    FridayDish("Crema Poblana", "crema", "none", "crema_poblana", "crema"),
    FridayDish("Crema de Almeja", "crema", "pescado", "crema_de_almeja", "crema"),
    FridayDish("Sopa de Mariscos", "sopa", "pescado", "sopa_de_mariscos", "sopa"),
    FridayDish("Chilpachole de Jaiba", "sopa", "pescado", "chilpachole_de_jaiba", "sopa"),
    FridayDish("Consome de Birria de Res", "sopa", "res", "consome_de_birria_de_res", "sopa"),
    FridayDish("Jugo de Carne", "sopa", "res", "jugo_de_carne", "sopa"),
    FridayDish("Caldo de Camaron", "sopa", "camaron", "caldo_de_camaron", "sopa"),
    FridayDish("Pozole de Cerdo", "sopa", "cerdo", "pozole_de_cerdo", "sopa"),
    FridayDish("Milanesa de Res con Ensalada", "fuerte", "res", "milanesa_de_res_con_ensalada", "fuerte_res"),
    FridayDish("Entomatado de Res", "fuerte", "res", "entomatado_de_res", "fuerte_res"),
    FridayDish("Tacos de Birria de Res", "fuerte", "res", "tacos_de_birria_de_res", "fuerte_res"),
    FridayDish("Albondigas al Chipotle", "fuerte", "res", "albondigas_al_chipotle", "fuerte_res"),
    FridayDish("Mole de Olla", "fuerte", "res", "mole_de_olla", "fuerte_res"),
    FridayDish("Machitos de Carnero", "complemento", "none", "machitos_de_carnero", "complemento"),
    FridayDish("Higado Encebollado", "complemento", "none", "higado_encebollado", "complemento"),
    FridayDish("Chile Relleno de Queso", "complemento", "none", "chile_relleno_de_queso", "complemento"),
    FridayDish("Pata en Salsa Verde", "complemento", "cerdo", "pata_en_salsa_verde", "complemento"),
    FridayDish("Romeritos", "complemento", "none", "romeritos", "complemento"),
    FridayDish("Manitas de Cerdo a la Vinagreta", "complemento", "cerdo", "manitas_de_cerdo_a_la_vinagreta", "complemento"),
    FridayDish("Manitas de Cerdo al Pibil", "complemento", "cerdo", "manitas_de_cerdo_al_pibil", "complemento"),
    FridayDish("Camarones Roca", "fuerte", "camaron", "camarones_roca", "fuerte_camaron"),
    FridayDish("Camarones Momia", "fuerte", "camaron", "camarones_momia", "fuerte_camaron"),
    FridayDish("Camarones Empanizados", "fuerte", "camaron", "camarones_empanizados", "fuerte_camaron"),
    FridayDish("Camarones Enchilados al Sarten con Queso", "fuerte", "camaron", "camarones_enchilados_al_sarten_con_queso", "fuerte_camaron"),
    FridayDish("Camarones Poblanos", "fuerte", "camaron", "camarones_poblanos", "fuerte_camaron"),
    FridayDish("Camarones a la Mexicana", "fuerte", "camaron", "camarones_a_la_mexicana", "fuerte_camaron"),
    FridayDish("Rockefeller", "fuerte", "pescado", "rockefeller", "fuerte_pescado"),
    FridayDish("Salsa Cremosa e Chipotle", "fuerte", "pescado", "salsa_cremosa_e_chipotle", "fuerte_pescado"),
    FridayDish("Empanizado con Ensalada", "fuerte", "pescado", "empanizado_con_ensalada", "fuerte_pescado"),
    FridayDish("Salsa Cremosa de Champiñon", "fuerte", "pescado", "salsa_cremosa_de_champinon", "fuerte_pescado"),
    FridayDish("Empanizado Gratinado", "fuerte", "pescado", "empanizado_gratinado", "fuerte_pescado"),
]


def main() -> None:
    created = []
    tagged = []

    for item in FRIDAY_DISHES:
        existing_any = search_dishes(
            query=item.name,
            active=None,
        )
        exact_any = next((d for d in existing_any if d["name"] == item.name), None)
        if exact_any:
            dish_id = int(exact_any["id"])
            with get_conn() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO dish_tag(dish_id, tag) VALUES (?, ?)",
                    (dish_id, TAG_ONLY_FRI),
                )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO dish_priority_rule(dish_id, weekday, slot, weight, note)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (dish_id, FRIDAY_WEEKDAY, item.slot, DEFAULT_PRIORITY_WEIGHT, "friday_specialty"),
                )
                conn.commit()
            tagged.append((dish_id, item.name))
            continue

        existing = search_dishes(
            query=item.name,
            course_group=item.course_group,
            protein=item.protein,
            active=None,
        )
        exact = next((d for d in existing if d["name"] == item.name), None)

        if exact:
            dish_id = int(exact["id"])
            with get_conn() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO dish_tag(dish_id, tag) VALUES (?, ?)",
                    (dish_id, TAG_ONLY_FRI),
                )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO dish_priority_rule(dish_id, weekday, slot, weight, note)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (dish_id, FRIDAY_WEEKDAY, item.slot, DEFAULT_PRIORITY_WEIGHT, "friday_specialty"),
                )
                conn.commit()
            tagged.append((dish_id, item.name))
            continue

        dish_id = create_dish(
            name=item.name,
            course_group=item.course_group,
            protein=item.protein,
            style_tag=item.style_tag,
            sauce_tag=None,
            tags=[TAG_ONLY_FRI],
        )
        with get_conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO dish_priority_rule(dish_id, weekday, slot, weight, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (dish_id, FRIDAY_WEEKDAY, item.slot, DEFAULT_PRIORITY_WEIGHT, "friday_specialty"),
            )
            conn.commit()
        created.append((dish_id, item.name))

    print("Etiquetados only_fri:")
    for dish_id, name in tagged:
        print(f"  [{dish_id}] {name}")

    print("\nCreados y etiquetados only_fri:")
    for dish_id, name in created:
        print(f"  [{dish_id}] {name}")


if __name__ == "__main__":
    main()
