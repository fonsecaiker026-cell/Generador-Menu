"""
Assign sauce_tag to all dishes based on name keywords.

sauce_tag groups dishes that share the same sauce/flavor profile so the
rotation engine can avoid repeating the same sauce within the window.

Rules:
- Only one sauce_tag per dish (the most specific / dominant one)
- Keyword matching is done on lowercased name, most-specific first
- After auto-assignment, a report is printed for manual review
"""
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

DB = "data/app.db"

# ─────────────────────────────────────────────────────────────────
# SAUCE MAP — ordered from most specific to most general.
# Each entry: (sauce_tag, [keywords_that_must_appear_in_name])
# If ALL keywords in the list are found, the tag is assigned.
# First match wins.
# ─────────────────────────────────────────────────────────────────
SAUCE_RULES = [
    # ── Salsas de chiles específicos ──────────────────────────────
    ("salsa_morita",        ["morita"]),
    ("salsa_guajillo",      ["guajillo"]),
    ("salsa_cascabel",      ["cascabel"]),
    ("salsa_catarino",      ["catarino"]),
    ("salsa_arbol",         ["chile de arbol"]),
    ("salsa_arbol",         ["chile arbol"]),
    ("salsa_pasilla",       ["pasilla"]),
    ("salsa_chiles_secos",  ["chiles secos"]),
    ("salsa_tres_chiles",   ["tres chiles"]),
    ("salsa_cien_fuegos",   ["cien fuegos"]),
    ("salsa_mulato",        ["mulato"]),
    ("salsa_ancho",         ["chile ancho"]),
    ("salsa_chiltepin",     ["chiltepin"]),
    ("salsa_habanero",      ["habanero"]),
    ("salsa_chipotle",      ["chipotle"]),

    # ── Salsas con nombre propio ──────────────────────────────────
    ("salsa_borracha",      ["borracha"]),
    ("salsa_tatemada",      ["tatemada"]),
    ("salsa_molcajeteada",  ["molcajeteada"]),
    ("salsa_molcajete",     ["salsa molcajete"]),
    ("salsa_martajada",     ["martajada"]),
    ("salsa_ranchera",      ["ranchera"]),
    ("salsa_arriera",       ["arriera"]),
    ("salsa_mexicana",      ["mexicana"]),
    ("salsa_pibil",         ["pibil"]),
    ("salsa_verde",         ["salsa verde"]),
    ("salsa_verde",         ["en verde"]),
    ("salsa_roja",          ["salsa roja"]),
    ("salsa_bechamel",      ["bechamel"]),
    ("salsa_holandesa",     ["holandesa"]),
    ("salsa_gravy",         ["gravy"]),
    ("salsa_bufe",          ["bufalo"]),
    ("salsa_búfalo",        ["buffalo"]),

    # ── Salsas cremosas (del menú de filetes) ────────────────────
    ("crema_cilantro",      ["crema de cilantro"]),
    ("crema_cilantro",      ["cremosa de cilantro"]),
    ("crema_chipotle",      ["crema de chipotle"]),
    ("crema_chipotle",      ["cremosa de chipotle"]),
    ("crema_espinaca",      ["crema de espinaca"]),
    ("crema_espinaca",      ["cremosa de espinaca"]),
    ("crema_champiñones",   ["crema de champiñon"]),
    ("crema_champiñones",   ["cremosa de champiñon"]),
    ("crema_poblano",       ["crema de poblano"]),
    ("crema_poblano",       ["cremosa de poblano"]),
    ("crema_poblano",       ["crema poblana"]),
    ("crema_tres_quesos",   ["tres quesos"]),
    ("crema_almejas",       ["crema de almejas"]),
    ("crema_almejas",       ["cremosa de almejas"]),
    ("crema_huitlacoche",   ["crema de huitlacoche"]),
    ("crema_huitlacoche",   ["cremosa de huitlacoche"]),

    # ── Moles ─────────────────────────────────────────────────────
    ("mole_verde",          ["mole verde"]),
    ("mole_poblano",        ["mole poblano"]),
    ("mole_negro",          ["mole negro"]),
    ("pipian",              ["pipian"]),
    ("pipian",              ["pipián"]),
    ("encacahuatado",       ["encacahuatado"]),
    ("almendrado",          ["almendrado"]),

    # ── Estilos con verdura como protagonista de salsa ────────────
    ("salsa_verdolagas",    ["verdolaga"]),
    ("salsa_nopales",       ["nopales"]),      # solo si es la salsa principal

    # ── Adobo ─────────────────────────────────────────────────────
    ("adobo",               ["adobo"]),

    # ── Salsas de fruta ───────────────────────────────────────────
    ("salsa_tamarindo",     ["tamarindo"]),
    ("salsa_ciruela",       ["ciruela"]),
    ("salsa_naranja",       ["naranja"]),
    ("salsa_maracuya",      ["maracuya"]),
    ("salsa_maracuya",      ["maracuyá"]),
    ("salsa_pina_chipotle", ["pina", "chipotle"]),
    ("salsa_pina",          ["piña"]),
    ("salsa_pina",          ["pina"]),
    ("salsa_jamaica",       ["jamaica"]),
    ("salsa_mango",         ["mango"]),

    # ── Salsas de queso / lácteo ──────────────────────────────────
    ("salsa_queso",         ["salsa de queso"]),
    ("salsa_queso_gorgo",   ["gorgonzola"]),

    # ── Estilos de cocción / preparación ─────────────────────────
    ("estilo_veracruzana",  ["veracruzana"]),
    ("estilo_talla",        ["a la talla"]),
    ("estilo_zarandeado",   ["zarandeado"]),
    ("estilo_mezcal",       ["mezcal"]),
    ("estilo_vino_blanco",  ["vino blanco"]),
    ("estilo_oporto",       ["oporto"]),
    ("estilo_pastor",       ["al pastor"]),
    ("estilo_chimichurri",  ["chimichurri"]),
    ("estilo_parmesana",    ["parmesana"]),
    ("estilo_napolitana",   ["napolitana"]),
    ("estilo_florentina",   ["florentina"]),
    ("estilo_rockefeller",  ["rockefeller"]),
    ("estilo_cajun",        ["cajon"]),
    ("estilo_cajun",        ["cajón"]),
    ("estilo_hawaiano",     ["hawaiano"]),
    ("estilo_coco",         ["al coco"]),
    ("estilo_mostaza",      ["mostaza"]),
    ("estilo_pimienta",     ["pimienta"]),
    ("estilo_alcaparras",   ["alcaparras"]),
    ("estilo_mantequilla_limon", ["mantequilla", "limon"]),
    ("estilo_mantequilla_limon", ["mantequilla", "limón"]),
    ("estilo_mantequilla",  ["mantequilla"]),
    ("estilo_finas_hierbas",["finas hierbas"]),
    ("estilo_cerveza",      ["cerveza"]),
    # ── Técnicas de cocción que se perciben como "el mismo plato" ──
    ("estilo_empanizado",   ["empanizado"]),
    ("estilo_empanizado",   ["empanizada"]),
    ("estilo_empapelado",   ["empapelado"]),
    ("estilo_empapelado",   ["empapelada"]),
    ("estilo_plancha",      ["a la plancha"]),
    ("estilo_gratinado",    ["gratinado"]),
    ("estilo_gratinado",    ["gratinada"]),
    ("estilo_frito",        ["frito"]),
    ("estilo_frito",        ["frita"]),
    # ── Rellenos — agrupados por relleno principal ─────────────────
    ("relleno_espinaca",    ["rellena", "espinaca"]),
    ("relleno_espinaca",    ["relleno", "espinaca"]),
    ("relleno_huitlacoche", ["rellena", "huitlacoche"]),
    ("relleno_huitlacoche", ["relleno", "huitlacoche"]),
    ("relleno_flor_calabaza",["rellena", "flor de calabaza"]),
    ("relleno_flor_calabaza",["relleno", "flor de calabaza"]),
    ("relleno_queso",       ["rellena", "queso"]),
    ("relleno_queso",       ["relleno", "queso"]),
    ("relleno_rajas",       ["rellena", "rajas"]),
    ("relleno_rajas",       ["relleno", "rajas"]),
    ("relleno_jamon",       ["rellena", "jamon"]),
    ("relleno_jamon",       ["relleno", "jamon"]),
]


def normalize(s: str) -> str:
    return s.lower().strip()


def _word_match(text: str, keyword: str) -> bool:
    """
    True si keyword aparece como palabra o secuencia de palabras en text.
    Evita falsos positivos como 'pina' dentro de 'espinaca'.
    """
    import re
    # Escapa y busca con word boundaries
    pattern = r'(?<![a-záéíóúüñ])' + re.escape(keyword) + r'(?![a-záéíóúüñ])'
    return bool(re.search(pattern, text, re.IGNORECASE))


def assign_sauce_tag(name: str) -> str | None:
    n = normalize(name)
    for tag, keywords in SAUCE_RULES:
        if all(_word_match(n, kw.lower()) for kw in keywords):
            return tag
    return None


def main():
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    cur.execute("SELECT id, name, course_group, protein FROM dish WHERE active=1 ORDER BY course_group, name")
    dishes = cur.fetchall()

    assigned = []
    unassigned = []

    for dish_id, name, cg, protein in dishes:
        tag = assign_sauce_tag(name)
        cur.execute("UPDATE dish SET sauce_tag=? WHERE id=?", (tag, dish_id))
        if tag:
            assigned.append((dish_id, name, cg, protein, tag))
        else:
            unassigned.append((dish_id, name, cg, protein))

    conn.commit()

    # ── Report ────────────────────────────────────────────────────
    print(f"Total activos: {len(dishes)}")
    print(f"Con sauce_tag: {len(assigned)}")
    print(f"Sin sauce_tag: {len(unassigned)}")

    print("\n" + "=" * 60)
    print("ASIGNADOS POR SAUCE_TAG")
    print("=" * 60)
    from collections import defaultdict
    by_tag = defaultdict(list)
    for r in assigned:
        by_tag[r[4]].append(r)
    for tag in sorted(by_tag):
        items = by_tag[tag]
        print(f"\n[{tag}] — {len(items)} platillo(s)")
        for r in items:
            print(f"  [{r[2]:15}][{r[3]:8}] {r[1]}")

    print("\n" + "=" * 60)
    print(f"SIN SAUCE_TAG ({len(unassigned)} platillos) — sin salsa identificable")
    print("=" * 60)
    for cg in sorted(set(r[2] for r in unassigned)):
        group = [r for r in unassigned if r[2] == cg]
        print(f"\n[{cg}] — {len(group)}")
        for r in group:
            print(f"  id={r[0]:5} [{r[3]:8}] {r[1]}")

    conn.close()


if __name__ == "__main__":
    main()
