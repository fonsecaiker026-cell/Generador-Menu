# src/engine/generator.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import random
from typing import Optional

from src.db import get_conn
from src.engine.slots import slots_for_day

# =========================
# Constantes del proyecto
# =========================
WINDOW_DEFAULT = 20
WINDOW_PASTA = 15
WINDOW_SAUCE = 20  # ventana de rotación de sauce_tag (cross-slot, cross-course_group)
WINDOW_BEEF_CUT = 10  # ventana cross-semanas para cortes de res (L-V); evita mismo corte semanas consecutivas

# Fijos
DISH_ID_ARROZ_AL_GUSTO = 1596
DISH_ID_ANTOJITOS_COMAL = 202

# style_tags para fijos de sábado
STYLE_PAELLA_FIJA = "paella_fija"
STYLE_NUGGETS_FIJO = "nuggets_fijo"
STYLE_PESCADO_AL_GUSTO_FIJO = "pescado_al_gusto_fijo"
STYLE_CAMARON_AL_GUSTO_FIJO = "camaron_al_gusto_fijo"
STYLE_PANCITA_FIJA = "pancita_fija"

# Tags de exclusividad por día
TAG_ONLY_FRI = "only_fri"
TAG_ONLY_SAT = "only_sat"

# Tags especiales
TAG_MONDAY_MOLCAJETE = "monday_molcajete"
TAG_SATURDAY_FIXED = "saturday_fixed"
TAG_SAT_ENCHILADAS = "sat_enchiladas"
TAG_FRIDAY_CHAMORRO = "friday_chamorro"

DAY_PRIORITY_TAG_BOOST = 8

# Slots fijos (no se eligen; siempre el mismo dish / style)
FIXED_SLOTS = {
    "entrada_comal",
    "arroz",
    "paella",
    "nuggets",
    "pancita",
}

# Slots que deben traer la leyenda "o al gusto"
AL_GUSTO_SLOTS = {"pescado_al_gusto", "camaron_al_gusto"}

# =========================
# Ensaladas semanales (3 por semana)
# =========================
SALAD_ANCHOR_OFFSET = {
    "ensalada_A": 0,  # lunes
    "ensalada_B": 1,  # martes
    "ensalada_C": 2,  # miércoles
}

SALAD_DAYS_BY_SLOT = {
    "ensalada_A": (0, 3),  # lun/jue
    "ensalada_B": (1, 4),  # mar/vie
    "ensalada_C": (2, 5),  # mié/sáb
}

SALAD_SLOTS = set(SALAD_ANCHOR_OFFSET.keys())

# Slots con rotación 0 (si no, se quedan sin candidatos fácil)
NO_ROTATION_SLOTS = {
    "chamorro",
    "pancita",
    "paella",
    "nuggets",
    "entrada_comal",
    # "enchiladas",  # opcional si quieres que nunca se bloquee por ventana
}

# =========================
# Date helpers
# =========================
def parse_yyyy_mm_dd(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def to_yyyy_mm_dd(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def ensure_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


# =========================
# DB helpers
# =========================
def fetch_one(conn, q: str, params=()):
    return conn.execute(q, params).fetchone()


def fetch_all(conn, q: str, params=()):
    return conn.execute(q, params).fetchall()


def dish_name(conn, dish_id: int) -> str:
    row = fetch_one(conn, "SELECT name FROM dish WHERE id=?", (int(dish_id),))
    return row["name"] if row else f"(dish_id={dish_id})"


def dish_is_active(conn, dish_id: int) -> bool:
    r = fetch_one(conn, "SELECT 1 AS ok FROM dish WHERE id=? AND active=1", (int(dish_id),))
    return bool(r)


def get_override(conn, day: date, slot: str):
    return fetch_one(
        conn,
        "SELECT forced_dish_id, blocked_dish_id FROM menu_override WHERE menu_date=? AND slot=?",
        (to_yyyy_mm_dd(day), slot),
    )


def insert_or_update_menu_week(conn, week_start: date) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO menu_week(week_start_date, generated_at, finalized, notes)
        VALUES (?, ?, 0, NULL)
        ON CONFLICT(week_start_date) DO UPDATE SET
          generated_at=excluded.generated_at
        """,
        (to_yyyy_mm_dd(week_start), now),
    )
    row = fetch_one(conn, "SELECT id FROM menu_week WHERE week_start_date = ?", (to_yyyy_mm_dd(week_start),))
    if not row:
        raise RuntimeError("No se pudo crear/leer menu_week. Revisa schema/DB.")
    return int(row["id"])


def clear_week_items(conn, week_id: int):
    conn.execute("DELETE FROM menu_item WHERE menu_week_id = ?", (int(week_id),))


def clear_day_items(conn, week_id: int, day: date):
    conn.execute(
        "DELETE FROM menu_item WHERE menu_week_id=? AND menu_date=?",
        (int(week_id), to_yyyy_mm_dd(day)),
    )


def delete_item(conn, week_id: int, day: date, slot: str) -> None:
    conn.execute(
        "DELETE FROM menu_item WHERE menu_week_id=? AND menu_date=? AND slot=?",
        (int(week_id), to_yyyy_mm_dd(day), slot),
    )


# =========================
# Result model
# =========================
@dataclass
class PickResult:
    dish_id: int
    explanation: str
    was_exception: bool = False
    exception_reason: Optional[str] = None
    is_forced: bool = False


def save_item(conn, week_id: int, day: date, slot: str, pick: PickResult):
    conn.execute(
        """
        INSERT OR REPLACE INTO menu_item(
            menu_week_id, menu_date, slot, dish_id,
            is_forced, was_exception, exception_reason, explanation
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(week_id),
            to_yyyy_mm_dd(day),
            slot,
            int(pick.dish_id),
            1 if pick.is_forced else 0,
            1 if pick.was_exception else 0,
            pick.exception_reason,
            pick.explanation,
        ),
    )


# =========================
# Season & lock helpers
# =========================
def _month_in_range(month: int, start: int, end: int) -> bool:
    """True si `month` cae dentro del rango [start, end], soportando rangos que cruzan año."""
    if start <= end:
        return start <= month <= end
    # cruza fin de año, ej: noviembre(11) → febrero(2)
    return month >= start or month <= end


def _blocked_by_season(conn, dish_ids: list[int], day: date) -> set[int]:
    """
    Devuelve los dish_ids que tienen dish_season.rule='BLOCK' para el mes actual.
    Los WARN se ignoran aquí (solo se bloquean los BLOCK).
    """
    if not dish_ids:
        return set()
    month = day.month
    qmarks = ",".join(["?"] * len(dish_ids))
    rows = conn.execute(
        f"""
        SELECT dish_id, start_month, end_month
        FROM dish_season
        WHERE rule = 'BLOCK'
          AND dish_id IN ({qmarks})
        """,
        tuple(dish_ids),
    ).fetchall()
    blocked = set()
    for r in rows:
        if _month_in_range(month, r["start_month"], r["end_month"]):
            blocked.add(int(r["dish_id"]))
    return blocked


def _blocked_by_lock(conn, dish_ids: list[int], day: date) -> set[int]:
    """
    Devuelve los dish_ids que tienen un dish_lock BLOCK activo para `day`.
    Un lock sin start_date o sin end_date se considera abierto por ese extremo.
    """
    if not dish_ids:
        return set()
    day_str = to_yyyy_mm_dd(day)
    qmarks = ",".join(["?"] * len(dish_ids))
    rows = conn.execute(
        f"""
        SELECT dish_id
        FROM dish_lock
        WHERE lock_type = 'BLOCK'
          AND dish_id IN ({qmarks})
          AND (start_date IS NULL OR start_date <= ?)
          AND (end_date   IS NULL OR end_date   >= ?)
        """,
        (*tuple(dish_ids), day_str, day_str),
    ).fetchall()
    return {int(r["dish_id"]) for r in rows}


def filter_season_and_lock(conn, cand: list[dict], day: date) -> list[dict]:
    """
    Elimina candidatos que estén bloqueados por temporada (dish_season BLOCK)
    o por un dish_lock BLOCK activo en `day`.
    """
    if not cand:
        return []
    ids = [int(c["id"]) for c in cand]
    seasonal_blocked = _blocked_by_season(conn, ids, day)
    lock_blocked = _blocked_by_lock(conn, ids, day)
    blocked = seasonal_blocked | lock_blocked
    if not blocked:
        return cand
    return [c for c in cand if int(c["id"]) not in blocked]


def _priority_boosts_by_dish(conn, dish_ids: list[int], day: date, slot: str) -> dict[int, int]:
    """
    Return additive priority weights for candidate dishes.

    Priority can come from:
    - day-only tags (`only_fri`, `only_sat`) when used on the matching day
    - explicit rows in `dish_priority_rule` matching weekday and/or slot
    """
    if not dish_ids:
        return {}

    qmarks = ",".join(["?"] * len(dish_ids))
    weekday = day.weekday()
    boosts: dict[int, int] = {int(did): 0 for did in dish_ids}

    tag_rows = conn.execute(
        f"""
        SELECT dish_id, tag
        FROM dish_tag
        WHERE dish_id IN ({qmarks})
          AND tag IN (?, ?)
        """,
        (*dish_ids, TAG_ONLY_FRI, TAG_ONLY_SAT),
    ).fetchall()
    for row in tag_rows:
        dish_id = int(row["dish_id"])
        tag = str(row["tag"])
        if tag == TAG_ONLY_FRI and weekday == 4:
            boosts[dish_id] = boosts.get(dish_id, 0) + DAY_PRIORITY_TAG_BOOST
        elif tag == TAG_ONLY_SAT and weekday == 5:
            boosts[dish_id] = boosts.get(dish_id, 0) + DAY_PRIORITY_TAG_BOOST

    priority_rows = conn.execute(
        f"""
        SELECT dish_id, weekday, slot, weight
        FROM dish_priority_rule
        WHERE dish_id IN ({qmarks})
          AND (weekday IS NULL OR weekday = ?)
          AND (slot IS NULL OR slot = ?)
        """,
        (*dish_ids, weekday, slot),
    ).fetchall()
    for row in priority_rows:
        dish_id = int(row["dish_id"])
        boosts[dish_id] = boosts.get(dish_id, 0) + int(row["weight"] or 0)

    return boosts


def _weighted_choice(conn, cand: list[dict], day: date, slot: str, rng: random.Random) -> dict:
    """Choose one candidate using additive priority weights; falls back to uniform random."""
    if len(cand) == 1:
        return cand[0]

    boosts = _priority_boosts_by_dish(conn, [int(x["id"]) for x in cand], day, slot)
    weights = [max(1, 1 + int(boosts.get(int(x["id"]), 0))) for x in cand]

    if len(set(weights)) == 1:
        return rng.choice(cand)

    total = sum(weights)
    pick = rng.uniform(0, total)
    acc = 0.0
    for candidate, weight in zip(cand, weights):
        acc += weight
        if pick <= acc:
            return candidate
    return cand[-1]


# =========================
# Day-only filter (only_sat / only_fri)
# =========================
def filter_day_only(conn, cand: list[dict], day: date, slot: str) -> list[dict]:
    """
    Reglas:
    - Los platillos con tag de exclusividad solo pueden salir en su día.
    - Esto aplica aunque el slot también exista entre semana.
    """
    if not cand:
        return []

    weekday = day.weekday()

    ids = [int(c["id"]) for c in cand]
    qmarks = ",".join(["?"] * len(ids))

    rows = conn.execute(
        f"""
        SELECT dish_id, tag
        FROM dish_tag
        WHERE tag IN (?, ?)
          AND dish_id IN ({qmarks})
        """,
        (TAG_ONLY_SAT, TAG_ONLY_FRI, *ids),
    ).fetchall()

    restricted_tags_by_dish: dict[int, set[str]] = {}
    for r in rows:
        restricted_tags_by_dish.setdefault(int(r["dish_id"]), set()).add(str(r["tag"]))

    out = []
    for c in cand:
        did = int(c["id"])
        tags = restricted_tags_by_dish.get(did, set())
        if TAG_ONLY_SAT in tags and weekday != 5:
            continue
        if TAG_ONLY_FRI in tags and weekday != 4:
            continue
        out.append(c)

    return out


# =========================
# Candidate lookup (NO rota aquí)
# =========================
def candidates(conn, slot: str, day: date) -> list[dict]:
    """
    IMPORTANTE:
    - Aquí NO aplicamos ventana de rotación.
    - Solo construimos el catálogo por slot + reglas de día.
    - La rotación real se aplica en pick_strict() con window_days (y ahí sí sirve relaxation).
    """
    rows = []

    # Slots directos por course_group
    if slot in {"crema", "pasta", "entrada_no_comal"}:
        rows = fetch_all(
            conn,
            """
            SELECT id, name, course_group, protein, style_tag, sauce_tag
            FROM dish
            WHERE active=1 AND course_group=?
            """,
            (slot,),
        )

    elif slot == "sopa":
        # Sopas de pollo son exclusivas del sábado (slot sopa_pollo)
        rows = fetch_all(
            conn,
            """
            SELECT id, name, course_group, protein, style_tag, sauce_tag
            FROM dish
            WHERE active=1 AND course_group='sopa' AND protein != 'pollo'
            """,
        )

    elif slot == "complemento":
        rows = fetch_all(
            conn,
            """
            SELECT DISTINCT d.id, d.name, d.course_group, d.protein, d.style_tag, d.sauce_tag
            FROM dish d
            LEFT JOIN dish_tag t ON t.dish_id = d.id
            WHERE d.active=1
              AND (
                    d.course_group='complemento'
                    OR t.tag='also_complemento'
              )
            """,
        )

    elif slot == "entrada_comal":
        rows = []  # NO editable

    elif slot.startswith("ensalada_"):
        rows = fetch_all(
            conn,
            """
            SELECT id, name, course_group, protein, style_tag, sauce_tag
            FROM dish
            WHERE active=1 AND course_group='ensalada'
            """,
        )

    elif slot.startswith("fuerte_"):
        prot = slot.replace("fuerte_", "")
        rows = fetch_all(
            conn,
            """
            SELECT id, name, course_group, protein, style_tag, sauce_tag
            FROM dish
            WHERE active=1
              AND course_group='fuerte'
              AND protein=?
              AND id NOT IN (SELECT dish_id FROM dish_tag WHERE tag=?)
            """,
            (prot, TAG_MONDAY_MOLCAJETE),
        )

    elif slot == "molcajete":
        rows = fetch_all(
            conn,
            """
            SELECT d.id, d.name, d.course_group, d.protein, d.style_tag, d.sauce_tag
            FROM dish d
            JOIN dish_tag t ON t.dish_id=d.id
            WHERE d.active=1
              AND t.tag=?
              AND d.protein IS NOT NULL
              AND d.protein != 'none'
            """,
            (TAG_MONDAY_MOLCAJETE,),
        )

    elif slot == "chamorro":
        rows = fetch_all(
            conn,
            """
            SELECT d.id, d.name, d.course_group, d.protein, d.style_tag, d.sauce_tag
            FROM dish d
            JOIN dish_tag t ON t.dish_id=d.id
            WHERE d.active=1
              AND d.course_group='fuerte'
              AND t.tag=?
            """,
            (TAG_FRIDAY_CHAMORRO,),
        )

    elif slot == "enchiladas":
        rows = fetch_all(
            conn,
            """
            SELECT d.id, d.name, d.course_group, d.protein, d.style_tag, d.sauce_tag
            FROM dish d
            JOIN dish_tag t ON t.dish_id=d.id
            WHERE d.active=1 AND t.tag=?
            """,
            (TAG_SAT_ENCHILADAS,),
        )

        # fallback por si existía formato anterior:
        if not rows:
            rows = fetch_all(
                conn,
                """
                SELECT d.id, d.name, d.course_group, d.protein, d.style_tag, d.sauce_tag
                FROM dish d
                JOIN dish_tag t ON t.dish_id=d.id
                WHERE d.active=1 AND t.tag=? AND d.style_tag=?
                """,
                (TAG_SATURDAY_FIXED, "enchiladas_variante"),
            )

    elif slot == "sopa_pollo":
        rows = fetch_all(
            conn,
            """
            SELECT DISTINCT d.id, d.name, d.course_group, d.protein, d.style_tag, d.sauce_tag
            FROM dish d
            LEFT JOIN dish_tag t
                ON t.dish_id = d.id
                AND t.tag = ?
            WHERE d.active=1
              AND d.course_group='sopa'
              AND (d.protein='pollo' OR t.tag IS NOT NULL)
              AND (d.style_tag IS NULL OR d.style_tag != 'pancita')
            """,
            (TAG_ONLY_SAT,),
        )

    elif slot == "pescado_al_gusto":
        rows = fetch_all(
            conn,
            """
            SELECT id, name, course_group, protein, style_tag, sauce_tag
            FROM dish
            WHERE active=1
              AND course_group='fuerte'
              AND protein='pescado'
              AND id NOT IN (SELECT dish_id FROM dish_tag WHERE tag=?)
            """,
            (TAG_MONDAY_MOLCAJETE,),
        )

    elif slot == "camaron_al_gusto":
        rows = fetch_all(
            conn,
            """
            SELECT id, name, course_group, protein, style_tag, sauce_tag
            FROM dish
            WHERE active=1
              AND course_group='fuerte'
              AND protein='camaron'
              AND id NOT IN (SELECT dish_id FROM dish_tag WHERE tag=?)
            """,
            (TAG_MONDAY_MOLCAJETE,),
        )

    # slots fijos por tag+style_tag (solo catálogo para UI / debug; generación usa pick_fixed())
    else:
        saturday_style_map = {
            "pancita": STYLE_PANCITA_FIJA,
            "paella": STYLE_PAELLA_FIJA,
            "pescado_al_gusto": STYLE_PESCADO_AL_GUSTO_FIJO,
            "camaron_al_gusto": STYLE_CAMARON_AL_GUSTO_FIJO,
            "nuggets": STYLE_NUGGETS_FIJO,
        }
        if slot in saturday_style_map:
            style = saturday_style_map[slot]
            rows = fetch_all(
                conn,
                """
                SELECT d.id, d.name, d.course_group, d.protein, d.style_tag, d.sauce_tag
                FROM dish d
                JOIN dish_tag t ON t.dish_id=d.id
                WHERE d.active=1 AND t.tag=? AND d.style_tag=?
                """,
                (TAG_SATURDAY_FIXED, style),
            )

    cand = [dict(r) for r in rows] if rows else []
    cand = filter_day_only(conn, cand, day, slot)
    cand = filter_season_and_lock(conn, cand, day)
    return cand


# =========================
# Repeat windows (para relaxation)
# =========================
def window_days_for_slot(slot: str) -> int:
    if slot in NO_ROTATION_SLOTS:
        return 0
    return WINDOW_PASTA if slot == "pasta" else WINDOW_DEFAULT


# Slots que comparten el mismo pool de dishes y no deben repetir entre sí.
# Ej: fuerte_pescado y pescado_al_gusto ambos usan dishes de protein=pescado.
_SISTER_SLOTS: dict[str, tuple[str, ...]] = {
    "fuerte_pescado":  ("pescado_al_gusto",),
    "pescado_al_gusto": ("fuerte_pescado",),
    "fuerte_camaron":  ("camaron_al_gusto",),
    "camaron_al_gusto": ("fuerte_camaron",),
}


def recent_dish_ids(conn, day: date, window_days: int, *, slot: str, exclude_week_id: Optional[int] = None) -> set[int]:
    """
    Rotación correcta:
    - MISMO slot + sister slots (misma proteína) para evitar colisión cross-slot
    - SOLO fechas anteriores al día (menu_date < day)
    - ventana [day-window, day)
    - puede excluir week_id (regenerar sin auto-bloquear)
    """
    if window_days <= 0:
        return set()

    slots_to_check = [slot] + list(_SISTER_SLOTS.get(slot, ()))
    qmarks = ",".join("?" * len(slots_to_check))
    start = day - timedelta(days=window_days)
    sql = f"""
        SELECT DISTINCT mi.dish_id
        FROM menu_item mi
        WHERE mi.slot IN ({qmarks})
          AND date(mi.menu_date) >= date(?)
          AND date(mi.menu_date) <  date(?)
    """
    params: list = [*slots_to_check, to_yyyy_mm_dd(start), to_yyyy_mm_dd(day)]

    if exclude_week_id is not None:
        sql += " AND mi.menu_week_id != ?"
        params.append(int(exclude_week_id))

    rows = fetch_all(conn, sql, tuple(params))
    return {int(r["dish_id"]) for r in rows}


def recent_pasta_styles(conn, day: date, window_days: int, *, exclude_week_id: Optional[int] = None) -> set[str]:
    if window_days <= 0:
        return set()

    start = day - timedelta(days=window_days)
    sql = """
        SELECT DISTINCT d.style_tag
        FROM menu_item mi
        JOIN dish d ON d.id = mi.dish_id
        WHERE date(mi.menu_date) >= date(?)
          AND date(mi.menu_date) <  date(?)
          AND d.style_tag IS NOT NULL
          AND d.course_group = 'pasta'
    """
    params = [to_yyyy_mm_dd(start), to_yyyy_mm_dd(day)]

    if exclude_week_id is not None:
        sql += " AND mi.menu_week_id != ?"
        params.append(int(exclude_week_id))

    rows = fetch_all(conn, sql, tuple(params))
    return {r["style_tag"] for r in rows}


# =========================
# Sauce-tag rotation helpers
# =========================
def recent_sauce_tags(
    conn,
    day: date,
    window_days: int,
    *,
    exclude_week_id: Optional[int] = None,
) -> set[str]:
    """
    Sauce_tags usadas en CUALQUIER slot en los últimos window_days días (cross-slot).
    Si un platillo tiene sauce_tag, no puede repetirse la misma salsa en ningún slot
    dentro de la ventana de rotación.
    """
    if window_days <= 0:
        return set()

    start = day - timedelta(days=window_days)
    sql = """
        SELECT DISTINCT d.sauce_tag
        FROM menu_item mi
        JOIN dish d ON d.id = mi.dish_id
        WHERE d.sauce_tag IS NOT NULL
          AND date(mi.menu_date) >= date(?)
          AND date(mi.menu_date) <  date(?)
    """
    params: list = [to_yyyy_mm_dd(start), to_yyyy_mm_dd(day)]

    if exclude_week_id is not None:
        sql += " AND mi.menu_week_id != ?"
        params.append(int(exclude_week_id))

    rows = fetch_all(conn, sql, tuple(params))
    return {r["sauce_tag"] for r in rows}


def week_sauce_tags(conn, week_id: int) -> set[str]:
    """
    Sauce_tags ya asignadas en la semana actual (cualquier slot ya guardado).
    Se recalcula en cada slot para reflejar lo que ya se eligió hoy y días anteriores.
    """
    rows = fetch_all(
        conn,
        """
        SELECT DISTINCT d.sauce_tag
        FROM menu_item mi
        JOIN dish d ON d.id = mi.dish_id
        WHERE mi.menu_week_id = ?
          AND d.sauce_tag IS NOT NULL
        """,
        (int(week_id),),
    )
    return {r["sauce_tag"] for r in rows}


def week_non_fixed_dish_ids_used(conn, week_id: int) -> frozenset[int]:
    """
    Dish IDs already used this week in non-fixed slots.
    Used to discourage intra-week dish repetition across different slots.
    """
    fixed_qmarks = ",".join("?" * len(FIXED_SLOTS))
    rows = fetch_all(
        conn,
        f"""
        SELECT DISTINCT dish_id
        FROM menu_item
        WHERE menu_week_id = ?
          AND slot NOT IN ({fixed_qmarks})
        """,
        (int(week_id), *tuple(FIXED_SLOTS)),
    )
    return frozenset(int(r["dish_id"]) for r in rows)


def build_blocked_sauce_tags(
    conn,
    week_id: int,
    day: date,
    exclude_week_id_for_rotation: Optional[int] = None,
) -> frozenset[str]:
    """
    Combina salsas recientes (ventana cross-semanas) con salsas ya usadas esta semana.
    El resultado es el conjunto de sauce_tags que NO pueden usarse en el siguiente pick.
    """
    cross_week = recent_sauce_tags(
        conn, day, WINDOW_SAUCE, exclude_week_id=exclude_week_id_for_rotation
    )
    this_week = week_sauce_tags(conn, week_id)
    return frozenset(cross_week | this_week)


# =========================
# Beef cut rotation helpers
# =========================

# Slots que cuentan para el bloqueo de corte de res
_RES_SLOTS = {"fuerte_res", "molcajete"}


def week_beef_cuts_used(conn, week_id: int) -> frozenset[int]:
    """
    Devuelve los beef_cut_id usados en slots de res (fuerte_res + molcajete) esta semana.
    Se usa para evitar que el mismo corte aparezca dos veces en la semana.
    """
    rows = fetch_all(
        conn,
        f"""
        SELECT DISTINCT dbc.beef_cut_id
        FROM menu_item mi
        JOIN dish_beef_cut dbc ON dbc.dish_id = mi.dish_id
        WHERE mi.menu_week_id = ?
          AND mi.slot IN ({','.join('?' * len(_RES_SLOTS))})
        """,
        (int(week_id), *_RES_SLOTS),
    )
    return frozenset(int(r["beef_cut_id"]) for r in rows)


def _apply_beef_cut_filter(conn, cand: list[dict], blocked_cut_ids: frozenset[int]) -> list[dict]:
    """
    Excluye candidatos que comparten algún corte de res ya usado esta semana.
    Dishes sin corte asignado (guisados, caldos) siempre pasan.
    """
    if not blocked_cut_ids or not cand:
        return cand

    dish_ids = [int(c["id"]) for c in cand]
    qmarks = ",".join("?" * len(dish_ids))
    cut_qmarks = ",".join("?" * len(blocked_cut_ids))

    rows = fetch_all(
        conn,
        f"""
        SELECT DISTINCT dish_id
        FROM dish_beef_cut
        WHERE dish_id IN ({qmarks})
          AND beef_cut_id IN ({cut_qmarks})
        """,
        (*dish_ids, *blocked_cut_ids),
    )
    blocked_dish_ids = {int(r["dish_id"]) for r in rows}
    return [c for c in cand if int(c["id"]) not in blocked_dish_ids]


def recent_beef_cut_ids(
    conn,
    day: date,
    window_days: int,
    *,
    exclude_week_id: Optional[int] = None,
) -> frozenset[int]:
    """
    Cortes de res (beef_cut_id) usados en _RES_SLOTS en los últimos window_days días.
    Solo días L-V (weekday 0-4): el sábado no cuenta para esta ventana.
    """
    if window_days <= 0:
        return frozenset()

    start = day - timedelta(days=window_days)
    slots_qmarks = ",".join("?" * len(_RES_SLOTS))
    sql = f"""
        SELECT DISTINCT dbc.beef_cut_id
        FROM menu_item mi
        JOIN dish_beef_cut dbc ON dbc.dish_id = mi.dish_id
        WHERE mi.slot IN ({slots_qmarks})
          AND date(mi.menu_date) >= date(?)
          AND date(mi.menu_date) <  date(?)
          AND strftime('%w', mi.menu_date) NOT IN ('0', '6')  -- excluye dom y sáb
    """
    params: list = [*_RES_SLOTS, to_yyyy_mm_dd(start), to_yyyy_mm_dd(day)]

    if exclude_week_id is not None:
        sql += " AND mi.menu_week_id != ?"
        params.append(int(exclude_week_id))

    rows = fetch_all(conn, sql, tuple(params))
    return frozenset(int(r["beef_cut_id"]) for r in rows)


def build_blocked_beef_cut_ids(
    conn,
    week_id: int,
    day: date,
    *,
    exclude_week_id_for_rotation: Optional[int] = None,
) -> frozenset[int]:
    """
    Combina cortes bloqueados intra-semana (semana actual) con los de semanas recientes
    (ventana WINDOW_BEEF_CUT días hacia atrás, excluye sábados).
    Se usa en slots _RES_SLOTS (fuerte_res, molcajete) en días L-V.
    """
    intra_week = week_beef_cuts_used(conn, week_id)
    cross_week = recent_beef_cut_ids(
        conn, day, WINDOW_BEEF_CUT,
        exclude_week_id=exclude_week_id_for_rotation,
    )
    return intra_week | cross_week


# =========================
# Pasta tipo intra-week rotation helpers
# =========================

def week_pasta_tipos_used(conn, week_id: int) -> frozenset[str]:
    """
    Returns pasta_tipo_* tags already used in the pasta slot this week.
    Prevents the same pasta type (espagueti, codito, etc.) from appearing
    more than once in a week.
    """
    rows = fetch_all(
        conn,
        """
        SELECT DISTINCT t.tag
        FROM menu_item mi
        JOIN dish_tag t ON t.dish_id = mi.dish_id AND t.tag LIKE 'pasta_tipo_%'
        WHERE mi.menu_week_id = ?
          AND mi.slot = 'pasta'
        """,
        (int(week_id),),
    )
    return frozenset(r["tag"] for r in rows)


def _apply_pasta_tipo_filter(conn, cand: list[dict], blocked_pasta_tipos: frozenset[str]) -> list[dict]:
    """
    Excludes pasta candidates whose pasta_tipo_* tag is already used this week.
    Dishes without a pasta_tipo_* tag always pass (they can appear freely).
    """
    if not blocked_pasta_tipos or not cand:
        return cand

    dish_ids = [int(c["id"]) for c in cand]
    qmarks = ",".join("?" * len(dish_ids))
    tipo_qmarks = ",".join("?" * len(blocked_pasta_tipos))

    rows = fetch_all(
        conn,
        f"""
        SELECT DISTINCT dish_id
        FROM dish_tag
        WHERE dish_id IN ({qmarks})
          AND tag IN ({tipo_qmarks})
        """,
        (*dish_ids, *blocked_pasta_tipos),
    )
    blocked_dish_ids = {int(r["dish_id"]) for r in rows}
    return [c for c in cand if int(c["id"]) not in blocked_dish_ids]


# =========================
# Picker
# =========================
def pick_dish_id_by_style_tag(conn, style_tag: str, required_tag: Optional[str] = None) -> int:
    if required_tag:
        row = fetch_one(
            conn,
            """
            SELECT d.id
            FROM dish d
            JOIN dish_tag t ON t.dish_id=d.id
            WHERE d.active=1 AND d.style_tag=? AND t.tag=?
            ORDER BY d.id
            LIMIT 1
            """,
            (style_tag, required_tag),
        )
    else:
        row = fetch_one(
            conn,
            "SELECT id FROM dish WHERE active=1 AND style_tag=? ORDER BY id LIMIT 1",
            (style_tag,),
        )

    if not row:
        extra = f" y tag='{required_tag}'" if required_tag else ""
        raise RuntimeError(f"No existe dish activo con style_tag='{style_tag}'{extra}. Revisa seed/tags.")
    return int(row["id"])


def pick_fixed(conn, slot: str) -> PickResult:
    if slot == "entrada_comal":
        return PickResult(
            dish_id=DISH_ID_ANTOJITOS_COMAL,
            explanation="Fijo: siempre 'Antojitos del comal'.",
            is_forced=True,
        )

    if slot == "arroz":
        return PickResult(
            dish_id=DISH_ID_ARROZ_AL_GUSTO,
            explanation="Fijo: siempre 'Arroz al gusto (Plátano, Huevo o Mole)'.",
            is_forced=True,
        )

    if slot == "paella":
        did = pick_dish_id_by_style_tag(conn, STYLE_PAELLA_FIJA, required_tag=TAG_SATURDAY_FIXED)
        return PickResult(dish_id=did, explanation="Fijo (Sábado): siempre 'Paella'.", is_forced=True)

    if slot == "nuggets":
        did = pick_dish_id_by_style_tag(conn, STYLE_NUGGETS_FIJO, required_tag=TAG_SATURDAY_FIXED)
        return PickResult(dish_id=did, explanation="Fijo (Sábado): siempre 'Nuggets'.", is_forced=True)

    if slot == "pancita":
        did = pick_dish_id_by_style_tag(conn, STYLE_PANCITA_FIJA, required_tag=TAG_SATURDAY_FIXED)
        return PickResult(dish_id=did, explanation="Fijo (Sábado): siempre 'Pancita'.", is_forced=True)

    raise ValueError(f"Slot '{slot}' no es fijo.")


def _postprocess_pick_explanation(slot: str, pick: PickResult) -> PickResult:
    if slot in AL_GUSTO_SLOTS:
        pick.explanation += " | Nota: incluir leyenda 'o al gusto'."
    return pick


def pick_strict(
    conn,
    slot: str,
    day: date,
    rng: random.Random,
    window_days: int,
    blocked_dish_id: Optional[int] = None,
    blocked_dish_ids: frozenset[int] = frozenset(),
    blocked_sauce_tags: frozenset = frozenset(),
    blocked_beef_cut_ids: frozenset = frozenset(),
    blocked_pasta_tipos: frozenset = frozenset(),
    exclude_week_id_for_rotation: Optional[int] = None,
    _candidate_ids: Optional[set] = None,  # if set, restrict to these dish IDs
) -> Optional[PickResult]:
    c = candidates(conn, slot, day)
    if _candidate_ids is not None:
        c = [x for x in c if int(x["id"]) in _candidate_ids]

    if blocked_dish_id is not None:
        c = [x for x in c if int(x["id"]) != int(blocked_dish_id)]
    if blocked_dish_ids:
        c = [x for x in c if int(x["id"]) not in blocked_dish_ids]

    if not c:
        return None

    # sin rotación de platillo — pero sí aplicamos sauce y corte filters
    if window_days <= 0:
        filtered = _apply_sauce_filter(c, blocked_sauce_tags)
        filtered = _apply_beef_cut_filter(conn, filtered, blocked_beef_cut_ids)
        if slot == "pasta":
            filtered = _apply_pasta_tipo_filter(conn, filtered, blocked_pasta_tipos)
        if not filtered:
            return None
        # Soft preference: prefer neutral protein for sopa/crema
        preferred = _apply_soup_protein_preference(filtered, slot, day)
        pool = preferred if preferred else filtered
        chosen = _weighted_choice(conn, pool, day, slot, rng)
        pick = PickResult(dish_id=int(chosen["id"]), explanation=f"Elegido '{chosen['name']}'.")
        return _postprocess_pick_explanation(slot, pick)

    # rotación por MISMO slot (+ sister slots)
    recent_ids = recent_dish_ids(
        conn,
        day,
        window_days,
        slot=slot,
        exclude_week_id=exclude_week_id_for_rotation,
    )

    recent_styles: set[str] = set()
    if slot == "pasta":
        recent_styles = recent_pasta_styles(conn, day, window_days, exclude_week_id=exclude_week_id_for_rotation)

    filtered = []
    for x in c:
        dish_id = int(x["id"])
        if dish_id in recent_ids:
            continue
        if slot == "pasta":
            stg = x.get("style_tag")
            if stg and stg in recent_styles:
                continue
        filtered.append(x)

    # aplicar filtros de salsa y corte de res
    filtered = _apply_sauce_filter(filtered, blocked_sauce_tags)
    filtered = _apply_beef_cut_filter(conn, filtered, blocked_beef_cut_ids)
    # pasta tipo filter
    if slot == "pasta":
        filtered = _apply_pasta_tipo_filter(conn, filtered, blocked_pasta_tipos)

    if not filtered:
        return None

    # Soft preference: prefer neutral protein for sopa/crema
    preferred = _apply_soup_protein_preference(filtered, slot, day)
    pool = preferred if preferred else filtered
    chosen = _weighted_choice(conn, pool, day, slot, rng)
    pick = PickResult(dish_id=int(chosen["id"]), explanation=f"Elegido '{chosen['name']}'.")
    return _postprocess_pick_explanation(slot, pick)


def _apply_sauce_filter(cand: list[dict], blocked_sauce_tags: frozenset) -> list[dict]:
    """Filtra candidatos cuyo sauce_tag esté bloqueado. NULL siempre pasa."""
    if not blocked_sauce_tags:
        return cand
    return [x for x in cand if x.get("sauce_tag") not in blocked_sauce_tags]


def _apply_soup_protein_preference(cand: list[dict], slot: str, day: date) -> list[dict]:
    """
    For sopa/crema on weekdays: prefer protein='none' dishes to avoid repeating
    the same protein as the day's fuertes (which always cover all 5 proteins).
    Falls back to full candidate list if fewer than 3 neutral candidates exist.
    """
    if slot not in {"sopa", "crema"} or day.weekday() == 5:
        return cand
    neutral = [x for x in cand if x.get("protein") in (None, "none")]
    return neutral if len(neutral) >= 3 else cand


def _priority_tag_for_slot_day(slot: str, day: date) -> Optional[str]:
    """Returns day-priority tag for this slot/day. Enchiladas slot is excluded."""
    if slot == "enchiladas":
        return None
    wd = day.weekday()
    if wd == 4:
        return TAG_ONLY_FRI
    if wd == 5:
        return TAG_ONLY_SAT
    return None


def _get_priority_dish_ids(conn, cand: list[dict], priority_tag: str) -> set[int]:
    """Returns IDs of candidate dishes tagged with priority_tag."""
    if not cand:
        return set()
    ids = [int(c["id"]) for c in cand]
    qmarks = ",".join("?" * len(ids))
    rows = fetch_all(
        conn,
        f"SELECT dish_id FROM dish_tag WHERE tag=? AND dish_id IN ({qmarks})",
        (priority_tag, *ids),
    )
    return {int(r["dish_id"]) for r in rows}


def pick_with_relaxation(
    conn,
    slot: str,
    day: date,
    rng: random.Random,
    blocked_dish_id: Optional[int] = None,
    blocked_dish_ids: frozenset[int] = frozenset(),
    blocked_sauce_tags: frozenset = frozenset(),
    blocked_beef_cut_ids: frozenset = frozenset(),
    blocked_pasta_tipos: frozenset = frozenset(),
    exclude_week_id_for_rotation: Optional[int] = None,
) -> Optional[PickResult]:
    base = window_days_for_slot(slot)

    common = dict(
        blocked_dish_id=blocked_dish_id,
        blocked_dish_ids=blocked_dish_ids,
        blocked_sauce_tags=blocked_sauce_tags,
        blocked_beef_cut_ids=blocked_beef_cut_ids,
        blocked_pasta_tipos=blocked_pasta_tipos,
        exclude_week_id_for_rotation=exclude_week_id_for_rotation,
    )

    # ── Prioridad: viernes/sábado — intentar primero con dishes marcados ─
    priority_tag = _priority_tag_for_slot_day(slot, day)
    if priority_tag:
        all_cand = candidates(conn, slot, day)
        if blocked_dish_id is not None:
            all_cand = [x for x in all_cand if int(x["id"]) != int(blocked_dish_id)]
        if blocked_dish_ids:
            all_cand = [x for x in all_cand if int(x["id"]) not in blocked_dish_ids]
        priority_ids = _get_priority_dish_ids(conn, all_cand, priority_tag)
        if priority_ids:
            r = pick_strict(conn, slot, day, rng, window_days=base, _candidate_ids=priority_ids, **common)
            if r:
                return r
            # All priority dishes are within rotation window → fall through to all candidates

    # ── Fase 1: ventana completa + filtros de salsa y corte ─────
    r = pick_strict(
        conn, slot, day, rng,
        window_days=base,
        **common,
    )
    if r:
        return r

    # ── Fase 2: relajar ventana de platillo, mantener filtros ───
    for w in range(base - 1, -1, -1):
        r = pick_strict(
            conn, slot, day, rng,
            window_days=w,
            blocked_dish_id=blocked_dish_id,
            blocked_sauce_tags=blocked_sauce_tags,
            blocked_beef_cut_ids=blocked_beef_cut_ids,
            blocked_pasta_tipos=blocked_pasta_tipos,
            exclude_week_id_for_rotation=exclude_week_id_for_rotation,
        )
        if r:
            r.was_exception = True
            r.exception_reason = f"WINDOW_RELAXED_{base}_TO_{w}"
            return r

    # ── Fase 3: sin filtro de salsa/pasta_tipo (emergencia) ──────
    # El catálogo está muy limitado; preferimos repetir salsa a dejar slot vacío.
    if blocked_sauce_tags or blocked_beef_cut_ids or blocked_pasta_tipos:
        r = pick_strict(
            conn, slot, day, rng,
            window_days=base,
            blocked_dish_id=blocked_dish_id,
            blocked_sauce_tags=frozenset(),
            blocked_beef_cut_ids=frozenset(),
            blocked_pasta_tipos=frozenset(),
            exclude_week_id_for_rotation=exclude_week_id_for_rotation,
        )
        if r:
            r.was_exception = True
            r.exception_reason = "SAUCE_BLOCK_RELAXED"
            return r

        for w in range(base - 1, -1, -1):
            r = pick_strict(
                conn, slot, day, rng,
                window_days=w,
                blocked_dish_id=blocked_dish_id,
                blocked_sauce_tags=frozenset(),
                blocked_beef_cut_ids=frozenset(),
                blocked_pasta_tipos=frozenset(),
                exclude_week_id_for_rotation=exclude_week_id_for_rotation,
            )
            if r:
                r.was_exception = True
                r.exception_reason = f"SAUCE_AND_WINDOW_RELAXED_{base}_TO_{w}"
                return r

    # Fase 4: permitir repetir dish_id dentro de la semana (ultima salida de emergencia).
    if blocked_dish_ids:
        r = pick_strict(
            conn, slot, day, rng,
            window_days=base,
            blocked_dish_id=blocked_dish_id,
            blocked_dish_ids=frozenset(),
            blocked_sauce_tags=blocked_sauce_tags,
            blocked_beef_cut_ids=blocked_beef_cut_ids,
            blocked_pasta_tipos=blocked_pasta_tipos,
            exclude_week_id_for_rotation=exclude_week_id_for_rotation,
        )
        if r:
            r.was_exception = True
            r.exception_reason = "WEEK_DISH_REPEAT_RELAXED"
            return r

        for w in range(base - 1, -1, -1):
            r = pick_strict(
                conn, slot, day, rng,
                window_days=w,
                blocked_dish_id=blocked_dish_id,
                blocked_dish_ids=frozenset(),
                blocked_sauce_tags=blocked_sauce_tags,
                blocked_beef_cut_ids=blocked_beef_cut_ids,
                blocked_pasta_tipos=blocked_pasta_tipos,
                exclude_week_id_for_rotation=exclude_week_id_for_rotation,
            )
            if r:
                r.was_exception = True
                r.exception_reason = f"WEEK_DISH_REPEAT_AND_WINDOW_RELAXED_{base}_TO_{w}"
                return r

    return None


# =========================
# Recompute helpers
# =========================
def _fixed_slots_for_day(day: date) -> list[str]:
    if day.weekday() == 5:  # sábado
        return ["entrada_comal", "paella", "nuggets", "pancita"]
    return ["entrada_comal", "arroz"]


def _apply_fixed_slot(conn, week_id: int, day: date, slot: str) -> None:
    if slot not in slots_for_day(day):
        return

    ov = get_override(conn, day, slot)
    if ov and ov["forced_dish_id"]:
        forced_id = int(ov["forced_dish_id"])
        if dish_is_active(conn, forced_id):
            pick = PickResult(
                dish_id=forced_id,
                explanation=f"FORZADO por override (slot fijo): {dish_name(conn, forced_id)}",
                is_forced=True,
            )
            pick = _postprocess_pick_explanation(slot, pick)
            save_item(conn, week_id, day, slot, pick)
            return

    save_item(conn, week_id, day, slot, pick_fixed(conn, slot))


def _apply_fixed_for_day(conn, week_id: int, day: date) -> None:
    for slot in _fixed_slots_for_day(day):
        _apply_fixed_slot(conn, week_id, day, slot)


def _pick_molcajete_for_monday(
    conn,
    day: date,
    rng: random.Random,
    exclude_week_id_for_rotation: Optional[int],
) -> PickResult:
    mol_ov = get_override(conn, day, "molcajete")

    if mol_ov and mol_ov["forced_dish_id"]:
        forced_id = int(mol_ov["forced_dish_id"])
        if dish_is_active(conn, forced_id):
            return PickResult(
                dish_id=forced_id,
                explanation=f"FORZADO por override: {dish_name(conn, forced_id)}",
                is_forced=True,
            )

    m = pick_with_relaxation(conn, "molcajete", day, rng, exclude_week_id_for_rotation=exclude_week_id_for_rotation)
    if m is None:
        raise RuntimeError("No hay candidatos para 'molcajete' (revisa dish_tag monday_molcajete).")
    prot = _molcajete_protein(conn, m.dish_id)
    if prot == "none":
        raise RuntimeError(
            f"Molcajete elegido sin proteina (dish_id={m.dish_id}). "
            "Todos los molcajetes deben tener protein definida."
        )
    return m


def _molcajete_protein(conn, mol_dish_id: int) -> str:
    prot_row = fetch_one(conn, "SELECT protein FROM dish WHERE id=?", (int(mol_dish_id),))
    return ((prot_row["protein"] if prot_row else None) or "none")


def _salad_anchor_day(week_start: date, slot: str) -> date:
    return week_start + timedelta(days=SALAD_ANCHOR_OFFSET[slot])


def _salad_linked_days(week_start: date, slot: str) -> list[date]:
    wd_targets = SALAD_DAYS_BY_SLOT[slot]
    return [week_start + timedelta(days=wd) for wd in wd_targets]


def _weekly_salad_pick(
    conn,
    week_id: int,
    week_start: date,
    slot: str,
    rng: random.Random,
    *,
    exclude_week_id_for_rotation: Optional[int] = None,
) -> PickResult:
    anchor_day = _salad_anchor_day(week_start, slot)

    existing = fetch_one(
        conn,
        """
        SELECT dish_id, is_forced, was_exception, exception_reason, explanation
        FROM menu_item
        WHERE menu_week_id=? AND menu_date=? AND slot=?
        """,
        (int(week_id), to_yyyy_mm_dd(anchor_day), slot),
    )
    if existing:
        did = int(existing["dish_id"])
        if dish_is_active(conn, did):
            return PickResult(
                dish_id=did,
                explanation=existing["explanation"] or f"Ensalada semanal ({slot}) reutilizada.",
                is_forced=bool(existing["is_forced"]),
                was_exception=bool(existing["was_exception"]),
                exception_reason=existing["exception_reason"],
            )

    ov = get_override(conn, anchor_day, slot)
    if ov and ov["forced_dish_id"]:
        forced_id = int(ov["forced_dish_id"])
        if dish_is_active(conn, forced_id):
            return PickResult(
                dish_id=forced_id,
                explanation=f"FORZADO (ensalada semanal {slot}) en ancla {to_yyyy_mm_dd(anchor_day)}: {dish_name(conn, forced_id)}",
                is_forced=True,
            )

    blocked_id = int(ov["blocked_dish_id"]) if (ov and ov["blocked_dish_id"]) else None
    blocked_week_ids = week_non_fixed_dish_ids_used(conn, week_id)
    pick = pick_with_relaxation(
        conn,
        slot,
        anchor_day,
        rng,
        blocked_dish_id=blocked_id,
        blocked_dish_ids=blocked_week_ids,
        exclude_week_id_for_rotation=exclude_week_id_for_rotation,
    )
    if pick is None:
        raise RuntimeError(f"No hay candidatos para ensalada semanal '{slot}' (ancla {to_yyyy_mm_dd(anchor_day)}).")

    pick.explanation = f"Elegida ensalada semanal ({slot}) en ancla {to_yyyy_mm_dd(anchor_day)}: {dish_name(conn, pick.dish_id)}"
    return pick


def recompute_day(
    conn,
    week_id: int,
    day: date,
    rng: random.Random,
    *,
    exclude_week_id_for_rotation: Optional[int] = None,
) -> None:
    day_slots = slots_for_day(day)
    clear_day_items(conn, week_id, day)

    _apply_fixed_for_day(conn, week_id, day)

    # Lunes molcajete (y quita fuerte de su proteína)
    if day.weekday() == 0 and "molcajete" in day_slots:
        m = _pick_molcajete_for_monday(conn, day, rng, exclude_week_id_for_rotation)
        save_item(conn, week_id, day, "molcajete", m)

        prot = _molcajete_protein(conn, m.dish_id)
        if prot and prot != "none":
            strong_slot = f"fuerte_{prot}"
            day_slots = [s for s in day_slots if s != strong_slot]

    week_start = ensure_monday(day)

    for slot in day_slots:
        if slot in FIXED_SLOTS or slot == "molcajete":
            continue

        # Ensaladas semanales
        if slot in SALAD_SLOTS:
            pick = _weekly_salad_pick(
                conn,
                week_id,
                week_start,
                slot,
                rng,
                exclude_week_id_for_rotation=exclude_week_id_for_rotation,
            )
            wd_targets = SALAD_DAYS_BY_SLOT[slot]
            linked_dates = [to_yyyy_mm_dd(week_start + timedelta(days=wd)) for wd in wd_targets]
            role = "ancla" if day.weekday() == SALAD_ANCHOR_OFFSET[slot] else "espejo"
            pick.explanation += f" | Ensalada semanal ({role}). También en: {', '.join(linked_dates)}"
            save_item(conn, week_id, day, slot, pick)
            continue

        ov = get_override(conn, day, slot)

        # Forzar
        if ov and ov["forced_dish_id"]:
            forced_id = int(ov["forced_dish_id"])
            if dish_is_active(conn, forced_id):
                pick = PickResult(
                    dish_id=forced_id,
                    explanation=f"FORZADO por override: {dish_name(conn, forced_id)}",
                    is_forced=True,
                )
                pick = _postprocess_pick_explanation(slot, pick)
                save_item(conn, week_id, day, slot, pick)
                continue

        blocked_id = int(ov["blocked_dish_id"]) if (ov and ov["blocked_dish_id"]) else None
        blocked_week_ids = week_non_fixed_dish_ids_used(conn, week_id)

        # Sauce blocking: salsas recientes (cross-semanas) + ya usadas esta semana
        blocked_sauces = build_blocked_sauce_tags(
            conn, week_id, day,
            exclude_week_id_for_rotation=exclude_week_id_for_rotation,
        )

        # Beef cut blocking (L-V en slots de res): intra-semana + cross-week (WINDOW_BEEF_CUT días).
        # Sábado queda excluido: el menú de sábado es diferente y no aplica la regla.
        blocked_cuts = (
            build_blocked_beef_cut_ids(
                conn, week_id, day,
                exclude_week_id_for_rotation=exclude_week_id_for_rotation,
            )
            if slot in _RES_SLOTS and day.weekday() != 5
            else frozenset()
        )

        # Pasta tipo blocking: tipos de pasta ya usados esta semana (intra-week).
        blocked_pasta_tipos = (
            week_pasta_tipos_used(conn, week_id)
            if slot == "pasta"
            else frozenset()
        )

        pick = pick_with_relaxation(
            conn,
            slot,
            day,
            rng,
            blocked_dish_id=blocked_id,
            blocked_dish_ids=blocked_week_ids,
            blocked_sauce_tags=blocked_sauces,
            blocked_beef_cut_ids=blocked_cuts,
            blocked_pasta_tipos=blocked_pasta_tipos,
            exclude_week_id_for_rotation=exclude_week_id_for_rotation,
        )
        if pick is None:
            raise RuntimeError(
                f"No se pudo llenar slot='{slot}' el día {to_yyyy_mm_dd(day)} "
                f"ni relajando window hasta 0. Revisa catálogo/overrides para ese slot."
            )

        save_item(conn, week_id, day, slot, pick)


def recompute_slot(
    conn,
    week_id: int,
    day: date,
    slot: str,
    rng: random.Random,
    *,
    exclude_week_id_for_rotation: Optional[int] = None,
) -> None:
    if slot == "molcajete" and day.weekday() == 0:
        recompute_day(conn, week_id, day, rng, exclude_week_id_for_rotation=exclude_week_id_for_rotation)
        return

    week_start = ensure_monday(day)

    # Ensaladas semanales: recalcula ancla y replica
    if slot in SALAD_SLOTS:
        linked_days = _salad_linked_days(week_start, slot)
        anchor_day = _salad_anchor_day(week_start, slot)

        if slot not in slots_for_day(anchor_day):
            return

        delete_item(conn, week_id, anchor_day, slot)
        anchor_pick = _weekly_salad_pick(
            conn,
            week_id,
            week_start,
            slot,
            rng,
            exclude_week_id_for_rotation=exclude_week_id_for_rotation,
        )
        anchor_pick.explanation += " | (Ensalada semanal: ancla)"
        save_item(conn, week_id, anchor_day, slot, anchor_pick)

        for d2 in linked_days:
            if d2 == anchor_day:
                continue
            if slot not in slots_for_day(d2):
                continue

            delete_item(conn, week_id, d2, slot)
            mirror_pick = PickResult(
                dish_id=anchor_pick.dish_id,
                explanation=f"Ensalada semanal ({slot}) replicada desde {to_yyyy_mm_dd(anchor_day)}. | (Ensalada semanal: espejo)",
                is_forced=anchor_pick.is_forced,
                was_exception=anchor_pick.was_exception,
                exception_reason=anchor_pick.exception_reason,
            )
            save_item(conn, week_id, d2, slot, mirror_pick)

        return

    day_slots = slots_for_day(day)
    if slot not in day_slots:
        raise RuntimeError(f"El slot '{slot}' no existe para el día {to_yyyy_mm_dd(day)}.")

    if slot in FIXED_SLOTS:
        delete_item(conn, week_id, day, slot)
        _apply_fixed_slot(conn, week_id, day, slot)
        return

    delete_item(conn, week_id, day, slot)

    ov = get_override(conn, day, slot)

    if ov and ov["forced_dish_id"]:
        forced_id = int(ov["forced_dish_id"])
        if dish_is_active(conn, forced_id):
            pick = PickResult(
                dish_id=forced_id,
                explanation=f"FORZADO por override: {dish_name(conn, forced_id)}",
                is_forced=True,
            )
            pick = _postprocess_pick_explanation(slot, pick)
            save_item(conn, week_id, day, slot, pick)
            return

    blocked_id = int(ov["blocked_dish_id"]) if (ov and ov["blocked_dish_id"]) else None
    blocked_week_ids = week_non_fixed_dish_ids_used(conn, week_id)

    blocked_sauces = build_blocked_sauce_tags(
        conn, week_id, day,
        exclude_week_id_for_rotation=exclude_week_id_for_rotation,
    )

    blocked_cuts = (
        build_blocked_beef_cut_ids(
            conn, week_id, day,
            exclude_week_id_for_rotation=exclude_week_id_for_rotation,
        )
        if slot in _RES_SLOTS and day.weekday() != 5
        else frozenset()
    )

    # Pasta tipo blocking: tipos de pasta ya usados esta semana (intra-week).
    blocked_pasta_tipos = (
        week_pasta_tipos_used(conn, week_id)
        if slot == "pasta"
        else frozenset()
    )

    pick = pick_with_relaxation(
        conn,
        slot,
        day,
        rng,
        blocked_dish_id=blocked_id,
        blocked_dish_ids=blocked_week_ids,
        blocked_sauce_tags=blocked_sauces,
        blocked_beef_cut_ids=blocked_cuts,
        blocked_pasta_tipos=blocked_pasta_tipos,
        exclude_week_id_for_rotation=exclude_week_id_for_rotation,
    )
    if pick is None:
        raise RuntimeError(
            f"No se pudo llenar slot='{slot}' el día {to_yyyy_mm_dd(day)} "
            f"ni relajando window hasta 0. Revisa catálogo/overrides para ese slot."
        )

    save_item(conn, week_id, day, slot, pick)


# =========================
# Generator (semana completa)
# =========================
def generate_week(
    week_start_date: str,
    exclude_week_id_for_rotation: Optional[int] = None,
    rng_seed: Optional[str] = None,
) -> int:
    week_start = ensure_monday(parse_yyyy_mm_dd(week_start_date))

    seed = rng_seed or to_yyyy_mm_dd(week_start)
    rng = random.Random(seed)

    with get_conn() as conn:
        week_id = insert_or_update_menu_week(conn, week_start)
        clear_week_items(conn, week_id)

        for i in range(6):  # L-S
            d = week_start + timedelta(days=i)
            recompute_day(
                conn,
                week_id,
                d,
                rng,
                exclude_week_id_for_rotation=exclude_week_id_for_rotation,
            )

        conn.commit()
        return week_id


if __name__ == "__main__":
    print(">>> generator.py se está ejecutando")
    week_id = generate_week("2026-01-05")
    print(">>> semana generada con id =", week_id)
