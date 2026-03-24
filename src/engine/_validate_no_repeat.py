# src/engine/_validate_no_repeat.py
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta

from src.db import get_conn

WINDOW_DEFAULT = 20
WINDOW_PASTA = 15

# Slots que NO se validan (porque son fijos o se permiten repetir)
EXEMPT_SLOTS = {
    "entrada_comal",  # siempre "Antojitos de comal"
    "arroz",          # fijo (L-V) -> lo ignoramos totalmente
    # Ensaladas: tú quieres patrón A/B/C que se repite
    "ensalada_A",
    "ensalada_B",
    "ensalada_C",
}

# Fijos de sábado: recomendado ignorarlos
EXEMPT_SLOTS |= {
    "pancita",
    "sopa_pollo",
    "paella",
    "pescado_al_gusto",
    "camaron_al_gusto",
    "nuggets",
    "enchiladas",
}


def parse_yyyy_mm_dd(s: str):
    return datetime.strptime(s, "%Y-%m-%d").date()


def main() -> None:
    with get_conn() as conn:
        last = conn.execute(
            "SELECT id, week_start_date, generated_at FROM menu_week ORDER BY id DESC LIMIT 1"
        ).fetchone()

        if not last:
            print("No hay semanas en menu_week.")
            return

        week_id = int(last["id"])
        week_start = last["week_start_date"]
        gen_at = last["generated_at"]

        rows = conn.execute(
            """
            SELECT
                mi.menu_date, mi.slot, mi.dish_id,
                mi.was_exception, mi.exception_reason,
                d.name, d.style_tag
            FROM menu_item mi
            JOIN dish d ON d.id = mi.dish_id
            WHERE mi.menu_week_id = ?
            ORDER BY date(mi.menu_date), mi.slot
            """,
            (week_id,),
        ).fetchall()

    items = [dict(r) for r in rows]

    print(f"Validando semana: id={week_id} start={week_start} generated_at={gen_at}")
    print(f"items: {len(items)}")

    if not items:
        print("⚠ No hay items para esa semana (menu_item vacío).")
        return

    # Conteo por día
    by_day = defaultdict(int)
    for r in items:
        by_day[r["menu_date"]] += 1

    # Historial por "key" para detectar repetición en ventana:
    # key normal: dish:<dish_id>
    # key pasta: style:<style_tag>
    history_by_key: dict[str, deque[tuple]] = defaultdict(deque)
    # deque guarda tuples: (date, slot, name, dish_id, style_tag)

    bad = 0
    exc = 0
    pasta_missing_style = 0

    for r in items:
        slot = r["slot"]

        # contar excepciones marcadas por el motor (aunque sea EXEMPT)
        if int(r.get("was_exception") or 0) == 1:
            exc += 1

        # ignorar slots EXEMPT
        if slot in EXEMPT_SLOTS:
            continue

        d = parse_yyyy_mm_dd(r["menu_date"])
        dish_id = int(r["dish_id"])
        name = r["name"]
        style_tag = r.get("style_tag")

        # Regla de llave + ventana
        if slot == "pasta":
            window = WINDOW_PASTA

            if style_tag:
                key = f"style:{style_tag}"
                key_label = f"style_tag={style_tag}"
            else:
                # fallback (idealmente nunca debería pasar si tus pastas tienen style_tag)
                pasta_missing_style += 1
                key = f"dish:{dish_id}"
                key_label = f"dish_id={dish_id} (fallback; falta style_tag)"
        else:
            window = WINDOW_DEFAULT
            key = f"dish:{dish_id}"
            key_label = f"dish_id={dish_id}"

        start = d - timedelta(days=window)

        dq = history_by_key[key]

        # limpiar items fuera de ventana (<= start no nos sirven)
        while dq and dq[0][0] < start:
            dq.popleft()

        # si queda algo en deque, hay repetición dentro de [start, d)
        # OJO: si el primer item es del mismo día pero en orden anterior, igual contaría;
        # en tu caso no hay slots duplicados del mismo tipo el mismo día, así que ok.
        if dq:
            prev_d, prev_slot, prev_name, prev_dish_id, prev_style = dq[0]
            print(
                f"❌ Violación ventana: {r['menu_date']} slot={slot} {key_label} '{name}' "
                f"repite dentro de {window} días (prev: {prev_d.isoformat()} slot={prev_slot} '{prev_name}')"
            )
            bad += 1

        # agregar esta aparición
        dq.append((d, slot, name, dish_id, style_tag))

    if pasta_missing_style:
        print(
            f"\n⚠ Nota: {pasta_missing_style} pastas no tienen style_tag. "
            f"Se validaron por dish_id (fallback)."
        )

    if bad == 0:
        print("✅ OK: no hay violaciones de ventana (ignorando slots EXEMPT).")
    else:
        print(f"BAD (violaciones ventana): {bad}")

    print(f"EXC (marcados como excepción): {exc}")

    print("\nConteo por día:")
    for day in sorted(by_day.keys()):
        print(f"  {day}: {by_day[day]} items")


if __name__ == "__main__":
    main()
