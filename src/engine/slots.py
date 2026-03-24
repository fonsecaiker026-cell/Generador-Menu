# src/engine/slots.py
from __future__ import annotations

from datetime import date

from src.config import CFG

WEEKDAY_SHORT = ["LUN", "MAR", "MIE", "JUE", "VIE", "SAB", "DOM"]


def weekday_short(d: date) -> str:
    return WEEKDAY_SHORT[d.weekday()]


# -------------------------
# Ensaladas (1 slot por día)
# -------------------------
_DEFAULT_SALAD_BY_WEEKDAY = {
    0: "ensalada_A",  # lunes
    1: "ensalada_B",  # martes
    2: "ensalada_C",  # miércoles
    3: "ensalada_A",  # jueves
    4: "ensalada_B",  # viernes
    5: "ensalada_C",  # sábado
    6: "ensalada_C",  # domingo (no se usa normalmente)
}


def salad_slot_for_day(d: date) -> str:
    """
    Regresa el slot de ensalada del día (A/B/C).
    Prioridad:
      1) CFG.salad_map[weekday] si existe
      2) mapping default (A/B/C)
    """
    try:
        m = getattr(CFG, "salad_map", None)
        if isinstance(m, dict):
            slot = m.get(d.weekday())
            if slot in ("ensalada_A", "ensalada_B", "ensalada_C"):
                return slot
    except Exception:
        pass

    return _DEFAULT_SALAD_BY_WEEKDAY[d.weekday()]


# -------------------------
# Slots por día
# -------------------------
def base_weekday_slots(d: date) -> list[str]:
    """
    Slots base para L-V (sin molcajete).
    Reglas:
      - L-V siempre hay 1 ensalada + arroz
      - Viernes: además chamorro (extra)
    """
    salad_slot = salad_slot_for_day(d)

    slots = [
        "entrada_comal",
        "entrada_no_comal",
        "sopa",
        "crema",
        "pasta",
        salad_slot,  # 1 ensalada por día
        "arroz",     # L-V siempre
        "fuerte_res",
        "fuerte_pollo",
        "fuerte_cerdo",
        "fuerte_pescado",
        "fuerte_camaron",
        "complemento",
    ]

    if d.weekday() == 4:  # viernes
        slots.append("chamorro")

    return slots


def monday_slots(d: date) -> list[str]:
    """
    Lunes: igual que base, pero incluye molcajete.
    (El generator decide si elimina el fuerte de la misma proteína.)
    """
    slots = base_weekday_slots(d)
    # Insertar molcajete antes de fuertes (orden más lógico)
    insert_at = 7  # justo antes de fuerte_res (después de arroz)
    if "molcajete" not in slots:
        slots.insert(insert_at, "molcajete")
    return slots


def saturday_slots(d: date) -> list[str]:
    """
    Slots de sábado:
      - SÍ hay entrada_comal (como pediste)
      - Sopas/caldos: pancita (fijo) + crema + sopa_pollo (only_sat)
      - SÍ hay 1 ensalada + pasta
      - SÍ hay fuertes normales (res/pollo/cerdo)
      - Especiales: paella, pescado_al_gusto, camaron_al_gusto, nuggets, enchiladas
      - NO arroz
    """
    salad_slot = salad_slot_for_day(d)

    return [
        "entrada_comal",
        "entrada_no_comal",
        "pancita",
        "crema",
        "sopa_pollo",
        salad_slot,
        "pasta",
        "fuerte_res",
        "fuerte_pollo",
        "fuerte_cerdo",
        "paella",
        "pescado_al_gusto",
        "camaron_al_gusto",
        "nuggets",
        "enchiladas",
    ]


def slots_for_day(d: date) -> list[str]:
    """
    Selector único que usa el generator.
    Semana operativa: L-S (0-5). Domingo regresa [] por seguridad.
    """
    wd = d.weekday()

    if wd == 6:
        return []

    if wd == 0:
        return monday_slots(d)

    if wd == 5:
        return saturday_slots(d)

    return base_weekday_slots(d)
