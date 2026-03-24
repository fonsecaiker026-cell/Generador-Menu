"""Audit duplicate dishes in the database."""
import sqlite3
import sys
import unicodedata
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

DB = "data/app.db"


def normalize(s):
    s = s.lower().strip()
    nfd = unicodedata.normalize('NFD', s)
    # Remove combining characters (accents)
    no_accents = [c for c in nfd if unicodedata.category(c) != 'Mn']
    s = ''.join(no_accents)
    return ' '.join(s.split())


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT id, name, course_group, protein, active FROM dish ORDER BY name")
    rows = cur.fetchall()

    # Group by (normalized_name, course_group)
    groups = defaultdict(list)
    for r in rows:
        key = (normalize(r[1]), r[2])
        groups[key].append(r)

    dupes = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"Total grupos con duplicados: {len(dupes)}")
    print()

    for (norm, cg), items in sorted(dupes.items()):
        print(f"GRUPO [{cg}]: {norm}")
        for i in items:
            status = "ACTIVO  " if i[4] == 1 else "inactivo"
            print(f"  [{status}] id={i[0]:5} | prot={i[3]:8} | {i[1]}")
        print()

    # Also find similar names (not exact) - e.g. "Sopa de X" vs "Sopa de X con Y"
    print()
    print("=" * 60)
    print("POSIBLES SIMILARES (mismo grupo, misma proteina, nombre muy parecido)")
    print("=" * 60)
    cur.execute("SELECT id, name, course_group, protein FROM dish WHERE active=1 ORDER BY course_group, protein, name")
    active = cur.fetchall()

    # Group by course_group + protein, find names sharing first 3 words
    cg_prot = defaultdict(list)
    for r in active:
        cg_prot[(r[2], r[3])].append(r)

    for (cg, prot), items in sorted(cg_prot.items()):
        # Group by first 3 normalized words
        word_groups = defaultdict(list)
        for r in items:
            words = normalize(r[1]).split()[:3]
            key = ' '.join(words)
            word_groups[key].append(r)
        for key, group in word_groups.items():
            if len(group) > 1:
                print(f"  [{cg}][{prot}] base: '{key}'")
                for r in group:
                    print(f"    id={r[0]:5} | {r[1]}")
                print()

    conn.close()


if __name__ == "__main__":
    main()
