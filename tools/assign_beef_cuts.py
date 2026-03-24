"""
Assign beef cuts to res dishes via keyword matching.

Populates dish_beef_cut table. A dish can have more than one cut (e.g. a
parrillada that includes arrachera + costilla), but for rotation purposes
the presence of ANY matching cut is enough to block repetition.

Run:
    python tools/assign_beef_cuts.py
"""
import re
import sqlite3
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

DB = "data/app.db"

# ─────────────────────────────────────────────────────────────────
# CUT RULES — ordered most-specific first.
# Each entry: (cut_name, [keywords_that_must_appear_in_name])
# First match that fires wins for that cut; a dish can match multiple rules
# (each matching cut is added separately to dish_beef_cut).
# ─────────────────────────────────────────────────────────────────
CUT_RULES: list[tuple[str, list[str]]] = [
    # ── Cortes premium de nombre inequívoco ────────────────────────
    ("arrachera",   ["arrachera"]),
    ("ribeye",      ["ribeye"]),
    ("ribeye",      ["rib eye"]),
    ("sirloin",     ["sirloin"]),
    ("t_bone",      ["t-bone"]),
    ("t_bone",      ["t bone"]),
    ("new_york",    ["new york"]),
    ("gaonera",     ["gaonera"]),
    ("picana",      ["picaña"]),
    ("picana",      ["picana"]),

    # ── Cortes específicos de nombre en el platillo ────────────────
    ("aguja",       ["aguja norteña"]),
    ("aguja",       ["aguja nortena"]),
    ("aguja",       ["agujas"]),
    ("aguja",       ["aguja"]),
    ("bistec",      ["bistec"]),
    ("bistec",      ["bistek"]),
    ("costilla",    ["costilla"]),
    ("chambarete",  ["chambarete"]),
    ("cecina",      ["cecina"]),
    ("suadero",     ["suadero"]),
    ("cola",        ["cola de res"]),
    ("cola",        ["colita de res"]),

    # ── Preparaciones que implican corte concreto ──────────────────
    ("filete",      ["filete"]),
    ("filete",      ["medallones"]),
    ("milanesa",    ["milanesa"]),
    ("sabana",      ["sabanita"]),
    ("sabana",      ["sábana"]),
    ("sabana",      ["sabana"]),
    ("salpicon",    ["salpicón"]),
    ("salpicon",    ["salpicon"]),
    ("puntas",      ["puntas"]),
]


def _word_match(text: str, keyword: str) -> bool:
    pattern = r"(?<![a-záéíóúüñ])" + re.escape(keyword) + r"(?![a-záéíóúüñ])"
    return bool(re.search(pattern, text, re.IGNORECASE))


def cuts_for_dish(name: str) -> list[str]:
    """Return all cut names that match this dish name (can be multiple)."""
    n = name.lower().strip()
    matched: list[str] = []
    seen: set[str] = set()
    for cut, keywords in CUT_RULES:
        if cut in seen:
            continue
        if all(_word_match(n, kw.lower()) for kw in keywords):
            matched.append(cut)
            seen.add(cut)
    return matched


def main() -> None:
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")

    # Build cut_name → cut_id map
    cut_id: dict[str, int] = {}
    for row in conn.execute("SELECT id, name FROM beef_cut").fetchall():
        cut_id[row[1]] = row[0]

    # Fetch all active res dishes
    dishes = conn.execute(
        "SELECT id, name FROM dish WHERE active=1 AND protein='res' ORDER BY name"
    ).fetchall()

    # Clear existing links (idempotent re-run)
    conn.execute("DELETE FROM dish_beef_cut WHERE dish_id IN (SELECT id FROM dish WHERE protein='res')")

    assigned: dict[int, list[str]] = defaultdict(list)
    unassigned: list[tuple[int, str]] = []

    for dish_id, name in dishes:
        cuts = cuts_for_dish(name)
        if cuts:
            for cut_name in cuts:
                if cut_name not in cut_id:
                    print(f"  [WARN] cut '{cut_name}' not in beef_cut table — skipping")
                    continue
                conn.execute(
                    "INSERT OR IGNORE INTO dish_beef_cut(dish_id, beef_cut_id) VALUES (?,?)",
                    (dish_id, cut_id[cut_name]),
                )
                assigned[dish_id].append(cut_name)
        else:
            unassigned.append((dish_id, name))

    conn.commit()
    conn.close()

    # ── Report ─────────────────────────────────────────────────────
    print(f"Total res dishes: {len(dishes)}")
    print(f"Con corte asignado: {len(assigned)}")
    print(f"Sin corte (guisados, caldos, etc.): {len(unassigned)}")

    print("\n" + "=" * 60)
    print("ASIGNADOS POR CORTE")
    print("=" * 60)
    by_cut: dict[str, list] = defaultdict(list)
    for dish_id, cuts in assigned.items():
        name = next(n for i, n in dishes if i == dish_id)
        for c in cuts:
            by_cut[c].append(name)
    for cut in sorted(by_cut):
        print(f"\n[{cut}] — {len(by_cut[cut])}")
        for n in sorted(by_cut[cut]):
            print(f"  {n}")

    print("\n" + "=" * 60)
    print(f"SIN CORTE ({len(unassigned)}) — guisados, caldos, preparaciones mixtas")
    print("=" * 60)
    for _, name in unassigned:
        print(f"  {name}")


if __name__ == "__main__":
    main()
